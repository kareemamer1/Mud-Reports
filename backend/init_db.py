import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import engine
from backend.models import Base

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Database tables created.")
