import sys
import os
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.abspath("c:/Users/stu/Desktop/Veridian/backend"))

# Load .env from parent directory
env_path = os.path.abspath("c:/Users/stu/Desktop/Veridian/.env")
if os.path.exists(env_path):
    print(f"Loading .env from {env_path}")
    load_dotenv(env_path)
else:
    print(f"Warning: .env not found at {env_path}")

try:
    from app.main import app
    print("Successfully imported app.main")
except Exception as e:
    print(f"Failed to import app.main: {e}")
    import traceback
    with open("import_error.log", "w") as f:
        traceback.print_exc(file=f)
    print("Error logged to import_error.log")
