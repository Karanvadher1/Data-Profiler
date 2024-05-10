# Create your views here.
from datetime import datetime
import fnmatch
import json
import os
import pandas as pd
from connectors.models import Matrix,Ingestion
from .utils import send_verification_email
from .models import User
from django.contrib import auth,messages
from django.contrib.auth.decorators import login_required
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import render,redirect
from django.core.paginator import Paginator
from matplotlib import pyplot as plt
import seaborn as sns
from django.db.models import Count
from django.db.models import Count, Exists, OuterRef
import tensorflow as tf
import tensorflow_probability as tfp
from connectors.views import select_table


def home(request):
  if request.user.is_authenticated:
    messages.warning(request,'You are already logged in')
    return redirect('dashboard')
  else:
    return render(request,'home.html')


def registeruser(request):
  if request.method == 'POST':
    username = request.POST.get('username')
    email = request.POST.get('email')
    password = request.POST.get('password')
    confirm_password = request.POST.get('confirm_password')
    if password != confirm_password:
      messages.warning(request,'Confirm Password did not matched')
      return redirect('registeruser')
    else:
      user = User.objects.create_user(username=username,email=email,password=password)
      user.save()
      #sending mail to user
      mail_subject = 'please activate your acount'
      email_template = 'emails/account_verification_email.html'
      send_verification_email(request,user,mail_subject,email_template)
      messages.success(request,'Your account has been registed succesfully!')
      return redirect('login')
  else:
    return render(request,'account/registeruser.html')


def login(request):
  if request.user.is_authenticated:
    messages.warning(request,'You are already logged in')
    return redirect('dashboard')
  if request.method == 'POST':
    email = request.POST['email']
    password = request.POST['password']
    user = auth.authenticate(request,email=email,password=password)
    if user is not None:
      auth.login(request,user)
      messages.success(request, 'You are now logged in')
      return redirect('dashboard')
    else:
      messages.error(request, 'Invalid login credentials')
      return redirect('login')   
  return render(request, 'account/login.html')


def activate(request,uidb64,token):
  # Activate the user by setting the activate status to true
  try:
    uid = urlsafe_base64_decode(uidb64).decode()
    user = User._default_manager.get(pk=uid)
  except(TypeError, ValueError,OverflowError,User.DoesNotExist):
    user = None

  if user is not None and default_token_generator.check_token(user, token):
    user.is_active = True
    user.save()
    messages.success(request,'Congratulation! your account is activated')
    return redirect('login')
  else:
    messages.error(request,'Invalid activation link')
    return redirect('account/registeruser')


@login_required(login_url='login')
def dashboard(request):
  matrix_data = []
  matrix = None
  columns = []
  null_values = []
  ingestion_data_list = []
  col1=[]
  std = []
  box_column_data = []
  box_value_data = []
  logs = None

  ingestion_data = Ingestion.objects.filter(user_id=request.user.id).order_by('-start_date').all()

  for ingestion in ingestion_data:
    if Matrix.objects.filter(ingestion_id = ingestion.id).exists:
      if ingestion.state != 'success':
        ingestion.state = 'success'
        ingestion.save()
    else:
      ingestion.state = 'Failed'
    data_dict = {
      'id':ingestion.id,
      'selected_table': json.loads(ingestion.conf)['selected_table'],
      'start_date': ingestion.start_date.strftime('%Y-%m-%d %H:%M:%S'),  # Format as desired
      'interval_start': ingestion.data_interval_start.strftime('%Y-%m-%d %H:%M:%S'),  # Format as desired
      'interval_end': ingestion.data_interval_end.strftime('%Y-%m-%d %H:%M:%S'),  # Format as desired
      'state': ingestion.state
    }
    
    ingestion_data_list.append(data_dict)  
  #getting ingestion record from user 
  if request.method == 'POST':
    selected_ingestion = request.POST.get('ingestion_id')
    box_plot_data_query = Ingestion.objects.filter(id=selected_ingestion).values_list('box_plot_data').first()
    
    if box_plot_data_query:
      box_plot_data = box_plot_data_query[0]
      
      # Extract column names and data from the box plot data dictionary
      if box_plot_data is not None:
        for column_name, values in box_plot_data.items():
          # Append a tuple containing column name and its values to the list
          box_column_data.append(column_name)
          values_list = list(values.values())
          box_value_data.append(values_list)
           
    # if box_value_data is not None:
    #   try:
    #     box_value_dataframe = pd.DataFrame(box_value_data)
    #     box_value_tensor = tf.constant(box_value_dataframe.values, dtype=tf.float32)
    #     correlation_matrix = tfp.stats.correlation(box_value_tensor, sample_axis=0)
    #     rounded_correlation_matrix = tf.round(correlation_matrix)
    #     print("Correlation Matrix:")
    #     print(correlation_matrix)
    #     print(rounded_correlation_matrix)
    #     # mean = tf.reduce_mean(box_value_tensor, axis=0)
    #     # print(mean)
    #     # stddev = tf.sqrt(tf.reduce_mean(tf.square(box_value_tensor - mean), axis=0))
    #     # print(stddev)
    #     # normalized_data = (box_value_tensor - mean) / stddev
    #     # correlation_matrix = tf.matmul(box_value_tensor, box_value_tensor, transpose_a=True) / tf.cast(tf.shape(normalized_data)[0], tf.float32)
    #     # Corr_Matrix = tf.round(box_value_tensor.corr(),2)
    #     # print('coreellaattion:',Corr_Matrix)
    #     # print(box_value_dataframe)
    #   except Exception as e:
    #     print("An error occurred:", e)
    #   Prepare the data dictionary to pass to the template
    
    if selected_ingestion:
      matrix = Matrix.objects.filter(ingestion_id=selected_ingestion).first()
      if matrix:
        ingestion_record = Ingestion.objects.get(id=selected_ingestion)
        if ingestion_record.state != 'success':
          ingestion_record.state = 'success'
          ingestion_record.save()
          
        matrix_data = {
          'id': matrix.ingestion_id,
          'dataset': matrix.dataset,
          'num_rows': matrix.num_rows,
          'num_cols': matrix.num_columns,
          'num_duplicate_row': matrix.num_duplicate_rows,
          'null_values_per_column_dict': matrix.null_values_per_column,
          'std_per_column': matrix.std_per_column_dict,
        }
      else:
        matrix_data = None
    
    if matrix_data:
      null_values_per_column_dict = matrix_data.get('null_values_per_column_dict', {})
      columns = list(null_values_per_column_dict.keys())
      null_values = list(null_values_per_column_dict.values())

      std_per_column = matrix_data.get('std_per_column')
      col1=list(std_per_column.keys())
      std = list(std_per_column.values())
      
  paginator = Paginator(ingestion_data_list,5)
  page_number = request.GET.get('page')
  page_obj = paginator.get_page(page_number)  

  success_count = Ingestion.objects.filter(user_id=request.user.id,state = 'success').count()
  failed_count = Ingestion.objects.filter(user_id=request.user.id,state = 'Failed').count()
  total_count = Ingestion.objects.filter(user_id=request.user.id).count()
  
  context = {
    'success':success_count,
    'failed':failed_count,
    'total':total_count,
    'ingestion_data':page_obj,
    'matrix_data':matrix_data,
    'columns':json.dumps(columns),
    'null_values':json.dumps(null_values),
    'col1':json.dumps(col1),
    'std':json.dumps(std),
    'log' : logs,
  }
  if box_column_data and box_value_data:
      context['box_column_data'] = box_column_data
      context['box_value_data'] = box_value_data
  return render(request,'account/dashboard.html',context)


