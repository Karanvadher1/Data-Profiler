from django.http import HttpResponse
import  mysql.connector
from django.shortcuts import render, redirect
from django.contrib import messages
from .database import get_mysql_connection


connection = None
username = None
password = None
database = None


def db_connection(request):
    global connection, username, password
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        if password != confirm_password:
            messages.warning(request, 'Confirm password did not match')
        else:
            connection = get_mysql_connection(username, password)
            if connection and connection.is_connected():
                messages.success(request, 'Connected to MySQL database successfully')
                return redirect('db_list')
            else:
                messages.error(request, 'Failed to connect to MySQL database')
    
    return render(request, 'connections/connection.html')


def db_list(request):
  global connection
  if connection.is_connected():
      cursor = connection.cursor()
      query = 'show databases'
      cursor.execute(query)
      all_db = cursor.fetchall()
      db = [db[0] for db in all_db]
      return render(request,'connections/database.html',{'db':db})
  else:
      return HttpResponse("invalid credentials")


def select_database(request):
  global database
  if request.method == 'POST':
    selected_database = request.POST.get('selected_database')
    database = selected_database
    return redirect('table_list', database=database)
  else:
    return HttpResponse("Invalid request method")

   
def table_list(request, database):
    global connection
    if connection.is_connected():
        cursor = connection.cursor()
        cursor.execute(f'USE {database}')  # Set the selected database
        cursor.execute('SHOW TABLES')
        all_tables = cursor.fetchall()
        table = [table[0] for table in all_tables]
        return render(request, 'connections/tables.html', {'table': table})   
    else:
        return HttpResponse("Invalid credentials or no active connection")

def select_table(request):
  if request.method == 'POST':
    selected_table = request.POST.get('selected_table')
    return redirect('selected_table', selected_table=selected_table)
  else:
    return HttpResponse("Invalid request method")
      

def selected_table(request, selected_table):
  global connection,database
  if connection.is_connected():
    cursor = connection.cursor()
    cursor.execute(f'USE {database}')
    cursor.execute(f'SELECT * FROM {selected_table}')
    table_data = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    
    return render(request, 'connections/selected_table.html', {'table_data': table_data, 'columns': columns})

