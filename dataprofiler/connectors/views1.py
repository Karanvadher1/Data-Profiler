from datetime import datetime
import os
import subprocess
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.views import View
from matplotlib import pyplot as plt
import pandas as pd
from account.models import User
from dataprofiler import settings
from .database import get_mysql_connection, get_postgresql_connection, get_postgresql_db_connection
from .models import Data_Warehouse, Ingestion,Mysql_connector
from django.contrib.auth.decorators import login_required
from airflow.models import DagRun
from django.utils.decorators import method_decorator
from django.views.generic import ListView,TemplateView,DeleteView


class Global:
    connection = None
    database = None
    db_username = None
    user_warehouse = None


class DataWarehouseListView(ListView):
    @method_decorator(login_required(login_url='login'))
    def get(self, request):
        data_warehouse = Data_Warehouse.objects.all()
        warehouses_info = []
        for warehouse in data_warehouse:
            warehouse_name = warehouse.warehouse_name
            image_filename = warehouse.warehouse_image.name
            image_path = os.path.join('images', 'icons', image_filename)
            warehouses_info.append({'name': warehouse_name, 'image_path': image_path})
        context = {'warehouses_info': warehouses_info}
        return render(request, 'connections/list_connector.html', context)
    

class SelectWarehouseView(View):
    @method_decorator(login_required(login_url='login'))
    def post(self, request):
        Global.user_warehouse = request.POST.get('warehouse')
        if Global.user_warehouse.lower() == 'mysql':
            return redirect('Mysql_connection')
        elif Global.user_warehouse.lower() == 'postgresql':
            return redirect('PostgreSQL_connection')
        else:
            return HttpResponse("Invalid warehouse")

        
class MySQLConnectionView(View):
    template_name = 'connections/mysql_connector.html'
    
    @method_decorator(login_required(login_url='login'))
    def get(self,request):
        return render(request,self.template_name)
    def post(self, request):
        username = request.POST.get('username')
        host = request.POST.get('host')
        Global.database = request.POST.get('database')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        if password != confirm_password:
            messages.warning(request, 'Confirm password did not match')
        else:
            Global.connection = get_mysql_connection(username, host, password)
            Global.db_username = username
            if Global.connection and Global.connection is not None:
                Mysql_connector.objects.update_or_create(
                    user=request.user,
                    username=username,
                    password=password,
                    host=host,
                )
                messages.success(request, 'Connected to MySQL database successfully')
                return redirect('list_mysql_db')
            else:
                messages.error(request, 'Failed to connect to MySQL database')
        return render(request, 'connections/mysql_connector.html')


class ListMysqldbView(ListView):
    def get(self,request):
        print("======================================")
        if Global.connection != None:
            all_databases = Global.connection.execute('show databases').fetchall()
            databases = [db[0] for db in all_databases ]
            print(databases)
            return render(request,'connections/list_database.html',{'databases':databases})
    def post(self,request):
        Global.database = request.POST.get('selected_database')
        return redirect('table_list')


