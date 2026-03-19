from dotenv import load_dotenv
from neo4j import GraphDatabase
import os

load_dotenv("config.env") # Load environment variables

URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER")
PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def get_session():
    return driver.session(database="learning")

def test_connection():
    with get_session() as session:
        result = session.run("RETURN 'Connection successful' AS message")
        print(result.single()["message"])

if __name__ == "__main__":
    test_connection()