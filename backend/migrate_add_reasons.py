import os
import sys
from sqlalchemy import text
from config.database import engine

def upgrade():
    try:
        with engine.connect() as conn:
            try:
                with conn.begin():
                    conn.execute(text("ALTER TABLE evaluation_results ADD COLUMN reasons JSON;"))
            except Exception as e:
                if "1064" in str(e) or "syntax" in str(e).lower():
                    # Fallback to TEXT for older MySQL/MariaDB versions that don't support JSON
                    with conn.begin():
                        conn.execute(text("ALTER TABLE evaluation_results ADD COLUMN reasons TEXT;"))
                else:
                    raise e
            print("Successfully added 'reasons' column to evaluation_results table.")
    except Exception as e:
        if "Duplicate column name" in str(e) or "already exists" in str(e):
            print("Column 'reasons' already exists.")
        else:
            print(f"Error: {e}")

if __name__ == "__main__":
    upgrade()
