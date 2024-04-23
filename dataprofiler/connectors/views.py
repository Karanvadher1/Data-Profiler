from datetime import datetime
import os
import subprocess
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from matplotlib import pyplot as plt
import pandas as pd
from account.models import User
from dataprofiler import settings
from .database import get_mysql_connection, get_postgresql_connection
from .models import Data_Warehouse, Ingestion,Mysql_connector
from django.contrib.auth.decorators import login_required
from airflow.models import DagRun


connection = None
database =None
user_warehouse = None


@login_required(login_url='login')
def check_connector(request):
  try:
    connector = Mysql_connector.objects.filter(user_id=request.user.id)
    connector_details = []
    if connector:
      for conn in connector:
        id = conn.id
        service = conn.service_name    
        connector_details.append({'id':id,'service':service})
    return render(request,'connections/my_connector.html',{'connector_details':connector_details})
  except:
    messages.warning(request,"You have not made any connector yet!")
    return redirect('db_warehouse')  
  
  
@login_required(login_url='login')
def select_connector(request):
  global connection,user_warehouse
  if request.method == 'POST':
    connector_id = request.POST.get('connector_id')
    if connector_id != None:
      connector = get_object_or_404(Mysql_connector, id=connector_id)
      if connector.service_name.lower() == 'mysql':
        user_warehouse = 'mysql'
        connection = get_mysql_connection(connector.username,connector.host,connector.password,connector.database)
        if connection != None:
          messages.success(request, f'Connected to MySQL Database : {connector.database} successfully')
          return redirect('table_list')   
        else:
          messages.error(request, 'Failed to connect to MySQL database')
      if connector.service_name.lower() == 'postgres':
        user_warehouse = 'postgres'
        connection = get_postgresql_connection(connector.username,connector.host,connector.password,connector.database)
        if connection != None:
          messages.success(request, f'Connected to PostgreSQL Database : {connector.database} successfully')
          return redirect('table_list')   
        else:
          messages.error(request, 'Failed to connect to MySQL database')
    return render(request, 'account/dashboard.html')


@login_required(login_url='login')
def db_warehouse(request):
  data_warehouse = Data_Warehouse.objects.all()
  warehouses_info = []  
  for warehouse in data_warehouse:
    # Access attributes of each warehouse object
    warehouse_name = warehouse.warehouse_name
    image_filename = warehouse.warehouse_image.name
    image_path = os.path.join('images', 'icons', image_filename)
    warehouses_info.append({'name': warehouse_name, 'image_path': image_path})
  context = {
    'warehouses_info':warehouses_info,
  }
  return render(request, 'connections/list_connector.html', context)


@login_required(login_url='login')
def select_warehouse(request):
  global user_warehouse
  if request.method == "POST":
    user_warehouse = request.POST.get('warehouse')
    if user_warehouse.lower() == 'mysql':
      return redirect('Mysql_connection')
    if user_warehouse.lower() == 'postgresql':
      return redirect('PostgreSQL_connection')  
  else:
    return HttpResponse("Invalid credentials or no active connection")

      
@login_required(login_url='login')
def Mysql_connection(request):
  global connection,database
  if request.method == 'POST':
    username = request.POST.get('username')
    host = request.POST.get('host')
    database = request.POST.get('database')
    password = request.POST.get('password')
    confirm_password = request.POST.get('confirm_password')
    if password != confirm_password:
      messages.warning(request, 'Confirm password did not match')
    else:
      connection = get_mysql_connection(username, host, password,database)
      if connection and connection != None:  
        Mysql_connector.objects.update_or_create(
          user=request.user,  
          username= username,
          password= password,
          host = host,
          database = database
        )
        messages.success(request, 'Connected to MySQL database successfully')
        return redirect('table_list')
      else:
        messages.error(request, 'Failed to connect to MySQL database')
  return render(request, 'connections/mysql_connector.html')


