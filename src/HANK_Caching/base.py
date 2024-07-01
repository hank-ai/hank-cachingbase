#%%
from HANK_Caching.decorators import redis_lru_cache, conditional_lru_cache
from HANK_Caching.utils import RedisClientManager
import time, datetime, random, logging


class CachingBase:
    SENTINEL = object()
    
    def __init__(self, caches_enabled=True, cached_methods:list=None, quiet=True):
        self.quiet = quiet
        self._cached_methods = cached_methods if cached_methods else []
        self.caches_enabled=caches_enabled
        
        if hasattr(self, 'func_cache_map'):
            self._cached_methods = self.initialize_caching(self.func_cache_map, quiet=self.quiet)
            
        if not caches_enabled:
            self.disable_caching(quiet=self.quiet)
    
    def initialize_caching(self, function_cache_map:dict=None, override_dict:dict=None, quiet=None):
        """
        Initialize caching for all methods in function_cache_map.
        Args:
            function_cache_map: dict. A dictionary of method names and their caching configurations. If not provided, the instance's func_cache_map attribute will be used.
            override_dict: dict. Optional dictionary of configuration overrides which will override any matching keys in the function_cache_map values dict.
            quiet: bool. Suppress printouts.
        """
        quiet = quiet if quiet is not None else self.quiet
        if function_cache_map is None:
            if not hasattr(self, 'func_cache_map'):
                raise AttributeError("No function_cache_map provided and no func_cache_map attribute found.")
            function_cache_map = self.func_cache_map
            
        cached_methods = []
        for func_name, config in function_cache_map.items():
            func = getattr(self, func_name)
            if func is None:
                raise AttributeError(f"Method '{func_name}' not found in class {self.__class__.__name__}")
            #pop the decorator
            config = config.copy()
            if override_dict:
                config.update(override_dict)
            if not quiet: print(f"Initializing caching for {func_name} ({id(func)}) with config: {config} ...")

            decorator = config.pop('decorator', conditional_lru_cache)
                    
            decorated_func = decorator(**config)(func)
            setattr(self, func_name, decorated_func)
            #if method doesn't have a __ORIGINAL_ attribute, store the original method
            if not hasattr(self, f"__ORIGINAL_{func_name}"):
                if not quiet: print(f" -> Storing original method for {func_name} as __ORIGINAL_{func_name}")
                setattr(self, f"__ORIGINAL_{func_name}", func)
            #cached_methods.append(getattr(self, func.__name__))
            cached_methods.append(func_name)
        return cached_methods
    
    def remove_caching(self, tags=[], quiet=None, remove_originals=False):
        """Remove caching from all lru_cache methods."""
        quiet = quiet if quiet is not None else self.quiet
        if not hasattr(self, '_cached_methods') or not self._cached_methods:
            if hasattr(self, 'func_cache_map'):
                if not quiet: print(f"No cached methods found. Trying to remove based on keys in func_cache_map ({list(self.func_cache_map.keys())}) ..." )
                self._cached_methods = list(self.func_cache_map.keys())
            else:
                if not quiet: print("No cached methods found. Nothing to remove.")
            return
        remaining_caches = []
        if not quiet: 
            print(f"Removing caching from {self.__class__.__name__}, tags = {tags} ...")
            print(f" -> all cached methods: {self._cached_methods}")
        for method_name in self._cached_methods:
            method = getattr(self, method_name)
            if not tags or method.tags.intersection(tags):
                # Retrieve the original method and replace the decorated method
                if hasattr(self, f"__ORIGINAL_{method_name}"):
                    original_method = getattr(self, f"__ORIGINAL_{method_name}")
                    setattr(self, method_name, original_method)
                    #optionally remove the orginal method
                    if remove_originals: delattr(self, f"__ORIGINAL_{method_name}")
                if not quiet: print(f"Removed caching from {method.__name__}")
            else:
                remaining_caches.append(method_name)
        self._cached_methods = remaining_caches
                                   
    def __str__(self):
        out = f"{self.__class__.__name__} with {len(self._cached_methods)} cached methods:"
        for method_name in self._cached_methods:
            method = getattr(self, method_name)
            enabled = method.enabled if hasattr(method, 'enabled') else None
            cache_info = method.cache_info() if hasattr(method, 'cache_info') else None
            out += f"\n-> {method.__name__}: id={id(method)}. enabled={enabled}. cacheinfo={cache_info}"
        return out

    def clear_caches(self, tags=[], quiet=None, gc=False):
        """Clear all lru_cache caches."""
        import gc
        quiet = quiet if quiet is not None else self.quiet
        for method_name in self._cached_methods:
            method = getattr(self, method_name)
            if not tags or method.tags.intersection(tags):
                method.cache_clear(quiet=quiet)
        if gc: gc.collect()
    
    def remove_locks(self, tags=[], quiet=None):
        """Remove locks from all lru_cache methods."""
        quiet = quiet if quiet is not None else self.quiet
        for method_name in self._cached_methods:
            method = getattr(self, method_name)
            if not tags or method.tags.intersection(tags):
                if getattr(method, 'lock', None):
                    method.lock = None
                    if not quiet: print(f"Removed lock from {method.__name__}")
                    
    def disable_caching(self, clear_cache:bool=False, tags=[], quiet=None):
        """Disable caching for all lru_cache methods."""
        quiet = quiet if quiet is not None else self.quiet
        if not quiet: print(f"Disabling caching for {self.__class__.__name__}, tags = {tags} ...")
        for method_name in self._cached_methods:
            method = getattr(self, method_name)
            if not quiet: print(f" -> Disabling caching for {method.__name__}, id={id(method)} ...")
            if method.enabled and (not tags or method.tags.intersection(tags)):
                if clear_cache:
                    method.cache_clear(quiet=quiet)
                method.disable_cache(quiet=quiet)
                
            # original_method = method.__wrapped__
            # wrapped_method = conditional_lru_cache(enabled=False)(original_method)
            # setattr(self, method_name, wrapped_method.__get__(self, self.__class__))

    def enable_caching(self, tags=[], quiet=None):
        """Enable caching for all lru_cache methods."""  
        quiet = quiet if quiet is not None else self.quiet
        if not quiet: print(F"Enabling caching for {self.__class__.__name__}, tags = {tags}...")
        for method_name in self._cached_methods:
            method = getattr(self, method_name)
            if not quiet: print(f" -> Enabling caching for {method.__name__}, id={id(method)} ...")
            if not method.enabled and (not tags or method.tags.intersection(tags)):
                method.enable_cache()
            # original_method = method.__wrapped__
            # wrapped_method = conditional_lru_cache(enabled=True)(original_method)
            # setattr(self, method_name, wrapped_method.__get__(self, self.__class__))

    def disable_caches_and_force_gc(self, tags=[], quiet=None):
        """Clear all lru_cache caches and force garbage collection."""
        quiet = quiet if quiet is not None else self.quiet
        import gc
        self.disable_caching(clear_cache=True, tags=tags, quiet=quiet)
        gc.collect()  # Force garbage collection

    def quiet_caches(self, quiet=None, tags=[]):
        """Disable or enable cache printouts for all lru_cache methods."""
        quiet = True if quiet is None else self.quiet
        for method_name in self._cached_methods:
            method = getattr(self, method_name)
            if not tags or method.tags.intersection(tags):
                #print(f"Turning quiet mode {'on' if quiet else 'off'} for {method_name}")
                method.quiet_cache(quiet=quiet)
                    
    