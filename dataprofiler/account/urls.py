from django.urls import path
from . import views


urlpatterns = [
   path('',views.home,name='home'),
   path('registeruser/',views.registeruser,name='registeruser'),
   path('login/',views.login,name='login'),  
   path('logout/',views.logout,name='logout'),
   path('forgot_password/',views.forgot_password,name='forgot_password'),
   path('reset_password_validate/<uidb64>/<token>/',views.reset_password_validate,name='reset_password_validate'),
   path('reset_password/',views.reset_password,name='reset_password'),
   
   path('activate/<uidb64>/<token>',views.activate,name='activate'),
   
   path('dashboard/',views.dashboard,name='dashboard'), 
   path('dashboard/', views.dashboard, name='dashboard_with_pagination'),
   path('dashboard/<str:box_plot>/', views.dashboard, name='dashboard'),

] 

