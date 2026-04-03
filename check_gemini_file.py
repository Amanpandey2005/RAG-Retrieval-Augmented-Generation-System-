import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv("backend/.env")

api_key = os.getenv("GEMINI_API_KEY")
with open("gemini_models.txt", "w") as f:
    f.write(f"Key found: {bool(api_key)}\n")
    if api_key:
        genai.configure(api_key=api_key)
        
        f.write("\n--- Listing Models ---\n")
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    f.write(f"{m.name}\n")
        except Exception as e:
            f.write(f"List models failed: {e}\n")

        f.write("\n--- Testing Embedding ---\n")
        try:
            emb = genai.embed_content(
                model="models/text-embedding-004",
                content="Hello world",
                task_type="retrieval_query"
            )
            f.write("Embedding success\n")
        except Exception as e:
            f.write(f"Embedding failed: {e}\n")

        f.write("\n--- Testing Generation ---\n")
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            res = model.generate_content("Hello")
            f.write(f"Generation success: {res.text}\n")
        except Exception as e:
            f.write(f"Generation failed: {e}\n")
