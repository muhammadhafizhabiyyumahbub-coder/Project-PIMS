from app.core.db import get_session_factory
from app.data.storage.universe import ensure_universe

def startup():
    session_factory = get_session_factory()
    db = session_factory()
    try:
        print("Ensuring universe...")
        univ = ensure_universe(db)
        print(f"Universe ensured. Assets: {len(univ.get('assets', []))}")
    finally:
        db.close()

if __name__ == "__main__":
    startup()
