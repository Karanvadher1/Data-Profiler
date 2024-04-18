# Create your views here.
import base64
from datetime import datetime
import glob
from io import BytesIO
import io
import json
import os
from connectors.models import Matrix,Ingestion
from .utils import send_verification_email
from .models import User
from django.contrib import auth,messages
from django.contrib.auth.decorators import login_required

from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import render,redirect
from django.core.paginator import Paginator
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
import seaborn as sns
from django.db.models import Count



def home(request):
  if request.user.is_authenticated:
    messages.warning(request,'You are already logged in')
    return redirect('dashboard')
  else:
    return render(request,'home.html')


def registeruser(request):
  if request.method == 'POST':
    # form = UserForm(request.POST)
    # if form.is_valid():
      #create user using form
      # password = form.cleaned_data['password']
      # user = form.save(commit=False)
      # user.set_password(password)
      
      #create user using create_user method
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
  ingestion_data = Ingestion.objects.filter(user_id=request.user.id).order_by('-start_date').all()

  matrix_data = []
  matrix = None
  columns = []
  null_values = []
  ingestion_data_list = []
  col1=[]
  std = []
  box_column_data = []
  box_value_data = []
  
  
  for ingestion in ingestion_data:  
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
      
    # Prepare the data dictionary to pass to the template
    

   
    if selected_ingestion:
      matrix = Matrix.objects.filter(ingestion_id=selected_ingestion).first()
      if matrix:
        matrix_data = {
          'id': matrix.ingestion_id,
          'dataset': matrix.dataset,
          'num_rows': matrix.num_rows,
          'num_cols': matrix.num_columns,
          'num_duplicate_row': matrix.num_duplicate_rows,
          'null_values_per_column_dict': matrix.null_values_per_column,
          'std_per_column': matrix.std_per_column_dict,
          # Add more fields as needed
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

  success_count =  Ingestion.objects.filter(user_id=request.user.id).annotate(matrix_count=Count('matrix')).exclude(matrix_count=0).count()
  failed_count = Ingestion.objects.filter(user_id = request.user.id,matrix__isnull=True).annotate(matrix_count=Count('matrix')).filter(matrix_count=0).count()
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
  }
  if box_column_data and box_value_data:
      context['box_column_data'] = box_column_data
      context['box_value_data'] = box_value_data
  return render(request,'account/dashboard.html',context)


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