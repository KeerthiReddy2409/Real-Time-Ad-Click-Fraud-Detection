from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "ClickGuard"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    REDIS_URL: str = "redis://localhost:6379"
    DATABASE_URL: str = "postgresql://clickguard:clickguard@localhost:5432/clickguard"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()