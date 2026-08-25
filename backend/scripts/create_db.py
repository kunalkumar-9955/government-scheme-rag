"""
scripts/create_db.py
--------------------
Run this script to create the govscheme_db database and govscheme_user.
It connects as 'postgres' superuser — you'll be prompted for the password.

Usage:
    python scripts/create_db.py

    Or with password:
    python scripts/create_db.py --password YOUR_POSTGRES_PASSWORD
"""

import sys
import getpass

try:
    import psycopg
except ImportError:
    print("ERROR: psycopg not installed. Run: python -m pip install psycopg>=3.1.0")
    sys.exit(1)

DB_NAME = "govscheme_db"
DB_USER = "govscheme_user"
DB_PASS = "govscheme_pass"

def main():
    # Get postgres password
    if "--password" in sys.argv:
        idx = sys.argv.index("--password")
        pg_password = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
    else:
        pg_password = getpass.getpass("Enter postgres superuser password: ")

    print(f"\n🔧 Connecting to PostgreSQL as postgres...")

    try:
        # Connect to default 'postgres' database as superuser
        conn = psycopg.connect(
            dbname="postgres",
            user="postgres",
            password=pg_password,
            host="localhost",
            port=5432,
            autocommit=True,
        )
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nMake sure PostgreSQL is running and try again.")
        print("Or use pgAdmin to manually create the user and database.")
        sys.exit(1)

    with conn.cursor() as cur:
        # Create user
        try:
            cur.execute(
                f"CREATE USER {DB_USER} WITH PASSWORD %s;",
                (DB_PASS,)
            )
            print(f"✅ Created user: {DB_USER}")
        except psycopg.errors.DuplicateObject:
            print(f"ℹ️  User '{DB_USER}' already exists — updating password.")
            cur.execute(f"ALTER USER {DB_USER} WITH PASSWORD %s;", (DB_PASS,))

        # Create database
        try:
            cur.execute(f"CREATE DATABASE {DB_NAME} OWNER {DB_USER};")
            print(f"✅ Created database: {DB_NAME}")
        except psycopg.errors.DuplicateDatabase:
            print(f"ℹ️  Database '{DB_NAME}' already exists.")

        # Grant privileges
        cur.execute(f"GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER};")
        print(f"✅ Granted privileges on {DB_NAME} to {DB_USER}")

    conn.close()

    # Connect to new DB and set schema privileges
    try:
        conn2 = psycopg.connect(
            dbname=DB_NAME,
            user="postgres",
            password=pg_password,
            host="localhost",
            port=5432,
            autocommit=True,
        )
        with conn2.cursor() as cur:
            cur.execute(f"GRANT ALL ON SCHEMA public TO {DB_USER};")
            cur.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {DB_USER};")
            cur.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {DB_USER};")
        conn2.close()
        print(f"✅ Schema privileges configured.")
    except Exception as e:
        print(f"⚠️  Could not set schema privileges: {e} (may be OK if DB is fresh)")

    print(f"\n✅ Database setup complete!")
    print(f"   Database: {DB_NAME}")
    print(f"   User:     {DB_USER}")
    print(f"   Password: {DB_PASS}")
    print(f"\nNext step: python manage.py migrate --settings=config.settings.phase1")


if __name__ == "__main__":
    main()
