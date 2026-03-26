"""
Offline Manager - MongoDB-Only Architecture
Handles automatic fallback between primary and local MongoDB instances
"""
from pymongo import MongoClient
from datetime import datetime
import threading
import time
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env to get DB names
_base = Path(__file__).resolve().parent.parent.parent
load_dotenv(_base / ".env")

class OfflineManager:
    """Singleton class for managing offline operations"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
        primary_db_name = os.environ.get('DB_NAME', 'restaurant_pos')
        local_db_name = os.environ.get('LOCAL_DB_NAME', 'restaurant_pos_local')

        # Primary MongoDB (server/cloud)
        try:
            self.primary_client = MongoClient(
                mongo_uri,
                serverSelectionTimeoutMS=2000
            )
            self.primary_db = self.primary_client[primary_db_name]
        except Exception as e:
            print(f"[WARN] OfflineManager: primary client init failed: {e}")
            self.primary_client = None
            self.primary_db = None

        # Local MongoDB (always available)
        self.local_client = MongoClient(mongo_uri)
        self.local_db = self.local_client[local_db_name]
        
        self.is_online = self.check_connection()
        self.start_sync_worker()
        self._initialized = True
    
    def check_connection(self):
        """Check if primary MongoDB is reachable"""
        if self.primary_client is None:
            return False
        try:
            self.primary_client.admin.command('ping')
            return True
        except Exception:
            return False
    
    def insert_order(self, order_data):
        """Insert order with automatic offline fallback"""
        try:
            if self.is_online and self.primary_db is not None:
                # Save to primary
                result = self.primary_db.orders.insert_one(order_data)
                # Cache locally
                self.local_db.orders.insert_one(order_data)
                return result.inserted_id
            else:
                # Offline: save locally + queue for sync
                result = self.local_db.orders.insert_one(order_data)
                
                self.local_db.sync_queue.insert_one({
                    "operation": "insert",
                    "collection": "orders",
                    "document": order_data,
                    "timestamp": datetime.now(),
                    "synced": False,
                    "retry_count": 0
                })
                
                return result.inserted_id
                
        except Exception as e:
            # Primary failed - switch to offline and save locally
            print(f"[WARN] insert_order: primary failed ({e}), switching to offline")
            self.is_online = False
            result = self.local_db.orders.insert_one(order_data)
            self.local_db.sync_queue.insert_one({
                "operation": "insert",
                "collection": "orders",
                "document": order_data,
                "timestamp": datetime.now(),
                "synced": False,
                "retry_count": 0
            })
            return result.inserted_id
    
    def update_order(self, filter_dict, update_dict):
        """Update with offline support"""
        try:
            if self.is_online and self.primary_db is not None:
                self.primary_db.orders.update_one(filter_dict, update_dict)
                self.local_db.orders.update_one(filter_dict, update_dict)
            else:
                self.local_db.orders.update_one(filter_dict, update_dict)
                
                self.local_db.sync_queue.insert_one({
                    "operation": "update",
                    "collection": "orders",
                    "filter": filter_dict,
                    "update": update_dict,
                    "timestamp": datetime.now(),
                    "synced": False,
                    "retry_count": 0
                })
        except Exception as e:
            # Primary failed - switch to offline and update locally
            print(f"[WARN] update_order: primary failed ({e}), switching to offline")
            self.is_online = False
            self.local_db.orders.update_one(filter_dict, update_dict)
            self.local_db.sync_queue.insert_one({
                "operation": "update",
                "collection": "orders",
                "filter": filter_dict,
                "update": update_dict,
                "timestamp": datetime.now(),
                "synced": False,
                "retry_count": 0
            })
    
    def find_orders(self, query=None):
        """Always read from local (fast)"""
        query = query or {}
        return list(self.local_db.orders.find(query))
    
    def sync_pending_operations(self):
        """Sync queued operations to primary"""
        if not self.is_online or self.primary_db is None:
            return
        
        pending = self.local_db.sync_queue.find({"synced": False})
        
        for item in pending:
            try:
                collection = self.primary_db[item['collection']]
                
                if item['operation'] == 'insert':
                    # Check if already exists
                    if not collection.find_one({"_id": item['document']['_id']}):
                        collection.insert_one(item['document'])
                    
                elif item['operation'] == 'update':
                    collection.update_one(
                        item['filter'],
                        item['update']
                    )
                
                # Mark as synced
                self.local_db.sync_queue.update_one(
                    {"_id": item['_id']},
                    {"$set": {"synced": True}}
                )
                
            except Exception as e:
                # Increment retry count
                self.local_db.sync_queue.update_one(
                    {"_id": item['_id']},
                    {
                        "$inc": {"retry_count": 1},
                        "$set": {"error": str(e)}
                    }
                )
    
    def start_sync_worker(self):
        """Background sync every 30 seconds"""
        def worker():
            while True:
                time.sleep(30)  # Wait 30 seconds
                self.is_online = self.check_connection()
                if self.is_online:
                    try:
                        self.sync_pending_operations()
                    except Exception as e:
                        print(f"[WARN] sync worker error: {e}")
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
    
    def get_pending_count(self):
        """Get number of unsynced operations"""
        return self.local_db.sync_queue.count_documents({"synced": False})
    
    def get_status(self):
        """Get connection status info"""
        return {
            "is_online": self.is_online,
            "pending_syncs": self.get_pending_count()
        }
