import os
import logging
from flask import Flask, request, jsonify, render_template, send_file
from sitemap_processor import process_sitemap, SitemapError
import traceback

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET") or "sitemap-monitor-secret-key"

@app.route('/health')
def health_check():
    """Health check endpoint that always returns 200 OK"""
    return jsonify({
        "status": "healthy",
        "message": "Service is running"
    }), 200

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
        
        # Process the sitemap
        logger.debug(f"Processing sitemap URL: {sitemap_url}")
        result = process_sitemap(sitemap_url)
        
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
    app.run(host='0.0.0.0', port=5000, debug=True)
