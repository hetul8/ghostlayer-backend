import os
import uuid
import json
import sqlite3
import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

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

# Database Setup (SQLite)
DB_PATH = os.path.join(os.getcwd(), "secrets.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS secrets (
            id TEXT PRIMARY KEY,
            type TEXT,
            masked_id TEXT,
            original_value TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Initialize DB on startup
init_db()

# Presidio Engines (Memory Optimized)
try:
    # 1. Define the Small Model Config
    configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
    }

    # 2. Initialize the Provider
    provider = NlpEngineProvider(nlp_configuration=configuration)
    nlp_engine = provider.create_engine()

    # 3. Pass the lightweight engine to the Analyzer
    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
    anonymizer = AnonymizerEngine()
except Exception as e:
    print(f"Error loading Presidio models: {e}")
    analyzer = None
    anonymizer = None

class MaskRequest(BaseModel):
    text: str

class UnmaskRequest(BaseModel):
    masked_text: str

@app.post("/mask")
def mask_text(request: MaskRequest, api_key: str = Depends(get_api_key)):
    if not analyzer or not anonymizer:
        raise HTTPException(status_code=500, detail="Presidio analyzer not initialized")
    
    text = request.text
    
    # Analyze
    results = analyzer.analyze(text=text, entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON"], language='en')
    sorted_results = sorted(results, key=lambda x: x.start, reverse=True)
    
    masked_text = text
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        for result in sorted_results:
            original_value = text[result.start:result.end]
            entity_type = result.entity_type
            
            # Generator unique ID
            unique_uuid = str(uuid.uuid4())
            short_id = unique_uuid[:8]
            placeholder = f"[{entity_type}_{short_id}]"
            
            # Store in SQLite
            cursor.execute(
                "INSERT INTO secrets (id, type, masked_id, original_value) VALUES (?, ?, ?, ?)",
                (unique_uuid, entity_type, placeholder, original_value)
            )
            
            # Replace in text
            masked_text = masked_text[:result.start] + placeholder + masked_text[result.end:]
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"DB Error: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        conn.close()
        
    return {"masked_text": masked_text}

@app.post("/unmask")
def unmask_text(request: UnmaskRequest, api_key: str = Depends(get_api_key)):
    masked_text = request.masked_text
    
    import re
    # Matches [TYPE_ID] where ID is 8 chars
    pattern = r"\[([A-Z_]+)_([a-f0-9]+)\]"
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    def replace_match(match):
        full_placeholder = match.group(0)
        # Check if exists in DB
        cursor.execute("SELECT original_value FROM secrets WHERE masked_id = ?", (full_placeholder,))
        row = cursor.fetchone()
        
        if row:
            return row[0]
        else:
            return full_placeholder

    try:
        unmasked_text = re.sub(pattern, replace_match, masked_text)
    finally:
        conn.close()
    
    return {"original_text": unmasked_text}

@app.get("/stats")
def get_stats(api_key: str = Depends(get_api_key)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Counts
        cursor.execute("SELECT COUNT(*) FROM secrets")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM secrets WHERE type = 'EMAIL_ADDRESS'")
        emails = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM secrets WHERE type = 'PHONE_NUMBER'")
        phones = cursor.fetchone()[0]
        
        # Recent Logs (Secure: Now including PII for Admin)
        cursor.execute("SELECT id, type, masked_id, original_value, timestamp FROM secrets ORDER BY timestamp DESC LIMIT 100")
        rows = cursor.fetchall()
        recent_logs = [dict(row) for row in rows]
        
        return {
            "total": total,
            "emails": emails,
            "phones": phones,
            "recent_logs": recent_logs
        }
    finally:
        conn.close()
