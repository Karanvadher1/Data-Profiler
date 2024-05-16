from django.urls import path
from . import views1
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('',views1.HomeView.as_view(),name="home"),
    path('registeruser/',views1.RegisterUserView.as_view(),name='registeruser'), 
    path('login/',views1.LoginView.as_view(),name='login'),
    path('logout/',login_required(views1.LogoutView.as_view()),name='logout'),
    path('dashboard/',login_required(views1.DashboardView.as_view()),name='dashboard'),
    path('forgot_password/',views1.ForgotPasswordView.as_view(),name='forgot_password'),
    path('activate/<uidb64>/<token>/',views1.ActivateView.as_view(),name='activate'),
    path('reset_password_validate/<uidb64>/<token>/',views1.ResetPasswordValidateView.as_view(),name='reset_password_validate'),
    path('reset_password/',views1.ResetPasswordValidateView.as_view(),name='reset_password'),
    path('list_log/', views1.ListLogView.as_view(), name='list_log'),
]

