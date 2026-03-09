
import os
import pymongo
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class DBManager:
    """
    Handles MongoDB operations for the Customer Support AI.
    """
    
    def __init__(self):
        self.mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        self.db_name = os.getenv("DB_NAME", "customer_support_db")
        self.collection_name = os.getenv("COLLECTION_NAME", "conversations")
        
        try:
            self.client = pymongo.MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            # Trigger a connection to verify
            self.client.server_info()
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            print(f"✅ Connected to MongoDB: {self.db_name}.{self.collection_name}")
        except Exception as e:
            print(f"⚠️  MongoDB Connection Failed: {e}")
            self.client = None
            self.db = None
            self.collection = None

    def is_connected(self) -> bool:
        return self.client is not None

    def insert_message(self, 
                       session_id: str, 
                       user_raw: str, 
                       user_masked: str, 
                       bot_masked: str, 
                       bot_final: str, 
                       pii_mapping: Dict) -> str:
        """
        Insert a new conversation turn into the database.
        """
        if not self.is_connected():
            return None
            
        document = {
            "session_id": session_id,
            "timestamp": datetime.utcnow(),
            "user_input": {
                "raw": user_raw,  # In a real prod app, you might want to encrypt this field specifically if DB isn't encrypted at rest
                "masked": user_masked
            },
            "bot_response": {
                "masked": bot_masked,
                "final": bot_final
            },
            "pii_mapping": pii_mapping  # Stored to allow reconstruction if needed
        }
        
        try:
            result = self.collection.insert_one(document)
            return str(result.inserted_id)
        except Exception as e:
            print(f"❌ Error inserting into MongoDB: {e}")
            return None

    def get_history(self, limit: int = 50) -> List[Dict]:
        """
        Retrieve conversation history, sorted by latest first.
        """
        if not self.is_connected():
            return []
            
        try:
            cursor = self.collection.find().sort("timestamp", pymongo.DESCENDING).limit(limit)
            
            history = []
            for doc in cursor:
                # Convert ObjectId to str for JSON serialization
                doc["_id"] = str(doc["_id"])
                history.append(doc)
            
            # Return reversed so it reads chronologically (Oldest -> Newest) if needed, 
            # but usually for reports we might want Newest -> Oldest or vice versa.
            # Let's return Newest -> Oldest as per sort.
            return list(history)
        except Exception as e:
            print(f"❌ Error retrieving history: {e}")
            return []

    def get_session_history_for_llm(self, session_id: str, limit: int = 10) -> List[Dict]:
        """
        Get recent chat history for a specific session to feed back to LLM context.
        """
        if not self.is_connected():
            return []
            
        # Implementation depends on how we want to format this for LLM
        # For now, just return specific fields
        pass
