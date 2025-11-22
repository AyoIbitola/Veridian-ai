import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from app.api import metrics
    print("Import app.api.metrics successful")
    
    # Try to instantiate the router or call a function if possible (mocking dependencies is hard)
    print("Metrics router:", metrics.router)
    
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
