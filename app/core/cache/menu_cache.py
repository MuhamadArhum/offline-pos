"""
Simple In-Memory Cache for Menu Items
Caches menu for 5 minutes to avoid repeated database queries
"""
from datetime import datetime, timedelta

from app.core.database import menu_col


class MenuCache:
    """Singleton cache for menu items"""
    _instance = None
    _cache = None
    _cache_time = None
    _cache_duration = timedelta(minutes=5)
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_menu(self):
        """Get menu from cache or database"""
        now = datetime.now()
        
        # Check if cache is valid
        if self._cache is not None and self._cache_time is not None:
            if now - self._cache_time < self._cache_duration:
                return self._cache
        
        # Cache miss or expired - fetch from database
        self._cache = list(menu_col.find({"available": True}))
        self._cache_time = now
        return self._cache
    
    def invalidate(self):
        """Clear cache (call when menu is updated)"""
        self._cache = None
        self._cache_time = None
