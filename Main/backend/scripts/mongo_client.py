import os
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "fin_gpt")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "conversations")
MONGO_VECTOR_COLLECTION = os.getenv("MONGO_VECTOR_COLLECTION", "Vector")

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

def save_vector(conversation_id: str, question_vector: list | None = None, response_vector: list | None = None, metadata: dict | None = None) -> str:
    if question_vector is None and response_vector is None:
        raise ValueError("Provide at least question_vector or response_vector")

    db = _get_db()
    payload = {
        "conversation_id": conversation_id,
        "metadata": metadata or {},
        "created_at": datetime.utcnow().isoformat()
    }
    if question_vector is not None:
        payload["question_vector"] = list(question_vector)
    if response_vector is not None:
        payload["response_vector"] = list(response_vector)

    for k, v in list(payload.items()):
        try:
            json.dumps(v)
        except Exception:
            payload[k] = str(v)

    result = db[MONGO_VECTOR_COLLECTION].insert_one(payload)
    return str(result.inserted_id)

def find_conversation(_id: str):
    db = _get_db()
    return db[MONGO_COLLECTION].find_one({"_id": ObjectId(_id)})