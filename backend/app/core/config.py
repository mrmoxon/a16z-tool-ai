from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    BRAVE_API: str
    MISTRAL_API_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()
