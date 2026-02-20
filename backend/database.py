from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import Base

# ── App database (read-write) ────────────────────────────────────────
engine = create_engine(
    "sqlite:///./app.db",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Wellstar database (read-only) ────────────────────────────────────
WELLSTAR_DB_PATH = Path(__file__).parent / "db" / "Wellstar.db"

wellstar_engine = create_engine(
    f"sqlite:///{WELLSTAR_DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=False,
)

WellstarSession = sessionmaker(
    autocommit=False, autoflush=False, bind=wellstar_engine
)


def get_wellstar_db():
    db = WellstarSession()
    try:
        yield db
    finally:
        db.close()
