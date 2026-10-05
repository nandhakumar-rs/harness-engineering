"""Postgres connection for the durable event log."""

import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set — add it to backend/.env")


async def connect() -> psycopg.AsyncConnection:
    return await psycopg.AsyncConnection.connect(DATABASE_URL)
