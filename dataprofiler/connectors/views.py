from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from .database import get_mysql_connection
from .models import Mysql_connector
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required

connection = None
database = None

@login_required(login_url='login')
def check_connector(request):
  connector = Mysql_connector.objects.get(user=request.user.id)
  if connector:
    # connection = get_mysql_connection(connector.username,connector.host,connector.password)
    id = connector.id
    service = connector.service_name
    return render(request,'connections/my_connector.html',{'service':service,'connector_id':id})
  return redirect('db_connection')

@login_required(login_url='login')
def select_connector(request, connector_id):
  global connection
  connector = get_object_or_404(Mysql_connector, id=connector_id)
  if connector:
    connection = get_mysql_connection(connector.username,connector.host,connector.password)
    if connection.is_connected:
      messages.success(request, 'Connected to MySQL database successfully')
      return redirect('db_list')        
    else:
      messages.error(request, 'Failed to connect to MySQL database')
  return render(request, 'account/dashboard.html')
      
      
@login_required(login_url='login')  
def db_connection(request):
    global connection
    if request.method == 'POST':
        username = request.POST.get('username')
        host = request.POST.get('host')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        if password != confirm_password:
          messages.warning(request, 'Confirm password did not match')
        else:
          connection = get_mysql_connection(username, host, password)
          if connection and connection.is_connected():
            
            Mysql_connector.objects.update_or_create(
                    user=request.user,  # Assuming user is logged in
                    defaults={
                      'username': username,
                      'password': password,
                      'host': host
                    }
                )
            messages.success(request, 'Connected to MySQL database successfully')
            return redirect('db_list')
          else:
            messages.error(request, 'Failed to connect to MySQL database')
    return render(request, 'connections/create_connector.html')


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
    return redirect('table_list')
  else:
    return HttpResponse("Invalid request method")

   
def table_list(request):
    global connection,database
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
    return render(request, 'connections/selected_table.html', {'table_data': table_data, 'columns': columns,'selected_table':selected_table})