class ListTableView(ListView):
    def get(self,request):
        if Global.connection != None:
            if Global.user_warehouse.lower() == 'mysql':
                Global.connection.execute(f'use {Global.database}')
                all_tables = Global.connection.execute('show tables').fetchall()
                tables = [table[0] for table in all_tables]
                return render(request, 'connections/tables.html', {'tables': tables})   
            if Global.user_warehouse.lower() == 'postgresql':
                connector = Mysql_connector.objects.get(user=request.user.id,service_name=Global.user_warehouse.lower(),username = Global.db_username.lower())
                Global.connection = get_postgresql_db_connection(connector.username,connector.host,connector.password,Global.database)
                Global.connection.execute(f'use {Global.database}')
                all_tables = Global.connection.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'").fetchall()
                tables = [table[0] for table in all_tables]
                return render(request, 'connections/tables.html', {'tables': tables})   
            else:
                return HttpResponse("Invalid warehouse type")
        else:
            return HttpResponse("Invalid credentials or no active connection")
    def post(self,request):
        selected_table = request.POST.getlist('selected_table')
        schedule_time = request.POST.getlist('schedule_time')
        if Global.connection != None:
            try:
                connector = Mysql_connector.objects.get(user=request.user.id,service_name=Global.user_warehouse.lower(),username = Global.db_username.lower())
                user_instance = User.objects.get(id=request.user.id)
                
                
                # Triggering airflow DAGs
                dag_id = 'etl_pipeline'
                try:
                    for table in selected_table:
                        data = {
                            'conf': f'{{"selected_table":"{table}","connector":"{connector.id}","user":"{connector.user_id}","db":"{Global.database} ","username":"{connector.username}", "host":"{connector.host}","password":"{connector.password}"}}',
                            'connector_id':connector.id,
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

                        result = Global.connection.execute(f'SELECT * FROM {table}').fetchall()      
                        serialized_data = [dict(row) for row in result]
                        df = pd.DataFrame(serialized_data)
                        if 'id' in df.columns:
                            df.drop(columns='id', inplace=True)
                        numeric_columns = df.select_dtypes(include=['int', 'float'])
                        numeric_columns = numeric_columns.dropna()
                        box_plot_data = numeric_columns.to_dict()
                        ingestion_instance.box_plot_data = box_plot_data
                        ingestion_instance.save()
                        
                        for schedule in schedule_time:
                            subprocess.run(['airflow', 'dags', 'trigger',dag_id, '-c', f'{{"service_name":"{connector.service_name}","schedule":"{schedule}","selected_table":"{table}","connector":"{connector.id}","ingestion_id":"{ingestion_instance.id}","user":"{connector.user_id}","db":"{Global.database} ","username":"{connector.username}", "host":"{connector.host}","password":"{connector.password}"}}'], check=True)
                            message = f"DAG {dag_id} triggered successfully"     
                            dag_runs = DagRun.find(dag_id=dag_id)
                            if schedule != None:
                                ingestion_instance.state = 'scheduled'
                                ingestion_instance.save()
                                if dag_runs:
                                #check status of dag
                                    for dag_run in dag_runs:
                                        current_state = dag_run.get_state()
                                        print(f"DAG run is currently in state: {current_state}")
                                        break 
                    return redirect('dashboard')
                except subprocess.CalledProcessError as e:
                    message = f"Error triggering DAG {dag_id}: {e}"
            except Mysql_connector.DoesNotExist:
                return HttpResponse("User credentials not found")
            return HttpResponse(message)
        else:
            return HttpResponse("Connection is not established.")
        
        
class CheckConnectorView(TemplateView):
    template_name = 'connections/my_connector.html'

    @method_decorator(login_required(login_url='login'), name='dispatch')
    def get(self, request):
        try:
            connector = Mysql_connector.objects.filter(user_id=request.user.id)
            connector_details = []
            if connector.exists():
                for conn in connector:
                    id = conn.id
                    service = conn.service_name
                    db_username = conn.username
                    connector_details.append({'id': id, 'service': service, 'username': db_username})
            context = {'connector_details': connector_details}
            return self.render_to_response(context)
        except Exception as e:
            messages.warning(request, "You have not made any connector yet!")
            return redirect('db_warehouse')
        
    def post(self,request):
        Global.db_username = request.POST.get('connector_id')
        if Global.db_username != None:
            connector = get_object_or_404(Mysql_connector, username=Global.db_username,user_id = request.user.id)
            if connector.service_name.lower() == 'mysql':
                Global.user_warehouse = 'mysql'
                Global.connection = get_mysql_connection(connector.username,connector.host,connector.password)
                if Global.connection != None:
                    messages.success(request, f'Connected to MySQL Database successfully')
                    return redirect('list_mysql_db')   
                else:
                    messages.error(request, 'Failed to connect to MySQL database')
            if connector.service_name.lower() == 'postgresql':
                Global.user_warehouse = 'postgresql'
                Global.connection = get_postgresql_connection(connector.username,connector.host,connector.password)
                if Global.connection != None:
                    messages.success(request, f'Connected to PostgreSQL Database : {connector.database} successfully')
                    return redirect('table_list')   
                else:
                    messages.error(request, 'Failed to connect to MySQL database')
            return render(request, 'account/dashboard.html')


class DeleteConnectorView(View):
    def get(self, request):
        delete_connector_id = request.GET.get('delete_connector_id')
        if delete_connector_id:
            connector = get_object_or_404(Mysql_connector, id=delete_connector_id)
            connector.delete()
            messages.success(request, 'Connector deleted successfully')
        return redirect('check_connector')

class Custom404View(TemplateView):
    template_name = '404.html'
    status_code = 404

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        response.status_code = self.status_code
        return response
    
    
