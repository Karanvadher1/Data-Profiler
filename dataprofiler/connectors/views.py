import base64
from datetime import datetime,timedelta
from io import BytesIO
import os
import subprocess
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.urls import reverse
from matplotlib import pyplot as plt
import pandas as pd

from account.models import User
from .database import get_mysql_connection
from .models import Ingestion, Matrix, Mysql_connector
from django.contrib.auth.decorators import login_required
from airflow.models import DagRun

connection = None
database =None


@login_required(login_url='login')
def check_connector(request):
  try:
    connector = Mysql_connector.objects.get(user=request.user.id)
    if connector:
      # connection = get_mysql_connection(connector.username,connector.host,connector.password)
      id = connector.id
      service = connector.service_name
      return render(request,'connections/my_connector.html',{'service':service,'connector_id':id})
  except:
    messages.warning(request,"You have not made any connector yet!")
    return redirect('db_connection')  
  
  
@login_required(login_url='login')
def select_connector(request, connector_id):
  global connection
  connector = get_object_or_404(Mysql_connector, id=connector_id)
  if connector:
    connection = get_mysql_connection(connector.username,connector.host,connector.password,connector.database)
    if connection != None:
      messages.success(request, f'Connected to MySQL Database : {connector.database} successfully')
      return redirect('table_list')        
    else:
      messages.error(request, 'Failed to connect to MySQL database')
  return render(request, 'account/dashboard.html')
      
      
@login_required(login_url='login')  
def db_connection(request):
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
              user=request.user,  # Assuming user is logged in
              username= username,
              password= password,
              host = host,
              database = database
            )
            messages.success(request, 'Connected to MySQL database successfully')
            return redirect('table_list')
          else:
            messages.error(request, 'Failed to connect to MySQL database')
    return render(request, 'connections/create_connector.html')

   
def table_list(request):
    global connection,database
    if connection != None:
        all_tables = connection.execute('SHOW TABLES').fetchall()
        table = [table[0] for table in all_tables]
        return render(request, 'connections/tables.html', {'table': table})   
    else:
        return HttpResponse("Invalid credentials or no active connection")


def select_table(request):
  if request.method == 'POST':
    selected_table = request.POST.getlist('selected_table')      
    selected_tables_str = ','.join(selected_table)
    return redirect('selected_table', selected_table=selected_tables_str)
  else:
    return HttpResponse("Invalid request method")
      

def selected_table(request, selected_table):
    global connection
    if connection != None:
      try:
        connector = Mysql_connector.objects.get(user=request.user.id)
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
            
            
            result = connection.execute(f'SELECT * FROM {table}').fetchall()
            
            serialized_data = [dict(row) for row in result]
            df = pd.DataFrame(serialized_data)
            numeric_columns = df.select_dtypes(include=['int', 'float'])
            
            for column in numeric_columns:
              plt.figure(figsize=(8, 6))
              plt.boxplot(df[column].dropna())  # Drop NA values if any
              plt.title(f'Box Plot for {column}')
              plt.xlabel('Values')
              plt.ylabel('Frequency')
                        
              image_dir = 'box_plot_imgs'
              
              file_name = f'{connector.user_id}_{ingestion_instance.id}_{table}_{column}.png'
              image_file_path = os.path.join(image_dir, file_name)
              plt.savefig(image_file_path)
              plt.close()
            
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
      
      
