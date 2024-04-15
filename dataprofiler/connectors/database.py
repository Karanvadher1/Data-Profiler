import mysql.connector
from sqlalchemy import create_engine

def get_mysql_connection(username, host, password,database):
    try:
        mysql_conn_str = f"mysql+mysqlconnector://{username}:{password}@{host}:3306/{database}"
        source_engine = create_engine(mysql_conn_str)
        conn = source_engine.connect()
        return conn
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None