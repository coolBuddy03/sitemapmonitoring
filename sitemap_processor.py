import requests
import logging
import xml.etree.ElementTree as ET
import urllib.parse
import concurrent.futures
from bs4 import BeautifulSoup
from time import time
from urllib.parse import urlparse
import gc  # Garbage collection
import os
import psutil

# Environment variables with defaults
MAX_URLS = int(os.environ.get('MAX_URLS', 5000))
CHUNK_SIZE = int(os.environ.get('CHUNK_SIZE', 10))
MAX_WORKERS = int(os.environ.get('MAX_WORKERS', 2))
MAX_MEMORY_MB = int(os.environ.get('MAX_MEMORY_MB', 500))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Custom exception for sitemap processing errors
class SitemapError(Exception):
    pass

def log_memory_usage():
    """Log current memory usage"""
    process = psutil.Process()
    memory_info = process.memory_info()
    memory_mb = memory_info.rss / 1024 / 1024
    logger.info(f"Memory usage: {memory_mb:.2f} MB")
    return memory_mb

def is_valid_url(url):
    """Check if a URL is valid"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def check_url_status(url):
    """
    Check the HTTP status code of a URL
    
    Args:
        url (str): URL to check
        
    Returns:
        dict: URL and its status information
    """
    try:
        # Make a HEAD request first (faster, less bandwidth)
        response = requests.head(
            url, 
            allow_redirects=False, 
            timeout=10,
            headers={'User-Agent': 'SitemapMonitor/1.0'}
        )
        
        # If HEAD request doesn't work well, try GET
        if response.status_code == 405:  # Method Not Allowed
            response = requests.get(
                url, 
                allow_redirects=True, 
                timeout=10,
                headers={'User-Agent': 'SitemapMonitor/1.0'},
                stream=True  # Stream to avoid loading entire content into memory
            )
            # Read a small amount to get status code without loading the whole content
            _ = next(response.iter_content(1024), None)
        
        redirect_url = response.url if response.url != url else None
        is_redirect = redirect_url is not None
        
        result = {
            'url': url,
            'status_code': response.status_code,
            'status_message': response.reason,
            'is_redirect': is_redirect,
            'redirect_url': redirect_url
        }
        
        # Close response and free memory
        response.close()
        
        return result
        
    except requests.Timeout:
        return {
            'url': url,
            'status_code': 0,
            'status_message': 'Timeout',
            'is_redirect': False,
            'redirect_url': None
        }
    except requests.ConnectionError:
        return {
            'url': url,
            'status_code': 0,
            'status_message': 'Connection Error',
            'is_redirect': False,
            'redirect_url': None
        }
    except Exception as e:
        return {
            'url': url,
            'status_code': 0,
            'status_message': f'Error: {str(e)}',
            'is_redirect': False,
            'redirect_url': None
        }

def check_urls_status(urls):
    """
    Check status codes for a list of URLs in parallel, with memory optimizations
    
    Args:
        urls (list): List of URLs to check
        
    Returns:
        list: List of URL status dictionaries
    """
    results = []

    # Create a ThreadPoolExecutor with a limited number of workers
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(check_url_status, url): url for url in urls}
        
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                url = future_to_url[future]
                logger.error(f"Error checking URL {url}: {str(e)}")
                results.append({
                    'url': url,
                    'status_code': 0,
                    'status_message': f'Error: {str(e)}',
                    'is_redirect': False,
                    'redirect_url': None
                })
    
    # Force garbage collection after processing batch
    gc.collect()
    
    return results

def extract_urls_generator(sitemap_url):
    """
    Generator that extracts URLs from sitemaps, handling nested sitemaps
    
    Args:
        sitemap_url (str): Starting sitemap URL
        
    Yields:
        str: Each URL found in the sitemap(s)
    """
    # Queue of sitemaps to process
    sitemap_queue = [sitemap_url]
    processed_sitemaps = set()
    
    while sitemap_queue:
        # Check memory usage periodically
        memory_mb = log_memory_usage()
        if memory_mb > MAX_MEMORY_MB:
            logger.warning(f"Memory limit reached during sitemap extraction: {memory_mb:.2f} MB")
            break
            
        current_sitemap = sitemap_queue.pop(0)
        
        # Skip if we've already processed this sitemap
        if current_sitemap in processed_sitemaps:
            continue
            
        processed_sitemaps.add(current_sitemap)
        
        try:
            # Fetch the sitemap
            response = requests.get(
                current_sitemap, 
                headers={'User-Agent': 'SitemapMonitor/1.0'}, 
                timeout=30,
                stream=True  # Stream the response to avoid loading all at once
            )
            response.raise_for_status()
            
            # Check if it's a sitemap index (contains other sitemaps)
            content_type = response.headers.get('Content-Type', '').lower()
            
            # Parse as XML
            if 'application/xml' in content_type or 'text/xml' in content_type or current_sitemap.endswith('.xml'):
                # Use iterparse for efficient memory usage
                try:
                    context = ET.iterparse(response.raw, events=('end',))
                    
                    for event, elem in context:
                        if elem.tag.endswith('loc'):
                            url = elem.text.strip() if elem.text else ""
                            
                            if url.endswith('.xml'):
                                sitemap_queue.append(url)
                            else:
                                yield url
                        
                        # Clear processed elements to save memory
                        elem.clear()
                except ET.ParseError:
                    # If iterparse fails, try alternative methods
                    logger.warning(f"XML parsing error for {current_sitemap}, trying alternative parsing")
                    response = requests.get(
                        current_sitemap, 
                        headers={'User-Agent': 'SitemapMonitor/1.0'}, 
                        timeout=30
                    )
                    
                    # Try to extract URLs using regular expressions
                    pattern = r'<loc>(.*?)</loc>'
                    import re
                    for match in re.finditer(pattern, response.text):
                        url = match.group(1)
                        if url.endswith('.xml'):
                            sitemap_queue.append(url)
                        else:
                            yield url
                
            else:
                # Try to parse as HTML - use a memory efficient approach
                content = b''
                for chunk in response.iter_content(chunk_size=8192):
                    content += chunk
                    # Limit content size to avoid memory issues
                    if len(content) > 10_000_000:  # 10MB limit
                        logger.warning(f"HTML content too large for {current_sitemap}, truncating")
                        break
                
                soup = BeautifulSoup(content, 'html.parser')
                
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    # Make relative URLs absolute
                    absolute_url = urllib.parse.urljoin(current_sitemap, href)
                    
                    if href.endswith('.xml'):
                        sitemap_queue.append(absolute_url)
                    else:
                        yield absolute_url
                
                # Clear soup and content to save memory
                del content
                soup.decompose()
                
            # Clear response to save memory
            response.close()
            del response
            
        except requests.RequestException as e:
            logger.error(f"Error fetching sitemap {current_sitemap}: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing sitemap {current_sitemap}: {str(e)}")
        
        # Force garbage collection after processing each sitemap
        gc.collect()

def calculate_statistics(results):
    """
    Calculate statistics from URL checking results with memory optimizations
    
    Args:
        results (list): List of URL status dictionaries
        
    Returns:
        dict: Statistics about the URL statuses
    """
    total = len(results)
    
    # Count by status code
    status_counts = {}
    status_categories = {
        'success': 0,  # 200-299
        'redirect': 0,  # 300-399
        'client_error': 0,  # 400-499
        'server_error': 0,  # 500-599
        'other': 0  # Anything else (like 0 for connection errors)
    }
    
    # Process one result at a time to avoid duplicate data in memory
    for result in results:
        status_code = result['status_code']
        status_counts[status_code] = status_counts.get(status_code, 0) + 1
        
        # Categorize the status code
        if 200 <= status_code < 300:
            status_categories['success'] += 1
        elif 300 <= status_code < 400:
            status_categories['redirect'] += 1
        elif 400 <= status_code < 500:
            status_categories['client_error'] += 1
        elif 500 <= status_code < 600:
            status_categories['server_error'] += 1
        else:
            status_categories['other'] += 1
    
    # Calculate percentages
    percentages = {}
    for category, count in status_categories.items():
        percentages[category] = round((count / total) * 100, 1) if total > 0 else 0
    
    return {
        'total': total,
        'status_counts': status_counts,
        'status_categories': status_categories,
        'percentages': percentages
    }

def process_sitemap(sitemap_url, max_urls=MAX_URLS, max_memory_mb=MAX_MEMORY_MB):
    """
    Process a sitemap URL, extract all URLs and check their status
    Handles nested sitemaps recursively with memory optimizations
    
    Args:
        sitemap_url (str): URL of the sitemap to process
        max_urls (int): Maximum number of URLs to process
        max_memory_mb (int): Maximum memory usage in MB
        
    Returns:
        dict: Dictionary containing the results of processing
    """
    try:
        # Validate the URL
        if not is_valid_url(sitemap_url):
            raise SitemapError(f"Invalid URL format: {sitemap_url}")
        
        start_time = time()
        logger.info(f"Starting to process sitemap: {sitemap_url}")
        log_memory_usage()
        
        # Instead of collecting all URLs first, we'll process them in batches
        # and stream the results
        all_results = []
        urls_processed = 0
        
        # Use a generator to extract URLs
        url_generator = extract_urls_generator(sitemap_url)
        
        # Process URLs in chunks
        current_chunk = []
        
        for url in url_generator:
            current_chunk.append(url)
            
            # When we have a full chunk or reached max_urls, process it
            if len(current_chunk) >= CHUNK_SIZE or (max_urls and urls_processed + len(current_chunk) >= max_urls):
                # Check memory usage before processing
                memory_mb = log_memory_usage()
                if memory_mb > max_memory_mb:
                    logger.warning(f"Memory limit reached: {memory_mb:.2f} MB. Stopping at {urls_processed} URLs.")
                    break
                
                chunk_results = check_urls_status(current_chunk)
                all_results.extend(chunk_results)
                
                urls_processed += len(current_chunk)
                logger.info(f"Processed {urls_processed} URLs so far")
                
                # Clear the chunk and force garbage collection
                current_chunk = []
                gc.collect()
                
                # Stop if we've reached the max URLs
                if max_urls and urls_processed >= max_urls:
                    logger.info(f"Reached maximum URL limit of {max_urls}")
                    break
        
        # Process any remaining URLs in the last chunk
        if current_chunk:
            memory_mb = log_memory_usage()
            if memory_mb <= max_memory_mb:
                chunk_results = check_urls_status(current_chunk)
                all_results.extend(chunk_results)
                urls_processed += len(current_chunk)
        
        # Calculate statistics
        stats = calculate_statistics(all_results)
        
        end_time = time()
        processing_time = round(end_time - start_time, 2)
        
        result = {
            'sitemap_url': sitemap_url,
            'processing_time': processing_time,
            'total_urls': len(all_results),
            'stats': stats,
            'results': all_results
        }
        
        # Force garbage collection again
        all_results = None
        gc.collect()
        log_memory_usage()
        
        return result
        
    except requests.RequestException as e:
        raise SitemapError(f"Failed to fetch sitemap: {str(e)}")
    except ET.ParseError:
        raise SitemapError(f"Failed to parse XML from sitemap: {sitemap_url}")
    except Exception as e:
        logger.error(f"Error processing sitemap: {str(e)}")
        raise SitemapError(f"Error processing sitemap: {str(e)}")
