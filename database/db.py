import mysql.connector
import os
from dotenv import load_dotenv

# .env file load kora
load_dotenv()

def get_db_connection():
    """
    Database connection create kore ebong connection object return kore.
    """
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            port=int(os.getenv("DB_PORT", 3306)),
            charset=os.getenv("DB_DEFAULT_CHARSET", "utf8mb4")
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None