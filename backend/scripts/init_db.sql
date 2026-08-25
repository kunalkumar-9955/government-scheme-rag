-- PostgreSQL initialization script for Government Scheme AI Assistant
-- Runs once when PostgreSQL container is first created

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable full-text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable unaccent for better text search
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Set timezone
SET timezone = 'Asia/Kolkata';

\echo 'Database extensions initialized successfully'
