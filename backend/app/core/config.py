from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Sentinel"
    API_V1_STR: str = "/v1"
    DATABASE_URL: str = "sqlite+aiosqlite:///./sentinel.db"
    SECRET_KEY: str = "supersecretkey" # In prod, get from env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    
    GEMINI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    
    # Notification Settings
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SLACK_WEBHOOK_URL: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
