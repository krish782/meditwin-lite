import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

# Firebase initialization
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    
    cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase initialized")
except Exception as e:
    print(f"⚠️ Firebase not initialized yet: {e}")
    db = None

# Gemini
try:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    print("✅ Gemini API configured")
except Exception as e:
    print(f"⚠️ Gemini not configured yet: {e}")
