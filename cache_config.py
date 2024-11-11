#cache_config.py
from flask_caching import Cache
import diskcache

# Initialize diskcache explicitly for Heroku's ephemeral storage
disk_cache = diskcache.Cache("cache-directory")  # Set directory for disk storage
cache = Cache(config={
    'CACHE_TYPE': 'FileSystemCache',  # Use file system cache, which works with DiskCache as well
    'CACHE_DIR': "cache-directory",  # Directory for disk-based caching
    'CACHE_DEFAULT_TIMEOUT': 1800,  # Cache timeout set to 30 minutes
})