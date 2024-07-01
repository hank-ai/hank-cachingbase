from functools import wraps
from cachetools import LRUCache, cached
import pickle, logging

from HANK_Caching.utils import RedisClientManager, make_hashable_key, hash_key, compress_key, decompress_key, get_function_identity

def redis_lru_cache(maxsize=1000, enabled=True, quiet=True, ttl=None, arg_transforms={}, tags=[], 
                    use_self_id:bool=False, cache_id:str=None,
                    allow_disable=True, hash_keys:bool=True, compress_keys:bool=False, **kwargs):
    """
    A decorator to cache the result of a function in a Redis cache.
    The filename, class, function, and arguments are used to create a unique key.
    The result is pickled and stored in the Redis cache.
    Prerequisites:
    - A redis database running on either:
        1) localhost:6379 or
        2) at environment variables REDIS_HOST, REDIS_PORT, REDIS_DB
        3) or a custom host, port, and db and redis_client created using those custom values
    Args:
    - redis_client: a Redis client instance .. you can generate one with CachingBase.create_redis_client()
    - maxsize: the maximum number of items to cache. default: 1000. Set to None for unlimited (sorta, still limited by Redis memory policy which should be lru)
    - enabled: whether caching is enabled
    - quiet: whether to print cache hit/miss messages
    - ttl: the time-to-live for each cache entry (in seconds)
    - arg_transforms: a dictionary of argument name -> transformation function to apply before hashing
        this is useful for doing things like converting datetime to YYYYMM or truncating zipcodes, etc so you get a more general key
    - tags: a list of tags to associate with the cache entry. this will allow you to disable or clear caches by tag using the CachingBase method clear_caches(tags=tags)
    - use_self_id: whether to include the id of the first argument (usually self) in the cache key. this is useful for instance methods where the instance state may affect the result
    - allow_disable: whether to allow the cache to be disabled. if False, the cache will always be enabled and disable_cache will be a no-op
    - compress_keys: whether to compress the keys before storing in Redis. this is useful for very long keys that may exceed the 512 byte limit in Redis
    
    """
    def decorator(func):
        nonlocal enabled, quiet, compress_keys, hash_keys, use_self_id, cache_id
        if cache_id is not None:
            cache_key_prefix = cache_id
        else:
            # Get a unique identity for the function
            func_identity = get_function_identity(func)
            cache_key_prefix = f"{func_identity}"
            if hash_keys:
                cache_key_prefix = hash_key(cache_key_prefix)
        if not cache_id: cache_id = "default"
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            if wrapper.enabled:
                key = make_hashable_key(func, args, kwargs, arg_transforms=arg_transforms, use_id=use_self_id)
                if wrapper.hash_keys:
                    key = hash_key(key)
                elif wrapper.compress_keys:
                    key = compress_key(key)
                cache_key = f"{wrapper.cache_key_prefix}:{key}"
                if not wrapper.quiet: print(f"Using cache_key: {cache_key}")
                # Try fetching the result from Redis
                result = wrapper.redis_client.get(cache_key)
                if result is not None:
                    if not wrapper.quiet: 
                        print(f" -> Cache hit!")
                        if wrapper.compress_keys: print(f"  -> Original key after : = {decompress_key(key)}")
                    
                    return pickle.loads(result)

                # Calculate the result as it's not cached
                result = func(*args, **kwargs)
                if ttl:
                    wrapper.redis_client.setex(cache_key, ttl, pickle.dumps(result))
                else:
                    # Set the result in Redis cache
                    wrapper.redis_client.set(cache_key, pickle.dumps(result))
                    
                # Maintain a list of keys for LRU behavior
                wrapper.redis_client.lpush(f"{wrapper.cache_key_prefix}:keys", cache_key)
                if maxsize and wrapper.redis_client.llen(f"{cache_key_prefix}:keys") > maxsize:
                    # Evict the oldest key
                    oldest_key = wrapper.redis_client.rpop(f"{wrapper.cache_key_prefix}:keys")
                    wrapper.redis_client.delete(oldest_key)
                return result
            else:
                return func(*args, **kwargs)
        # Custom getstate to manage the pickling process
        def __getstate__():
            state = wrapper.__dict__.copy()
            # Remove redis_client from the state before pickling
            state['redis_client'] = None
            return state

        # Custom setstate to manage the unpickling process
        def __setstate__(state):
            # Restore the redis_client after unpickling
            state['redis_client'] = RedisClientManager.get_redis_client(name=cache_id)
            wrapper.__dict__.update(state)
            
        def clear_cache(cache_key_prefix, quiet=True):
            # Get all keys from the list
            redis_client = RedisClientManager.get_redis_client(name=cache_id)
            prefix = f"{cache_key_prefix}:keys"
            if not quiet: print(f"Clearing cache with prefix {prefix} ...")
            keys = redis_client.lrange(prefix, 0, -1)
            # Delete each key
            for key in keys:
                if not quiet: print(f"Deleting key: {key}")
                redis_client.delete(key)
            # Now delete the list itself
            redis_client.delete(f"{cache_key_prefix}:keys")
        # Attach cache control methods and state to the wrapper
        # wrapper.cache = cache
        wrapper.__getstate__ = __getstate__
        wrapper.__setstate__ = __setstate__
        
        wrapper.allow_disable = allow_disable
        wrapper.enabled = enabled
        wrapper.redis_client = RedisClientManager.get_redis_client(name=cache_id)
        wrapper.cache_key_prefix = cache_key_prefix
        wrapper.compress_keys = compress_keys
        wrapper.hash_keys = hash_keys
        wrapper.quiet = quiet
        wrapper.quiet_cache = lambda quiet=True: setattr(wrapper, 'quiet', quiet)
        wrapper.cache_info = None if wrapper.redis_client is None else lambda: wrapper.redis_client.llen(f"{cache_key_prefix}:keys")
        if wrapper.redis_client is not None:
            wrapper.cache_clear = lambda **kwargs: clear_cache(wrapper.cache_key_prefix, **kwargs)
        else:
            wrapper.cache_clear = lambda: None
        wrapper.enable_cache = lambda: setattr(wrapper, 'enabled', True)
        if allow_disable:
            wrapper.disable_cache = lambda quiet=True: setattr(wrapper, 'enabled', False) or (not quiet and print(f"Disabled caching for {func.__name__}"))
        else:
            wrapper.disable_cache = lambda quiet=True: None
        wrapper.disable_cache_and_clear = lambda quiet=True: wrapper.cache_clear(quiet=quiet) or wrapper.disable_cache(quiet=quiet)
        wrapper.tags = set(tags)


        return wrapper
    return decorator


