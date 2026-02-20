import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import engine, wellstar_engine
from backend.models import Base


def create_wellstar_indexes():
    """Create performance indexes on Wellstar.db (safe to re-run)."""
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_equipment_job_date ON Equipment(Job, ReportDate);",
        "CREATE INDEX IF NOT EXISTS idx_sample_job_date ON Sample(Job, ReportDate);",
        "CREATE INDEX IF NOT EXISTS idx_concentaddloss_job_date ON ConcentAddLoss(Job, ReportDate);",
        "CREATE INDEX IF NOT EXISTS idx_report_job_date ON Report(Job, ReportDate);",
        "CREATE INDEX IF NOT EXISTS idx_circdata_job_date ON CircData(Job, ReportDate);",
        "CREATE INDEX IF NOT EXISTS idx_sample_time ON Sample(Job, ReportDate, SampleTime);",
    ]
    with wellstar_engine.connect() as conn:
        for sql in indexes:
            conn.execute(__import__("sqlalchemy").text(sql))
        conn.commit()
    print("Wellstar.db indexes created.")


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("App database tables created.")

    create_wellstar_indexes()
