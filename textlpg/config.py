"""
TextLPG — Database Configuration

This module handles the connection to Neo4j.
Think of it like your MySQL connection setup:

    MySQL:  connection = mysql.connector.connect(host='localhost', user='root', password='...', database='mydb')
    Neo4j:  driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

The "driver" is the connection pool — it manages connections for us.
The "session" is one active connection — like cursor in MySQL.

Usage in other files:
    from textlpg.config import get_session
    with get_session() as session:
        result = session.run("MATCH (b:Book) RETURN b.code")
        for record in result:
            print(record["b.code"])

The "with" statement auto-closes the session when done — like:
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM books")
    cursor.close()  # <-- "with" does this automatically
"""

from dotenv import load_dotenv
from neo4j import GraphDatabase
import os

# Load environment variables from config.env file
# This keeps secrets (passwords) out of the code
# Same idea as .env files in Django projects
# Use absolute path so it works from any working directory (e.g., Streamlit)
_project_root = os.path.join(os.path.dirname(__file__), "..")
load_dotenv(os.path.join(_project_root, "config.env"))

URI = os.getenv("NEO4J_URI")        # neo4j://127.0.0.1:7687 (bolt protocol, port 7687)
USER = os.getenv("NEO4J_USER")      # default: neo4j
PASSWORD = os.getenv("NEO4J_PASSWORD")

# Create the driver (connection pool) — this is created ONCE and reused
# MySQL equivalent: connection = mysql.connector.connect(...)
driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))


def get_session():
    """
    Get a database session (= one active connection).

    database="textlpg" specifies which database to use.
    Neo4j can have multiple databases (like MySQL: USE textlpg;)

    Returns a session that should be used with 'with':
        with get_session() as session:
            session.run("MATCH ...")
    """
    return driver.session(database="textlpg")


def test_connection():
    """Quick test to verify the database is reachable."""
    with get_session() as session:
        result = session.run("RETURN 'Connection successful' AS message")
        print(result.single()["message"])


if __name__ == "__main__":
    test_connection()
