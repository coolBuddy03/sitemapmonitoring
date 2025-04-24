import multiprocessing

# Binding
bind = "0.0.0.0:5000"

# Worker processes
workers = 4  # Start with 2 workers, adjust as needed
worker_class = 'gevent'  # Use gevent for async workers (lighter on memory)
worker_connections = 500  # Lower connection limit to conserve memory
timeout = 300  # Increase timeout to handle longer-running requests
keepalive = 2

# Logging
accesslog = '/opt/logs/access.log'
errorlog = '/opt/logs/error.log'
loglevel = 'debug'  # Debug logging for more visibility

# Process naming
proc_name = 'sitemap_monitor'

# Server mechanics
daemon = True  # Let Gunicorn daemonize the process in production
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
keyfile = None
certfile = None

# Worker management
max_requests = 1000  # Restart workers periodically
max_requests_jitter = 50  # Add jitter to avoid restarting all workers at once
