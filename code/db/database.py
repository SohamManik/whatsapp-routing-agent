import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

# Use SQLite for local development, allow Postgres via ENV
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./whatsapp_agent.db")

# For SQLite, we need to disable same_thread check and increase timeout for concurrency
connect_args = {"check_same_thread": False, "timeout": 15} if "sqlite" in DATABASE_URL else {}

engine = create_engine(
    DATABASE_URL, connect_args=connect_args
)

if "sqlite" in DATABASE_URL:
    with engine.connect() as con:
        con.execute(text('PRAGMA journal_mode=WAL'))

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from .models import *
Base.metadata.create_all(bind=engine)
