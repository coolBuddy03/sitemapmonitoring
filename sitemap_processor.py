import requests
import logging
import xml.etree.ElementTree as ET
import urllib.parse
import concurrent.futures
from bs4 import BeautifulSoup
from time import time
from urllib.parse import urlparse
import psutil
import os

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Maximum number of parallel requests
MAX_WORKERS = 5
BATCH_SIZE = 25  # Adjust this depending on your memory limits

# Custom exception for sitemap processing errors
class SitemapError(Exception):
    pass

def log_memory(tag=""):
    """Log memory usage at a specific point."""
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss / 1024 / 1024  # In MB
    logger.debug(f"[MEMORY] {tag} - {mem:.2f} MB")

def process_sitemap(sitemap_url):
    """
    Process a sitemap URL, extract all URLs and check their status
    Handles nested sitemaps recursively
    
    Args:
        sitemap_url (str): URL of the sitemap to process
        
    Returns:
        dict: Dictionary containing the results of processing
    """
    try:
        # Validate the URL
        if not is_valid_url(sitemap_url):
            raise SitemapError(f"Invalid URL format: {sitemap_url}")
        
        start_time = time()
        logger.debug(f"Starting to process sitemap: {sitemap_url}")
        
        # Fetch and parse the sitemap
        urls_to_check = []
        nested_sitemaps = []
        
        # Process the initial sitemap
        _extract_urls_from_sitemap(sitemap_url, urls_to_check, nested_sitemaps)
        
        # Process any nested sitemaps
        while nested_sitemaps:
            nested_sitemap = nested_sitemaps.pop(0)
            _extract_urls_from_sitemap(nested_sitemap, urls_to_check, nested_sitemaps)

        logger.debug(f"Found {len(urls_to_check)} URLs to check")
        log_memory("Before URL status checking")

        # Check status of all URLs in parallel with batching
        results = check_urls_in_batches(urls_to_check)
        
        # Calculate statistics
        stats = calculate_statistics(results)
        
        end_time = time()
        processing_time = round(end_time - start_time, 2)
        log_memory("After URL status checking")
        
        return {
            'sitemap_url': sitemap_url,
            'processing_time': processing_time,
            'total_urls': len(results),
            'stats': stats,
            'results': results
        }
        
    except requests.RequestException as e:
        raise SitemapError(f"Failed to fetch sitemap: {str(e)}")
    except ET.ParseError:
        raise SitemapError(f"Failed to parse XML from sitemap: {sitemap_url}")
    except Exception as e:
        logger.error(f"Error processing sitemap: {str(e)}")
        raise SitemapError(f"Error processing sitemap: {str(e)}")

