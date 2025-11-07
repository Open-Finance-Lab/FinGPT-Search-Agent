import os
from datetime import datetime
from urllib.parse import quote_plus

try:
    from pymongo import MongoClient
except Exception as e:
    print("pymongo not installed:", e)
    raise

def load_env_file(path):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k not in os.environ:
                os.environ[k] = v

# try to load backend/.env if variables missing
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
env_path = os.path.join(BASE_DIR, ".env")
load_env_file(env_path)

MONGO_URI = os.getenv("MONGO_URI")
DB = os.getenv("MONGO_DB", "FinGPT_Search_Agent")
COL = os.getenv("MONGO_COLLECTION", "Messages")

# if no full URI, build one from parts
if not MONGO_URI:
    user = os.getenv("MONGO_USER")
    pwd = os.getenv("MONGO_PASS")
    host = os.getenv("MONGO_HOST")
    if not (user and pwd and host):
        raise SystemExit("Set MONGO_URI or MONGO_USER/MONGO_PASS/MONGO_HOST in env or backend/.env")
    MONGO_URI = f"mongodb+srv://{quote_plus(user)}:{quote_plus(pwd)}@{host}/{DB}?retryWrites=true&w=majority"

# if URI missing DB path, pymongo will still work using db param below
print("Connecting (credentials masked)...")
try:
    client = MongoClient(MONGO_URI)
    db = client[DB]
    col = db[COL]
    doc = {
        "created_at": datetime.utcnow().isoformat(),
        "session_id": "demo_test_session",
        "messages": [
            {"role": "user", "text": "Hello from demo", "timestamp": datetime.utcnow().isoformat()},
            {"role": "assistant", "text": "Demo reply", "timestamp": datetime.utcnow().isoformat()}
        ],
        "notes": "simple demo insert"
    }
    res = col.insert_one(doc)
    print("Inserted document id:", res.inserted_id)
except Exception as e:
    print("Insert failed:", e)
finally:
    try:
        client.close()
    except Exception:
        pass