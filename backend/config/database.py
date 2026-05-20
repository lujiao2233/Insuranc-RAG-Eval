from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mysql+pymysql://root:password@localhost:3306/rag_evaluation")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",
    }

settings = Settings()

engine_kwargs = {}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    **engine_kwargs
)

if not settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_timezone(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("SET time_zone = '+08:00'")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
