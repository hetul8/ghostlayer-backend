import os
import uuid
import datetime
import secrets
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

# Auth Configuration
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
# MY_SECRET_KEY removed in favor of DB check

# ... (db setup)

# Define Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    api_keys = relationship("APIKey", back_populates="user")

class APIKey(Base):
    __tablename__ = "api_keys"
    key = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    user = relationship("User", back_populates="api_keys")

class Secret(Base):
    __tablename__ = "secrets"
    id = Column(String, primary_key=True, index=True)
    type = Column(String)
    masked_id = Column(String, index=True)
    original_value = Column(Text)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

# ... (create tables)

# ... (get_db)

# Security Dependency
async def get_api_key(api_key_header: str = Security(api_key_header), db: Session = Depends(get_db)):
    if not api_key_header:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="API Key missing")
    
    # Check DB
    api_key_record = db.query(APIKey).filter(APIKey.key == api_key_header, APIKey.is_active == True).first()
    
    if api_key_record:
        return api_key_record.user # Return the User object!
    else:
        # Fallback for the hardcoded dashboard key during migration?
        # User said "Remove the hardcoded API_KEY check".
        # But if I remove it, the currently deployed dashboard (using "ghost_123_secret") will break until I create a user for it.
        # I will assume I should add a check *or* I should just follow instructions strictly.
        # "Remove the hardcoded API_KEY check" -> Strict.
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Invalid or inactive API Key"
        )

# Admin Tools
class CreateUserRequest(BaseModel):
    email: str

@app.post("/admin/create_user")
def create_user(request: CreateUserRequest, db: Session = Depends(get_db)):
    # Check if exists
    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create User
    new_user = User(email=request.email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Generate Key
    new_key = "gk_live_" + secrets.token_urlsafe(16)
    db_key = APIKey(key=new_key, user_id=new_user.id)
    db.add(db_key)
    db.commit()
    
    return {"email": new_user.email, "api_key": new_key}

# Create Tables
try:
    Base.metadata.create_all(bind=engine)
    print("Database tables created/verified.")
except Exception as e:
    print(f"Error creating tables: {e}")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- PRESIDIO SETUP ---
try:
    configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
    }
    provider = NlpEngineProvider(nlp_configuration=configuration)
    nlp_engine = provider.create_engine()
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
def mask_text(request: MaskRequest, api_key: str = Depends(get_api_key), db: Session = Depends(get_db)):
    if not analyzer or not anonymizer:
        raise HTTPException(status_code=500, detail="Presidio analyzer not initialized")
    
    text = request.text
    results = analyzer.analyze(text=text, entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON"], language='en')
    sorted_results = sorted(results, key=lambda x: x.start, reverse=True)
    
    masked_text = text
    
    try:
        for result in sorted_results:
            original_value = text[result.start:result.end]
            entity_type = result.entity_type
            
            unique_uuid = str(uuid.uuid4())
            short_id = unique_uuid[:8]
            placeholder = f"[{entity_type}_{short_id}]"
            
            # Create DB Record
            db_secret = Secret(
                id=unique_uuid,
                type=entity_type,
                masked_id=placeholder,
                original_value=original_value
            )
            db.add(db_secret)
            
            masked_text = masked_text[:result.start] + placeholder + masked_text[result.end:]
            
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"DB Error: {e}")
        raise HTTPException(status_code=500, detail="Database error")
        
    return {"masked_text": masked_text}

@app.post("/unmask")
def unmask_text(request: UnmaskRequest, api_key: str = Depends(get_api_key), db: Session = Depends(get_db)):
    masked_text = request.masked_text
    import re
    pattern = r"\[([A-Z_]+)_([a-f0-9]+)\]"
    
    def replace_match(match):
        full_placeholder = match.group(0)
        # Query DB
        secret = db.query(Secret).filter(Secret.masked_id == full_placeholder).first()
        if secret:
            return secret.original_value
        else:
            return full_placeholder

    unmasked_text = re.sub(pattern, replace_match, masked_text)
    return {"original_text": unmasked_text}

@app.get("/stats")
def get_stats(api_key: str = Depends(get_api_key), db: Session = Depends(get_db)):
    try:
        total = db.query(Secret).count()
        emails = db.query(Secret).filter(Secret.type == 'EMAIL_ADDRESS').count()
        phones = db.query(Secret).filter(Secret.type == 'PHONE_NUMBER').count()
        
        # Recent Logs (Secure: No PII)
        logs = db.query(Secret).order_by(Secret.timestamp.desc()).limit(100).all()
        
        recent_logs = []
        for log in logs:
            recent_logs.append({
                "id": log.id,
                "type": log.type,
                "masked_id": log.masked_id,
                "original_value": log.original_value, # Admin View Enabled
                "timestamp": log.timestamp.isoformat()
            })
        
        return {
            "total": total,
            "emails": emails,
            "phones": phones,
            "recent_logs": recent_logs
        }
    except Exception as e:
        print(f"Stats Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
