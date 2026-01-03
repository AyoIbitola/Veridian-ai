import sys
import os
from app.core.config import settings

print(f"Current Working Directory: {os.getcwd()}")
print(f"Env File Expected: .env")
print(f"Env File Exists: {os.path.exists('.env')}")

key = settings.GEMINI_API_KEY
if key:
    print(f"GEMINI_API_KEY: Found (Length: {len(key)})")
    print(f"Key preview: {key[:4]}...{key[-4:]}")
else:
    print("GEMINI_API_KEY: Not Found (None or Empty)")

print(f"Project Name: {settings.PROJECT_NAME}")
