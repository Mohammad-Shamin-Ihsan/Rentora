from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_host:        str = "localhost"
    db_port:        int = 5432
    db_name:        str = "rentora_db"
    db_user:        str = "postgres"
    db_password:    str
    frontend_url:   str = "http://localhost:4200"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    class Config:
        env_file = ".env"

settings = Settings()