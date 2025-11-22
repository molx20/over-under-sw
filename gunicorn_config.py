# Gunicorn Configuration for Railway Deployment

# Worker timeout (10 minutes to handle slow NBA API calls)
# Railway has 10min request timeout, so we set worker timeout to 9 minutes
timeout = 540  # 9 minutes in seconds

# Number of worker processes
workers = 2

# Worker class
worker_class = 'sync'

# Bind to Railway's PORT
bind = "0.0.0.0:8080"

# Logging
accesslog = '-'  # Log to stdout
errorlog = '-'   # Log to stderr
loglevel = 'info'

# Keep-alive
keepalive = 5

# Graceful timeout for workers
graceful_timeout = 120

# Max requests per worker (restart after N requests to prevent memory leaks)
max_requests = 1000
max_requests_jitter = 100

print("[gunicorn] Configuration loaded:")
print(f"  - Worker timeout: {timeout}s (9 minutes)")
print(f"  - Workers: {workers}")
print(f"  - Graceful timeout: {graceful_timeout}s")
