import multiprocessing
import os

# Binding
bind = "0.0.0.0:8000"

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1  # Dynamic worker calculation
worker_class = 'gevent'  # Use 'gevent' for asynchronous workers, more suitable for high concurrency
worker_connections = 1000  # Maximum simultaneous clients per worker

# Timeout and Keep-Alive
timeout = 30  # Timeout reduced to 30 seconds for quicker failure recovery
keepalive = 5  # Increase keep-alive to 5 seconds for better performance with long connections

# Logging
accesslog = "-"
errorlog = "-"
loglevel = 'debug'

# Process naming
proc_name = 'sitemap_monitor'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL
keyfile = None
certfile = None 