def conditional_lru_cache(enabled=True, maxsize=128, arg_transforms={}, tags=[], quiet=True, allow_disable=True, thread_safe=False,
                          cache_id:str=None, use_self_id:bool=False, **kwargs):
    # from threading import RLock

    if maxsize is None:
        maxsize = 1000000
    cache = LRUCache(maxsize)
    
    def decorator(func):
        nonlocal enabled, quiet, allow_disable, thread_safe, cache, arg_transforms, tags, use_self_id, cache_id
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            if wrapper.enabled:
                custom_key = lambda *a, **kw: make_hashable_key(func, a, kw, arg_transforms=arg_transforms, prefix=cache_id, use_id=use_self_id) 
                # print(f"Using custom key: {custom_key(*args, **kwargs)} in {func.__name__} ...")
                # if thread_safe and wrapper.lock:
                #     with wrapper.lock:
                #         return cached(cache, key=custom_key)(func)(*args, **kwargs)
                # else:
                return cached(cache, key=custom_key)(func)(*args, **kwargs)
            else:
                return func(*args, **kwargs)
            
        # Attach cache control methods and state to the wrapper
        wrapper.cache = cache
        wrapper.allow_disable = allow_disable
        wrapper.enabled = enabled
        wrapper.quiet = quiet
        # wrapper.lock = RLock() if thread_safe else None
        # wrapper.__getstate__ = __getstate__
        # wrapper.__setstate__ = __setstate__
        wrapper.thread_safe = thread_safe
        wrapper.cache_info = lambda: cache.currsize
        wrapper.cache_clear = lambda **kwargs: cache.clear()
        wrapper.quiet_cache = lambda quiet=True: setattr(wrapper, 'quiet', quiet)
        wrapper.enable_cache = lambda: setattr(wrapper, 'enabled', True)
        if allow_disable:
            wrapper.disable_cache = lambda quiet=True: setattr(wrapper, 'enabled', False) or (not quiet and print(f"Disabled caching for {func.__name__}"))
        else:
            wrapper.disable_cache = lambda quiet=True: None
        wrapper.disable_cache_and_clear = lambda quiet=True: wrapper.cache_clear(quiet=quiet) or wrapper.disable_cache(quiet=quiet)
        wrapper.tags = set(tags)

        return wrapper

    return decorator
