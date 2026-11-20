import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv("PIMS_DATABASE_URL")
if not database_url:
    print("DATABASE_URL not found in .env")
    exit(1)

engine = create_engine(database_url)

with engine.connect() as conn:
    result = conn.execute(text("SELECT tablename, indexname, indexdef FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename;"))
    for row in result:
        print(f"Table: {row.tablename}, Index: {row.indexname}")
        print(f"  Def: {row.indexdef}")