def list_log(request):
  if request.method == 'POST':
    selected_ingestion = request.POST.get('ingestion_id')
    dag_run = Ingestion.objects.filter(id=selected_ingestion).values_list('dag_run_id').first()
    if dag_run:
      dag_run_id = dag_run[0]
      datetime_obj = datetime.strptime(dag_run_id, "manual__%Y-%m-%dT%H:%M:%S.%f")
      target_directory = datetime_obj.strftime("manual__%Y-%m-%dT%H:%M")
      print(target_directory)
      log_file,log = airflow_log(target_directory)
      return render(request,'account/airflow_log.html',{'log_file':log_file,'log':log})


def airflow_log(substring):
  directory_path = '/home/master/airflow/logs/dag_id=etl_pipeline'
  log_file = []
  log = []
  try:
    matching_folders = [name for name in os.listdir(directory_path) if os.path.isdir(os.path.join(directory_path, name)) and substring in name]
    for folder in matching_folders:
      match_folder_path = os.path.join(directory_path,folder)
      if os.path.exists(match_folder_path) and os.path.isdir(match_folder_path):
        directory_contents = os.listdir(match_folder_path)
        for content in directory_contents:
          log_file.append(content)
          final_path = os.path.join(match_folder_path,content)
          if os.path.exists(final_path) and os.path.isdir(final_path):
              dirs = os.listdir(final_path)
              for dir in dirs:
                log_file_path = os.path.join(final_path, dir)
                with open(log_file_path, 'r') as f:
                  lines = f.readlines()
                  combined_log = ""
                  for i, line in enumerate(lines):
                      if "INFO" in line:
                          # Check if "INFO" is at the end of the line and there's more content in the next line
                          if line.strip().endswith("INFO") and i < len(lines) - 1:
                              combined_log += line.strip() + " " + lines[i + 1].strip() + "\n"
                          else:
                              combined_log += line.strip() + "\n"
                  log.append(combined_log)
      else:
        print("Directory '{}' does not exist or is not a directory.".format(directory_path))
    return log_file,log
  except:
    print("No Logs Found")
    
   
    


def logout(request):
  auth.logout(request)
  messages.info(request, 'You are loggedout')
  return redirect('home')
  
  
def forgot_password(request):
  if request.method == 'POST':
    email = request.POST['email']

    if User.objects.filter(email=email).exists():
      user = User.objects.get(email__exact = email)
      #send reset password email
      mail_subject = 'Reset your Password'
      email_template = 'emails/reset_password_email.html'
      send_verification_email(request,user,mail_subject,email_template)
      messages.success(request,'Password reset link has been sent to your email address')
      return redirect('login')
    else:
      messages.error(request,'Account does not exist')
      return redirect('forgot_password')
  return render(request,'account/forgot_password.html')
  
  
def reset_password_validate(request, uidb64, token):
  #validate the user by decodeing the token and user pk
  try:
    uid = urlsafe_base64_decode(uidb64).decode()
    user = User._default_manager.get(pk=uid)
  except(TypeError, ValueError,OverflowError,User.DoesNotExist):
    user = None
      
  if user is not None and default_token_generator.check_token(user, token):
    request.session['uid'] = uid
    messages.info(request,'Please reset your password')
    return redirect('reset_password')
  else:
    messages.error(request,'This link has been expired')
    return redirect('login')

    
def reset_password(request):
  if request.method == 'POST':
    password = request.POST['password']
    confirm_password = request.POST['confirm_password']

    if password == confirm_password:
      pk = request.session.get('uid')
      user = User.objects.get(pk=pk)
      user.set_password(password)
      user.is_active = True
      user.save()
      messages.success(request,'Password reset succesfull')
      return redirect('login')
    else:
      messages.error(request,'password do not match')
      return redirect('reset_password')
  return render(request,'account/reset_password.html')