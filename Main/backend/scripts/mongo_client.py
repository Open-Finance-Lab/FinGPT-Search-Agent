import os
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "fin_gpt")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "conversations")

_client = None
_db = None

def _get_db():
    global _client, _db
    if _client is None:
        if not MONGO_URI:
            raise RuntimeError("MONGO_URI not set")
        _client = MongoClient(MONGO_URI)
        _db = _client[MONGO_DB]
    return _db

def save_conversation(doc: dict) -> str:
    db = _get_db()
    doc_copy = dict(doc)
    result = db[MONGO_COLLECTION].insert_one(doc_copy)
    return str(result.inserted_id)

def find_conversation(_id: str):
    db = _get_db()
    return db[MONGO_COLLECTION].find_one({"_id": ObjectId(_id)})