from datetime import datetime
import json
import os
import pandas as pd
from connectors.models import Matrix,Ingestion
from .utils import airflow_log, send_verification_email
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
# import tensorflow as tf
# import tensorflow_probability as tfp
from connectors.views import select_table
from django.views import View


class HomeView(View):
    def get(self,request):
        if request.user.is_authenticated:
            messages.warning(request,'You are already logged in')
            return redirect('dashboard')
        return render(request,'home.html')


class RegisterUserView(View):
    template_name = 'account/registeruser.html'
    def get(self,request):
        return render(request,self.template_name)
    
    def post(self,request):
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        if password != confirm_password:
            messages.warning(request,'Confirm Password did not matched')
            return redirect('registeruser')
    
        elif User.objects.filter(email=email).exists():
            messages.warning(request, 'Email is already registered')
            return redirect('registeruser')
    
        else:
            user = User.objects.create_user(username=username,email=email,password=password)
            user.save()
            # sending mail to user
            mail_subject = 'please activate your acount'
            email_template = 'emails/account_verification_email.html'
            send_verification_email(request,user,mail_subject,email_template)
            messages.success(request,'Your account has been registed succesfully!')
            return redirect('login')


class LoginView(View):
    template_name = 'account/login.html'
    def get(self,request):
        return render(request,self.template_name)
    
    def post(self,request):
        email = request.POST.get('email')
        password = request.POST.get('password')
        if request.user.is_authenticated:
            messages.warning(request,'You are already logged in')
            return redirect('dashboard')
        user = auth.authenticate(request,email=email,password=password)
        
        if user is not None:
            auth.login(request,user)
            messages.success(request, 'You are now logged in')
            return redirect('dashboard')
        else:        
            context = {
                "email": email,
                "password": password,
                "error": "Both fields are required."
            }
            return render(request, self.template_name, context)  

class ActivateView(View):
    def get(self,request,uidb64,token):
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
            return redirect('registeruser')
            

class DashboardView(View):
    template_name = 'account/dashboard.html'
    def get(self, request):
        return self.handle_request(request)

    def post(self, request):
        return self.handle_request(request)

    def handle_request(self, request):
        matrix_data = []
        columns = []
        null_values = []
        ingestion_data_list = []
        col1 = []
        std = []
        box_column_data = []
        box_value_data = []
        logs = None
        ingestion_data = Ingestion.objects.filter(user_id=request.user.id).annotate(
            has_matrix=Exists(Matrix.objects.filter(ingestion_id=OuterRef('pk')))
        ).order_by('-id')

        # Update states based on the existence of related Matrix records
        for ingestion in ingestion_data:
            ingestion.state = 'success' if ingestion.has_matrix else 'failed'
            ingestion.save()

        # Fetch all ingestion data with updated states
        for ingestion in ingestion_data:
            data_dict = {
                'id': ingestion.id,
                'selected_table': json.loads(ingestion.conf)['selected_table'],
                'start_date': ingestion.start_date.strftime('%Y-%m-%d %H:%M:%S'),
                'interval_start': ingestion.data_interval_start.strftime('%Y-%m-%d %H:%M:%S'),
                'interval_end': ingestion.data_interval_end.strftime('%Y-%m-%d %H:%M:%S'),
                'state': ingestion.state
            }
            ingestion_data_list.append(data_dict)
        if request.method == 'POST':
            selected_ingestion = request.POST.get('ingestion_id')
            box_plot_data_query = Ingestion.objects.filter(id=selected_ingestion).values_list('box_plot_data').first()

            if box_plot_data_query:
                box_plot_data = box_plot_data_query[0]
                if box_plot_data is not None:
                    for column_name, values in box_plot_data.items():
                        box_column_data.append(column_name)
                        values_list = list(values.values())
                        box_value_data.append(values_list)

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
                    }
                else:
                    matrix_data = None

            if matrix_data:
                null_values_per_column_dict = matrix_data.get('null_values_per_column_dict', {})
                columns = list(null_values_per_column_dict.keys())
                null_values = list(null_values_per_column_dict.values())

                std_per_column = matrix_data.get('std_per_column')
                col1 = list(std_per_column.keys())
                std = list(std_per_column.values())

        paginator = Paginator(ingestion_data_list, 5)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        success_count = Ingestion.objects.filter(user_id=request.user.id, state='success').count()
        failed_count = Ingestion.objects.filter(user_id=request.user.id, state='failed').count()
        total_count = Ingestion.objects.filter(user_id=request.user.id).count()

        context = {
            'success': success_count,
            'failed': failed_count,
            'total': total_count,
            'ingestion_data': page_obj,
            'matrix_data': matrix_data,
            'columns': json.dumps(columns),
            'null_values': json.dumps(null_values),
            'col1': json.dumps(col1),
            'std': json.dumps(std),
            'log': logs,
        }
        if box_column_data and box_value_data:
            context['box_column_data'] = box_column_data
            context['box_value_data'] = box_value_data

        return render(request, self.template_name, context)


class ListLogView(View):
    def post(self, request, *args, **kwargs):
        selected_ingestion = request.POST.get('ingestion_id')
        dag_run = Ingestion.objects.filter(id=selected_ingestion).values_list('dag_run_id').first()
        if dag_run:
            dag_run_id = dag_run[0]
            datetime_obj = datetime.strptime(dag_run_id, "manual__%Y-%m-%dT%H:%M:%S.%f")
            target_directory = datetime_obj.strftime("manual__%Y-%m-%dT%H:%M")
            log = airflow_log(target_directory)
            return render(request, 'account/airflow_log.html', {'log': log})


class ForgotPasswordView(View):
    template_name = 'account/forgot_password.html'
    def get(self,request):
        return render(request,self.template_name)
    
    def post(self,request):
        email = request.POST.get("email")
        if User.objects.filter(email = email).exists():
            user = User.objects.get(email__exact = email)
            mail_subject = 'Reset your Password'
            email_template = 'emails/reset_password_email.html'
            send_verification_email(request,user,mail_subject,email_template)
            messages.success(request,'Password reset link has been sent to your email address')
            return redirect('login')
        else:
            messages.error(request,'Account does not exist')
            return redirect('forgot_password')


class LogoutView(View):
    def get(self,request):
        auth.logout(request)
        messages.info(request, 'You are loggedout')
        return redirect('home')
    
    
class ResetPasswordValidateView(View):
    def get(self, request, uidb64=None, token=None):
        if uidb64 and token:
            try:
                uid = urlsafe_base64_decode(uidb64).decode()
                user = User._default_manager.get(pk=uid)
            except (TypeError, ValueError, OverflowError, User.DoesNotExist):
                user = None

            if user is not None and default_token_generator.check_token(user, token):
                request.session['uid'] = uid
                messages.info(request, 'Please reset your password')
                return redirect('reset_password')
            else:
                messages.error(request, 'This link has expired')
                return redirect('login')
        else:
            return render(request, 'account/reset_password.html')

    def post(self, request, *args, **kwargs):
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        if password == confirm_password:
            pk = request.session.get('uid')
            if pk:
                user = User.objects.get(pk=pk)
                user.set_password(password)
                user.is_active = True
                user.save()
                messages.success(request, 'Password reset successful')
                return redirect('login')
            else:
                messages.error(request, 'Invalid session. Please try the password reset process again.')
                return redirect('login')
        else:
            messages.error(request, 'Passwords do not match')
            return redirect('reset_password')