from sqlalchemy import text
from config.database import engine
from models.database import Base

def migrate():
    print("Starting migration...")
    with engine.connect() as conn:
        # Check columns for documents table
        print("Checking 'documents' table...")
        res = conn.execute(text("SHOW COLUMNS FROM documents"))
        columns = [row[0] for row in res.fetchall()]
        print(f"Existing columns in 'documents': {columns}")
        
        missing_docs = {
            "is_analyzed": "BOOLEAN DEFAULT FALSE",
            "analyzed_at": "DATETIME",
            "doc_metadata_col": "JSON",
            "outline": "JSON",
            "product_entities": "JSON"
        }
        
        for col, col_type in missing_docs.items():
            if col not in columns:
                print(f"Adding column '{col}' to 'documents' table...")
                conn.execute(text(f"ALTER TABLE documents ADD COLUMN {col} {col_type}"))
                print(f"Column '{col}' added.")

        # Check document_chunks table
        print("\nChecking 'document_chunks' table...")
        try:
            res = conn.execute(text("SHOW COLUMNS FROM document_chunks"))
            columns_chunks = [row[0] for row in res.fetchall()]
            print(f"Existing columns in 'document_chunks': {columns_chunks}")
            
            # Column mapping: old_name -> new_name/type
            renames = {
                'start_pos': ('start_char', 'INTEGER'),
                'end_pos': ('end_char', 'INTEGER'),
                'vector': ('dense_vector', 'JSON'),
                'metadata_json': ('chunk_metadata', 'JSON'),
                'metadata': ('chunk_metadata', 'JSON') # handle if it was renamed to metadata before
            }
            
            for old_col, (new_col, col_type) in renames.items():
                if old_col in columns_chunks and new_col not in columns_chunks:
                    print(f"Renaming '{old_col}' to '{new_col}' in 'document_chunks'...")
                    try:
                        conn.execute(text(f"ALTER TABLE document_chunks RENAME COLUMN {old_col} TO {new_col}"))
                    except:
                        conn.execute(text(f"ALTER TABLE document_chunks CHANGE COLUMN {old_col} {new_col} {col_type}"))
                    print(f"Column '{old_col}' renamed to '{new_col}'.")
                elif new_col not in columns_chunks:
                    print(f"Adding column '{new_col}' to 'document_chunks'...")
                    conn.execute(text(f"ALTER TABLE document_chunks ADD COLUMN {new_col} {col_type}"))
                    print(f"Column '{new_col}' added.")

            # Add missing columns for DocumentChunk
            missing_chunks = {
                "overlap_ratio": "JSON",
                "entities": "JSON"
            }
            for col, col_type in missing_chunks.items():
                if col not in columns_chunks:
                    print(f"Adding column '{col}' to 'document_chunks'...")
                    conn.execute(text(f"ALTER TABLE document_chunks ADD COLUMN {col} {col_type}"))
                    print(f"Column '{col}' added.")

        except Exception as e:
            print(f"Error migrating 'document_chunks': {e}")
            print("Running create_all()...")
            Base.metadata.create_all(bind=engine)

        # Update foreign keys to CASCADE
        print("\nUpdating foreign keys to support CASCADE...")
        fk_updates = [
            ("document_chunks", "document_id", "documents", "id"),
            ("testsets", "document_id", "documents", "id"),
            ("testsets", "user_id", "users", "id"),
            ("questions", "testset_id", "testsets", "id"),
            ("evaluations", "user_id", "users", "id"),
            ("evaluation_results", "evaluation_id", "evaluations", "id"),
            ("configurations", "user_id", "users", "id")
        ]
        
        for table, col, ref_table, ref_col in fk_updates:
            try:
                # Find existing constraint name
                fk_query = text(f"""
                    SELECT CONSTRAINT_NAME 
                    FROM information_schema.KEY_COLUMN_USAGE 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = '{table}' 
                    AND COLUMN_NAME = '{col}' 
                    AND REFERENCED_TABLE_NAME IS NOT NULL
                """)
                res = conn.execute(fk_query).fetchone()
                if res:
                    constraint_name = res[0]
                    print(f"Dropping and recreating FK '{constraint_name}' on {table}({col}) with ON DELETE CASCADE...")
                    conn.execute(text(f"ALTER TABLE {table} DROP FOREIGN KEY {constraint_name}"))
                    conn.execute(text(f"""
                        ALTER TABLE {table} 
                        ADD CONSTRAINT {constraint_name} 
                        FOREIGN KEY ({col}) REFERENCES {ref_table}({ref_col}) 
                        ON DELETE CASCADE
                    """))
                    print(f"FK '{constraint_name}' updated.")
            except Exception as e:
                print(f"Warning: Could not update FK for {table}({col}): {e}")

        conn.commit()
    print("\nMigration completed successfully!")

if __name__ == "__main__":
    migrate()
