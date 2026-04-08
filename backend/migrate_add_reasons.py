import os
import sys
from sqlalchemy import text
from config.database import engine

def upgrade():
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE evaluation_results ADD COLUMN reasons JSON;"))
            conn.commit()
            print("Successfully added 'reasons' column to evaluation_results table.")
    except Exception as e:
        if "Duplicate column name" in str(e) or "already exists" in str(e):
            print("Column 'reasons' already exists.")
        else:
            print(f"Error: {e}")

if __name__ == "__main__":
    upgrade()
