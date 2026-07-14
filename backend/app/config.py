from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str = "your_groq_api_key_here"
    groq_model: str = "gemma2-9b-it"
    groq_fallback_model: str = "llama-3.3-70b-versatile"
    database_url: str = "sqlite:///./hcp_crm.db"

    class Config:
        env_file = ".env"


settings = Settings()
