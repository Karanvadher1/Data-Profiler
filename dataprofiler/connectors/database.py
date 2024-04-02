import mysql.connector

def get_mysql_connection(username, host, password):
    try:
        conn = mysql.connector.connect(user=username, password=password, host=host)
        return conn
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None