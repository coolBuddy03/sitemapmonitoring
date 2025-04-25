import os
import logging
import psutil
from flask import Flask, request, jsonify, render_template, send_file
from sitemap_processor import process_sitemap, SitemapError
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET") or "sitemap-monitor-secret-key"

# Environment configuration with defaults
MAX_URLS =  5000
MAX_MEMORY_MB =  500

def log_memory_usage():
    """Log current memory usage"""
    process = psutil.Process()
    memory_info = process.memory_info()
    memory_mb = memory_info.rss / 1024 / 1024
    logger.info(f"Memory usage: {memory_mb:.2f} MB")
    return memory_mb

@app.route('/health')
def health_check():
    """Health check endpoint that always returns 200 OK"""
    return jsonify({
        "status": "healthy",
        "message": "Service is running"
    }), 200

@app.route('/memory')
def memory_check():
    """Endpoint to check current memory usage"""
    memory_mb = log_memory_usage()
    return jsonify({
        "memory_usage_mb": round(memory_mb, 2),
        "max_memory_mb": MAX_MEMORY_MB,
        "status": "ok" if memory_mb < MAX_MEMORY_MB else "warning"
    })

@app.route('/')
def index():
    """Render the main dashboard page"""
    return render_template('index.html')

@app.route('/process_sitemap', methods=['POST'])
def process_sitemap_request():
    """
    Process a sitemap URL submitted by the user
    Checks all URLs within the sitemap and returns their status codes
    """
    try:
        # Get the sitemap URL from the request
        sitemap_url = request.json.get('sitemap_url')
        if not sitemap_url:
            return jsonify({'error': 'No sitemap URL provided'}), 400
        
        # Get optional parameters with defaults
        max_urls = request.json.get('max_urls', MAX_URLS)
        
        # Log memory usage before processing
        log_memory_usage()
        
        # Process the sitemap
        logger.info(f"Processing sitemap URL: {sitemap_url} with max_urls={max_urls}")
        result = process_sitemap(sitemap_url, max_urls=max_urls, max_memory_mb=MAX_MEMORY_MB)
        
        # Log memory usage after processing
        log_memory_usage()
        
        # Return the results
        return jsonify(result)
    
    except SitemapError as e:
        logger.error(f"Sitemap processing error: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': 'An unexpected error occurred'}), 500

@app.route('/download_zip')
def download_zip():
    """Download the zip file of the project"""
    # Recreate the zip file to ensure it's fresh
    import subprocess
    try:
        # Create a fresh copy of the project files
        subprocess.run("mkdir -p /tmp/sitemap_monitor", shell=True)
        subprocess.run("cp -r app.py main.py sitemap_processor.py templates/ static/ /tmp/sitemap_monitor/", shell=True)
        subprocess.run("cd /tmp && zip -r sitemap_monitor.zip sitemap_monitor", shell=True)
        
        zip_path = '/tmp/sitemap_monitor.zip'
        if os.path.exists(zip_path):
            return send_file(zip_path, as_attachment=True, download_name='sitemap_monitor.zip')
        else:
            return 'Failed to create zip file', 500
    except Exception as e:
        logger.error(f"Error creating zip file: {str(e)}")
        return f'Error creating zip file: {str(e)}', 500

if __name__ == '__main__':
    # Set debug to False in production
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
