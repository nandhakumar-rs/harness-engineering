"""Postgres connection for the durable event log."""

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set — add it to backend/.env")


async def connect() -> psycopg.AsyncConnection:
    return await psycopg.AsyncConnection.connect(DATABASE_URL)


SCHEMA = Path(__file__).with_name("schema.sql").read_text()


async def init_db() -> None:
    """Create the event_log table if it doesn't exist. Safe to run on every startup."""
    async with await connect() as conn:
        await conn.execute(SCHEMA)
