import asyncio
import os
import sys

from sqlalchemy import create_engine, text

def main():
    db_url = "postgresql://postgres:Password12@!@127.0.0.1:5432/CareerShift"
    engine = create_engine(db_url)
    with engine.connect() as conn:
        res = conn.execute(text("SELECT id, task_analysis_input_hash FROM assessments ORDER BY created_at DESC LIMIT 1")).fetchone()
        if res:
            print("Assessment ID:", res[0])
        else:
            print("No assessments found")

if __name__ == "__main__":
    main()
