import mysql.connector

def get_mysql_connection(username, password):
    try:
        conn = mysql.connector.connect(user=username, password=password, host='0.0.0.0')
        return conn
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None