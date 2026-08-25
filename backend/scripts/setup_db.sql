-- setup_db.sql — Run once to create the govscheme database and user
-- Usage: psql -U postgres -f setup_db.sql

-- Create user (skip if exists)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'govscheme_user') THEN
        CREATE USER govscheme_user WITH PASSWORD 'govscheme_pass';
    ELSE
        ALTER USER govscheme_user WITH PASSWORD 'govscheme_pass';
    END IF;
END
$$;

-- Create database (skip if exists)
SELECT 'CREATE DATABASE govscheme_db OWNER govscheme_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'govscheme_db')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE govscheme_db TO govscheme_user;

-- Connect to govscheme_db and set schema privileges
\c govscheme_db
GRANT ALL ON SCHEMA public TO govscheme_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO govscheme_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO govscheme_user;
