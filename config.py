import os
import json
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")
FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS")  # For Railway (JSON string)
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

# Firebase initialization
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    
    # Try to load from environment variable first (Railway/Production)
    if FIREBASE_CREDENTIALS:
        print("🔧 Loading Firebase from environment variable...")
        cred_dict = json.loads(FIREBASE_CREDENTIALS)
        cred = credentials.Certificate(cred_dict)
    # Fall back to file path (Local development)
    elif FIREBASE_CREDENTIALS_PATH:
        print("🔧 Loading Firebase from file path...")
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
    else:
        # Last resort: try default path
        print("🔧 Loading Firebase from default path...")
        cred = credentials.Certificate('firebase-credentials.json')
    
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase initialized successfully")
except json.JSONDecodeError as e:
    print(f"❌ Firebase credentials JSON parse error: {e}")
    db = None
except Exception as e:
    print(f"⚠️ Firebase not initialized yet: {e}")
    db = None

# Gemini
try:
    import google.generativeai as genai
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        print("✅ Gemini API configured")
    else:
        print("⚠️ GEMINI_API_KEY not found in environment")
except Exception as e:
    print(f"⚠️ Gemini not configured yet: {e}")