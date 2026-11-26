"""Create an administrator account: python -m app.create_admin"""
from getpass import getpass
from pathlib import Path
import sys

# When this file is run as ``python app/create_admin.py``, Python puts the
# ``app`` directory (rather than the project root) on sys.path. Add the root
# so the package imports below work in both direct-script and module modes.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.core.database import SessionLocal, initialize_database
from app.models.models import User
from app.security import hash_password


def main() -> None:
    initialize_database()

    username = input("Admin username: ").strip()
    password = getpass("Admin password (minimum 8 characters): ")
    confirm = getpass("Confirm password: ")

    if password != confirm:
        raise SystemExit("Passwords do not match.")

    if len(username) < 3 or len(password) < 8:
        raise SystemExit("Username must be at least 3 characters and password at least 8.")
    
    if len(username) > 80 or len(password) > 128:
        raise SystemExit("Username must be at most 80 characters and password at most 128.")
    
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.username == username)):
            raise SystemExit("That username already exists.")
        
        db.add(User(username=username, password_hash=hash_password(password), role="admin"))
        db.commit()

    print(f"Admin account '{username}' created.")


if __name__ == "__main__":
    main()
