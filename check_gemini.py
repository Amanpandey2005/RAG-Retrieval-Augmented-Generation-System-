import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("backend/.env")

api_key = os.getenv("GEMINI_API_KEY")
print(f"Key found: {bool(api_key)}")
if api_key:
    genai.configure(api_key=api_key)
    
    print("\n--- Listing Models ---")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
    except Exception as e:
        print(f"List models failed: {e}")

    print("\n--- Testing Embedding ---")
    try:
        emb = genai.embed_content(
            model="models/text-embedding-004",
            content="Hello world",
            task_type="retrieval_query"
        )
        print("Embedding success")
    except Exception as e:
        print(f"Embedding failed: {e}")

    print("\n--- Testing Generation ---")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        res = model.generate_content("Hello")
        print(f"Generation success: {res.text}")
    except Exception as e:
        print(f"Generation failed: {e}")
