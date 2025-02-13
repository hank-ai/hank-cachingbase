from collections.abc import Mapping, Iterable
from cachetools.keys import hashkey

import inspect, pickle, logging, time

SENTINEL = object()
class RedisClientManager:
    clients = {}
    redis_is_available = True
    last_retry_time = 0
    RETRY_INTERVAL_SEC = 300  # 5 minutes

    @staticmethod
    def get_redis_client(name="default", host=SENTINEL, port=SENTINEL, db=SENTINEL, raise_on_error=False, 
                         check_connection=True, **kwargs):
        """
        Create a Redis client instance. 
        If host, port, or db are not provided, use environment variables. 
        -> If environment variables are not set, use default values of localhost, 6379, and 0 respectively.

        Args:
          - name: str. A name to identify the client. Useful for multiple clients.
          - host: str. The Redis host. Default: 'localhost'
          - port: int. The Redis port. Default: 6379
          - db: int. The Redis database. Default: 0
          - raise_on_error: bool. Whether to raise an error if the client cannot connect.
          - check_connection: bool. Whether to ping Redis before returning the client.
        """

        # If we have previously marked Redis unavailable:
        if not RedisClientManager.redis_is_available:
            now = time.time()
            # Check if it's time to attempt reconnect
            if now - RedisClientManager.last_retry_time < RedisClientManager.RETRY_INTERVAL_SEC:
                # Not time yet; skip trying again and just return None
                logging.info("Redis is not available, skipping retry until interval has passed...")
                return None
            else:
                # Enough time has passed, let's attempt a reconnect below.
                logging.info("Retrying Redis connection...")

        import os
        try:
            import redis
        except ImportError:
            logging.error("Please install the 'redis' package using 'pip install redis'")
            if raise_on_error:
                raise ImportError("Please install the 'redis' package using 'pip install redis'")
            else:
                return None

        if host is SENTINEL:
            host = os.getenv('REDIS_HOST', 'localhost')
        if port is SENTINEL:
            port = os.getenv('REDIS_PORT', 6379)
        if db is SENTINEL:
            db = os.getenv('REDIS_DB', 0)

        # If we have a client already and haven't changed any settings, just return it
        if name in RedisClientManager.clients and RedisClientManager.redis_is_available:
            return RedisClientManager.clients[name]

        # Otherwise, we create (or recreate) a client and optionally ping it
        r = redis.Redis(host=host, port=port, db=db, **kwargs)
        if check_connection:
            try:
                # Attempt a quick connection check
                redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    socket_connect_timeout=1
                ).ping()
                # If we succeed, mark available
                RedisClientManager.redis_is_available = True
            except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
                logging.error(f"Error connecting to Redis: {e}")
                RedisClientManager.redis_is_available = False
                # update last_retry_time to now
                RedisClientManager.last_retry_time = time.time()
                if raise_on_error:
                    raise e
                else:
                    return None

        RedisClientManager.clients[name] = r
        return r

def make_hashable(o):
    """ Use a non-recursive approach for common types for efficiency. """
    if isinstance(o, (int, float, str, bool, type(None))):
        return o
    elif isinstance(o, Mapping):
        return frozenset((k, make_hashable(v)) for k, v in sorted(o.items()))
    elif isinstance(o, Iterable) and not isinstance(o, (str, bytes)):
        return tuple(make_hashable(e) for e in o)
    return o  # Fallback for unhashable types

def hash_key(raw_key:str):
    import hashlib
    if not isinstance(raw_key, str):
        raw_key = str(raw_key)
    return hashlib.md5(raw_key.encode('utf-8')).hexdigest()

def compress_key(raw_key:str):
    import zlib, base64
    if isinstance(raw_key, str):
        raw_key = raw_key.encode('utf-8')
    else:
        raw_key = str(raw_key).encode('utf-8')
    compressed = zlib.compress(raw_key)
    return base64.b64encode(compressed).decode('utf-8')

def decompress_key(compressed_key:str):
    import zlib, base64
    compressed = base64.b64decode(compressed_key.encode('utf-8'))
    return zlib.decompress(compressed).decode('utf-8')

def make_hashable_key(func, args, kwargs, prefix:str=None, arg_transforms=None, use_id=True):
    """Create a hashable key from args and kwargs, applying transformations as needed."""
    # Pre-calculate parameter names for transformation
    self_id = id(args[0]) if args else 0
    args = inspect.signature(func).bind(*args, **kwargs)
    args.apply_defaults()
    args = {k:v for k,v in args.arguments.items() if k != "self" and k != 'kwargs'}
    #combine args and kwargs, not including the kwargs item by itself
    args.update(kwargs)
    # print(args)
    if arg_transforms:
        for arg, transform in arg_transforms.items():
            if arg in args:
                args[arg] = transform(args[arg])
            # if arg in kwargs:
            #     kwargs[arg] = transform(kwargs[arg])
    pf = f"{prefix}" if prefix else ""
    sid = f"{self_id}" if use_id else ""
    return hashkey(f"{sid}{pf}{args}")
    
def get_function_identity(func):
    """Get a unique identifier for the function including filename, class, and function name."""
    func_file = inspect.getfile(func)
    if hasattr(func, '__qualname__'):
        qualname = func.__qualname__
    else:
        qualname = func.__name__
    return f"{func_file}:{qualname}"