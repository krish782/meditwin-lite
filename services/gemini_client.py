import os
import google.generativeai as genai  # STAY WITH OLD SDK (it works)


GEMINI_MODEL = "models/gemini-2.5-flash"  # OLDEST + most stable model


def init_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY env var is not set")
    
    genai.configure(api_key=api_key)


def summarize_text(text: str) -> str:
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(f"Summarize this:\n\n{text[:1000]}")
    return response.text
