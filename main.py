import os
import uuid
import json
import redis
from typing import Optional
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth Configuration
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
MY_SECRET_KEY = os.getenv("MY_SECRET_KEY", "dev-secret-key") # Default for dev comfort, change in prod!

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == MY_SECRET_KEY:
        return api_key_header
    else:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials"
        )

# redis_client = redis.Redis(host='localhost', port=6379, db=0)
# Use environment variable or default
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

# Presidio Engines
# Optimization: Load NLP engine once
try:
    analyzer = AnalyzerEngine()
    anonymizer = AnonymizerEngine()
except Exception as e:
    print(f"Error loading Presidio models: {e}")
    # We allow app to start but endpoints might fail if not handled
    analyzer = None
    anonymizer = None

# Redis Connection with Fallback
try:
    # Try connecting to real Redis
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, socket_connect_timeout=1)
    redis_client.ping()
    print(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
    print("WARNING: Could not connect to real Redis. Using FakeRedis for demonstration.")
    import fakeredis
    redis_client = fakeredis.FakeRedis()

class MaskRequest(BaseModel):
    text: str

class UnmaskRequest(BaseModel):
    masked_text: str

@app.post("/mask")
def mask_text(request: MaskRequest, api_key: str = Depends(get_api_key)):
    if not analyzer or not anonymizer:
        raise HTTPException(status_code=500, detail="Presidio analyzer not initialized")
    
    text = request.text
    
    # 1. Analyze
    results = analyzer.analyze(text=text, entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON"], language='en')
    
    # 2. Anonymize with custom logic to store in Redis
    sorted_results = sorted(results, key=lambda x: x.start, reverse=True)
    
    masked_text = text
    
    for result in sorted_results:
        original_value = text[result.start:result.end]
        entity_type = result.entity_type
        
        # Generator unique ID
        unique_id = str(uuid.uuid4())[:8] # Short UUID for readability/compactness
        placeholder = f"[{entity_type}_{unique_id}]"
        
        # Store in Redis: placeholder -> original_value
        # TTL: 10 minutes (600 seconds)
        redis_client.setex(placeholder, 600, original_value)
        
        # Replace in text
        masked_text = masked_text[:result.start] + placeholder + masked_text[result.end:]
        
    return {"masked_text": masked_text}

@app.post("/unmask")
def unmask_text(request: UnmaskRequest, api_key: str = Depends(get_api_key)):
    masked_text = request.masked_text

    
    # We need to find all placeholders like [ENTITY_ID]
    # Simple regex approach: \[([A-Z_]+)_([a-f0-9-]+)\]
    # Or just iterate through the string?
    # Actually, we can just search for the patterns we generated.
    # But since we need to do replacements, let's use a regex to find candidates.
    
    import re
    # Matches [TYPE_ID] where TYPE is uppercase letters/underscores, ID is alphanumeric/dashes
    # Example: [PERSON_a1b2c3d4]
    pattern = r"\[([A-Z_]+)_([a-f0-9]+)\]"
    
    def replace_match(match):
        full_placeholder = match.group(0)
        # Check if exists in Redis
        original_value = redis_client.get(full_placeholder)
        if original_value:
            return original_value.decode('utf-8')
        else:
            # If expired or not found, keep placeholder? Or return generic?
            # Requirement says "Swap them back". If missing, maybe keep it?
            return full_placeholder

    unmasked_text = re.sub(pattern, replace_match, masked_text)
    
    return {"original_text": unmasked_text}

@app.get("/debug/keys")
def get_debug_keys():
    # Helper to decode bytes to string
    keys = redis_client.keys("*")
    data = {}
    for key in keys:
        val = redis_client.get(key)
        key_str = key.decode("utf-8") if isinstance(key, bytes) else str(key)
        val_str = val.decode("utf-8") if isinstance(val, bytes) else str(val)
        data[key_str] = val_str
    return data