@login_required(login_url='login')
def PostgreSQL_connection(request):
  global connection,database
  if request.method == 'POST':
    username = request.POST.get('username')
    host = request.POST.get('host')
    database = request.POST.get('database')
    password = request.POST.get('password')
    confirm_password = request.POST.get('confirm_password')
    if password != confirm_password:
      messages.warning(request, 'Confirm password did not match')
    else:
      connection = get_postgresql_connection(username, host, password,database)
      if connection and connection != None:  
        Mysql_connector.objects.update_or_create(
          service_name = 'postgresql',
          user=request.user,  
          username= username,
          password= password,
          host = host,
          database = database
        )
        messages.success(request, 'Connected to PostgreSQL database successfully')
        return redirect('table_list')
      else:
        messages.error(request, 'Failed to connect to MySQL database')
  return render(request, 'connections/postgresql_connector.html')

   
def table_list(request):
  global connection, database, user_warehouse
  print(user_warehouse)
  try:  
    if connection != None:
      if user_warehouse.lower() == 'mysql':
        all_tables = connection.execute('show tables').fetchall()
        tables = [table[0] for table in all_tables]
        return render(request, 'connections/tables.html', {'tables': tables})   
        
      if user_warehouse.lower() == 'postgresql':
        all_tables = connection.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'").fetchall()
        tables = [table[0] for table in all_tables]
        return render(request, 'connections/tables.html', {'tables': tables})   
      else:
          return HttpResponse("Invalid warehouse type")
    else:
        return HttpResponse("Invalid credentials or no active connection")
  except Exception as e:
      print(f"Error fetching tables: {e}")
      return HttpResponse("Error fetching tables")


def select_table(request):
  if request.method == 'POST':
    selected_table = request.POST.getlist('selected_table')      
    selected_tables_str = ','.join(selected_table)
    return redirect('selected_table', selected_table=selected_tables_str)
  else:
    return HttpResponse("Invalid request method")
      

def selected_table(request, selected_table):
  global connection,user_warehouse
  if connection != None:
    try:
      print(request.user.id)
      print(user_warehouse)
      connector = Mysql_connector.objects.get(user=request.user.id,service_name = user_warehouse.lower())
      print(connector)
      user_instance = User.objects.get(id=request.user.id)
      # Triggering airflow DAGs
      dag_id = 'etl_pipeline'
      try:
        selected_tables_list = selected_table.split(',')
        for table in selected_tables_list:
          data = {
            'conf': f'{{"selected_table":"{table}","connector":"{connector.id}","user":"{connector.user_id}","db":"{connector.database} ","username":"{connector.username}", "host":"{connector.host}","password":"{connector.password}"}}',
            'dag_id': dag_id,
            'dag_run_id': f'manual__{datetime.utcnow().isoformat()}',
            'end_date': None,
            'external_trigger': True,
            'last_scheduling_decision': None,
            'run_type': 'manual',
            'start_date': None,
            'state': 'queued',
            'user': user_instance
          }
          ingestion_instance = Ingestion.create_ingestion(**data)
          # Fetch data from the database
          result = connection.execute(f'SELECT * FROM {table}').fetchall()
          # Convert SQLAlchemy object into dict
          serialized_data = [dict(row) for row in result]
          df = pd.DataFrame(serialized_data)
          # Calculate box plot data
          numeric_columns = df.select_dtypes(include=['int', 'float'])
          numeric_columns = numeric_columns.dropna()
          box_plot_data = numeric_columns.to_dict()
          
          # Save box plot data to ingestion instance
          ingestion_instance.box_plot_data = box_plot_data
          ingestion_instance.save()
          
          subprocess.run(['airflow', 'dags', 'trigger',dag_id, '-c', f'{{"selected_table":"{table}","connector":"{connector.id}","ingestion_id":"{ingestion_instance.id}","user":"{connector.user_id}","db":"{connector.database} ","username":"{connector.username}", "host":"{connector.host}","password":"{connector.password}"}}'], check=True)
          message = f"DAG {dag_id} triggered successfully"     
          dag_runs = DagRun.find(dag_id=dag_id)
          if dag_runs:
            #check status of dag
            for dag_run in dag_runs:
              current_state = dag_run.get_state()
              print(f"DAG run is currently in state: {current_state}")
              ingestion_instance.state = current_state
              ingestion_instance.save()
              #check status of tasks
              break 
          
        return redirect('dashboard')
      except subprocess.CalledProcessError as e:
          message = f"Error triggering DAG {dag_id}: {e}"
    except Mysql_connector.DoesNotExist:
      return HttpResponse("User credentials not found")
    return HttpResponse(message)
  else:
      return HttpResponse("Connection is not established.")