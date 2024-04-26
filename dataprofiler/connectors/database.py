import mysql.connector
from sqlalchemy import create_engine

def get_mysql_connection(username, host, password):
    try:
        mysql_conn_str = f"mysql+mysqlconnector://{username}:{password}@{host}:3306/"
        source_engine = create_engine(mysql_conn_str)
        conn = source_engine.connect()
        return conn
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None
    
def get_postgresql_connection(username, host, password):
    try:        
        postgres_conn_str = f"postgresql://{username}:{password}@{host}:5432/"
        engine = create_engine(postgres_conn_str)
        conn = engine.connect()
        return conn
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return None