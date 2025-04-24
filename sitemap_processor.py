import aiohttp
import asyncio
import logging
import xml.etree.ElementTree as ET
import urllib.parse
from bs4 import BeautifulSoup
from time import time
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Maximum number of parallel requests (adjust based on available memory)
MAX_WORKERS = 5

# Custom exception for sitemap processing errors
class SitemapError(Exception):
    pass

async def process_sitemap(sitemap_url):
    """
    Process a sitemap URL asynchronously, extract all URLs and check their status
    Handles nested sitemaps recursively
    """
    try:
        # Validate the URL
        if not is_valid_url(sitemap_url):
            raise SitemapError(f"Invalid URL format: {sitemap_url}")
        
        start_time = time()
        logger.debug(f"Starting to process sitemap: {sitemap_url}")
        
        # Fetch and parse the sitemap asynchronously
        urls_to_check = []
        nested_sitemaps = []
        
        # Process the initial sitemap
        await _extract_urls_from_sitemap(sitemap_url, urls_to_check, nested_sitemaps)
        
        # Process any nested sitemaps
        while nested_sitemaps:
            nested_sitemap = nested_sitemaps.pop(0)
            await _extract_urls_from_sitemap(nested_sitemap, urls_to_check, nested_sitemaps)
        
        logger.debug(f"Found {len(urls_to_check)} URLs to check")
        
        # Check status of all URLs asynchronously
        results = await check_urls_status(urls_to_check)
        
        # Calculate statistics
        stats = calculate_statistics(results)
        
        end_time = time()
        processing_time = round(end_time - start_time, 2)
        
        return {
            'sitemap_url': sitemap_url,
            'processing_time': processing_time,
            'total_urls': len(results),
            'stats': stats,
            'results': results
        }
        
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

async def _extract_urls_from_sitemap(sitemap_url, urls_to_check, nested_sitemaps):
    """
    Extract URLs from a sitemap, identifying both page URLs and nested sitemaps asynchronously
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(sitemap_url, headers={'User-Agent': 'SitemapMonitor/1.0'}, timeout=30) as response:
                response.raise_for_status()

                content_type = response.headers.get('Content-Type', '').lower()
                if 'application/xml' in content_type or 'text/xml' in content_type or sitemap_url.endswith('.xml'):
                    # Parse as XML
                    root = ET.fromstring(await response.text())
                    
                    namespaces = {
                        'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                        '': ''  # Default namespace
                    }
                    
                    # Handle sitemap index
                    sitemap_tags = []
                    for ns in namespaces:
                        ns_prefix = f"{ns}:" if ns else ""
                        sitemap_tags.extend(root.findall(f'.//{ns_prefix}sitemap', namespaces))
                    
                    if sitemap_tags:
                        for sitemap_tag in sitemap_tags:
                            for ns in namespaces:
                                ns_prefix = f"{ns}:" if ns else ""
                                loc_element = sitemap_tag.find(f'./{ns_prefix}loc', namespaces)
                                if loc_element is not None and loc_element.text:
                                    nested_sitemaps.append(loc_element.text.strip())
                                    break
                    else:
                        for ns in namespaces:
                            ns_prefix = f"{ns}:" if ns else ""
                            for url_element in root.findall(f'.//{ns_prefix}url', namespaces):
                                for loc in url_element.findall(f'./{ns_prefix}loc', namespaces):
                                    if loc.text:
                                        urls_to_check.append(loc.text.strip())
                else:
                    # Parse as HTML
                    soup = BeautifulSoup(await response.text(), 'html.parser')
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        absolute_url = urllib.parse.urljoin(sitemap_url, href)
                        if href.endswith('.xml'):
                            nested_sitemaps.append(absolute_url)
                        else:
                            urls_to_check.append(absolute_url)
    except Exception as e:
        logger.error(f"Error fetching sitemap {sitemap_url}: {str(e)}")
        raise SitemapError(f"Failed to fetch sitemap {sitemap_url}: {str(e)}")

async def check_url_status(url):
    """
    Check the HTTP status code of a URL asynchronously
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, allow_redirects=False, timeout=10, headers={'User-Agent': 'SitemapMonitor/1.0'}) as response:
                if response.status == 405:  # Method Not Allowed
                    async with session.get(url, allow_redirects=True, timeout=10, headers={'User-Agent': 'SitemapMonitor/1.0'}) as response:
                        redirect_url = response.url if response.url != url else None
                        is_redirect = redirect_url is not None
                        return {
                            'url': url,
                            'status_code': response.status,
                            'status_message': response.reason,
                            'is_redirect': is_redirect,
                            'redirect_url': redirect_url
                        }
                else:
                    return {
                        'url': url,
                        'status_code': response.status,
                        'status_message': response.reason,
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

async def check_urls_status(urls):
    """
    Check status codes for a list of URLs asynchronously
    """
    # Limit the URLs to the first 50 (if needed)
    urls_to_check = urls[:50]

    results = await asyncio.gather(
        *(check_url_status(url) for url in urls_to_check)
    )
    return results

def calculate_statistics(results):
    """
    Calculate statistics from URL checking results
    """
    total = len(results)
    
    status_counts = {}
    for result in results:
        status_code = result['status_code']
        status_counts[status_code] = status_counts.get(status_code, 0) + 1
    
    status_categories = {
        'success': 0,  
        'redirect': 0,  
        'client_error': 0,  
        'server_error': 0,  
        'other': 0  
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
    
    percentages = {category: round((count / total) * 100, 1) if total > 0 else 0 for category, count in status_categories.items()}
    
    return {
        'total': total,
        'status_counts': status_counts,
        'status_categories': status_categories,
        'percentages': percentages
    }

# Run the process
async def main():
    sitemap_url = "your-sitemap-url.xml"
    result = await process_s
