from fastapi import Request, HTTPException
from collections import defaultdict
import time

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.limit = 100 # requests
        self.window = 60 # seconds

    async def check(self, key: str):
        now = time.time()
        reqs = self.requests[key]
        
        # Clean old requests
        self.requests[key] = [t for t in reqs if t > now - self.window]
        
        if len(self.requests[key]) >= self.limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        self.requests[key].append(now)

rate_limiter = RateLimiter()