def is_valid_url(url):
    """Check if a URL is valid"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def _extract_urls_from_sitemap(sitemap_url, urls_to_check, nested_sitemaps):
    """
    Extract URLs from a sitemap, identifying both page URLs and nested sitemaps
    
    Args:
        sitemap_url (str): URL of the sitemap to process
        urls_to_check (list): List to append page URLs to
        nested_sitemaps (list): List to append nested sitemap URLs to
    """
    try:
        # Fetch the sitemap
        response = requests.get(sitemap_url, headers={'User-Agent': 'SitemapMonitor/1.0'}, timeout=30)
        response.raise_for_status()
        
        # Check if it's a sitemap index (contains other sitemaps)
        content_type = response.headers.get('Content-Type', '').lower()
        
        # Parse as XML
        if 'application/xml' in content_type or 'text/xml' in content_type or sitemap_url.endswith('.xml'):
            root = ET.fromstring(response.content)
            
            # Handle different XML namespaces
            namespaces = {
                'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                '': ''  # Default namespace
            }
            
            # Check for sitemap index
            sitemap_tags = []
            for ns in namespaces:
                ns_prefix = f"{ns}:" if ns else ""
                sitemap_tags.extend(root.findall(f'.//{ns_prefix}sitemap', namespaces))
            
            if sitemap_tags:
                # This is a sitemap index
                for sitemap_tag in sitemap_tags:
                    for ns in namespaces:
                        ns_prefix = f"{ns}:" if ns else ""
                        loc_element = sitemap_tag.find(f'./{ns_prefix}loc', namespaces)
                        if loc_element is not None and loc_element.text:
                            nested_sitemaps.append(loc_element.text.strip())
                            break
            else:
                # This is a regular sitemap
                for ns in namespaces:
                    ns_prefix = f"{ns}:" if ns else ""
                    for url_element in root.findall(f'.//{ns_prefix}url', namespaces):
                        for loc in url_element.findall(f'./{ns_prefix}loc', namespaces):
                            if loc.text:
                                urls_to_check.append(loc.text.strip())
        else:
            # Try to parse as HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.endswith('.xml'):
                    # Make relative URLs absolute
                    absolute_url = urllib.parse.urljoin(sitemap_url, href)
                    nested_sitemaps.append(absolute_url)
                else:
                    # Make relative URLs absolute
                    absolute_url = urllib.parse.urljoin(sitemap_url, href)
                    urls_to_check.append(absolute_url)
    
    except requests.RequestException as e:
        logger.error(f"Error fetching sitemap {sitemap_url}: {str(e)}")
        raise SitemapError(f"Failed to fetch sitemap {sitemap_url}: {str(e)}")
    except ET.ParseError:
        logger.warning(f"XML parsing error for {sitemap_url}, trying alternative parsing")
        # If XML parsing fails, try to extract URLs using regular expressions
        try:
            pattern = r'<loc>(.*?)</loc>'
            import re
            urls = re.findall(pattern, response.text)
            for url in urls:
                if url.endswith('.xml'):
                    nested_sitemaps.append(url)
                else:
                    urls_to_check.append(url)
        except Exception as e:
            raise SitemapError(f"Failed to parse sitemap {sitemap_url}: {str(e)}")

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
                headers={'User-Agent': 'SitemapMonitor/1.0'}
            )
        
        redirect_url = response.url if response.url != url else None
        is_redirect = redirect_url is not None
        
        return {
            'url': url,
            'status_code': response.status_code,
            'status_message': response.reason,
            'is_redirect': is_redirect,
            'redirect_url': redirect_url
        }
        
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

def check_urls_in_batches(urls):
    """Process URLs in memory-efficient batches."""
    results = []
    for i in range(0, len(urls), BATCH_SIZE):
        batch = urls[i:i + BATCH_SIZE]
        logger.debug(f"Processing batch {i // BATCH_SIZE + 1} of {(len(urls) + BATCH_SIZE - 1) // BATCH_SIZE}")
        batch_results = check_urls_status(batch)
        results.extend(batch_results)
        log_memory(f"After batch {i // BATCH_SIZE + 1}")
    return results

def calculate_statistics(results):
    """
    Calculate statistics from URL checking results
    
    Args:
        results (list): List of URL status dictionaries
        
    Returns:
        dict: Statistics about the URL statuses
    """
    total = len(results)
    
    # Count by status code
    status_counts = {}
    for result in results:
        status_code = result['status_code']
        status_counts[status_code] = status_counts.get(status_code, 0) + 1
    
    # Group by status code category
    status_categories = {
        'success': 0,  # 200-299
        'redirect': 0,  # 300-399
        'client_error': 0,  # 400-499
        'server_error': 0,  # 500-599
        'other': 0  # Anything else (like 0 for connection errors)
    }
    
    for status_code, count in status_counts.items():
        if 200 <= status_code < 300:
            status_categories['success'] += count
        elif 300 <= status_code < 400:
            status_categories['redirect'] += count
        elif 400 <= status_code < 500:
            status_categories['client_error'] += count
        elif 500 <= status_code < 600:
            status_categories['server_error'] += count
        else:
            status_categories['other'] += count
    
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

# Entry point or an example of calling process_sitemap
if __name__ == '__main__':
    sitemap_url = 'https://example.com/sitemap.xml'
    result = process_sitemap(sitemap_url)
    print(result)
