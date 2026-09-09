import os
from pathlib import Path

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import create_app
from app.config import Config
from app.seed import seed_database

app = create_app(os.getenv("FLASK_ENV", "development"))

if __name__ == "__main__":
    # Ensure database exists and is seeded if first run
    db_file = Path(Config.DATABASE_PATH)
    if not db_file.exists():
        print(f"[*] Database file '{Config.DATABASE_PATH}' not found. Auto-seeding initial database...")
        seed_database(Config.DATABASE_PATH)

    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "127.0.0.1")
    debug = os.getenv("FLASK_DEBUG", "1") == "1"

    print(f"\n=======================================================")
    print(f"  Coders Era Event Platform running at:")
    print(f"  http://{host}:{port}")
    print(f"=======================================================\n")
    
    app.run(host=host, port=port, debug=debug)
