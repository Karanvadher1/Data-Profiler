# Create your views here.
from .utils import send_verification_email
from .models import User
from .forms import UserForm
from django.contrib import auth,messages
from django.contrib.auth.decorators import login_required

from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import render,redirect


def home(request):
  return render(request,'home.html')


def registeruser(request):
  if request.method == 'POST':
    form = UserForm(request.POST)
    if form.is_valid():
      #create user using form
      # password = form.cleaned_data['password']
      # user = form.save(commit=False)
      # user.set_password(password)
      
      #create user using create_user method
      username = form.cleaned_data['username']
      email = form.cleaned_data['email']
      password = form.cleaned_data['password']
      user = User.objects.create_user(username=username,email=email,password=password)
      user.save()
      
      #sending mail to user
      mail_subject = 'please activate your acount'
      email_template = 'emails/account_verification_email.html'
      send_verification_email(request,user,mail_subject,email_template)
      messages.success(request,'Your account has been registed succesfully!')
      return redirect('login')
    else:
      return redirect('home')
  else:
    form = UserForm(request.POST)
    context = {
      'form':form
    }
    return render(request,'account/registeruser.html',context)


def login(request):
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
  return render(request,'account/dashboard.html')


@login_required(login_url='login')
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