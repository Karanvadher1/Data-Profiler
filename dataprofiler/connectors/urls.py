from django.urls import path
from . import views


urlpatterns = [
   path('connector/',views.connector,name='connector'),
   path('select_table/',views.select_table,name='select_table'),
   path('select_database/',views.select_database,name='select_database'),
   path('selected_database/<str:selected_database>/', views.selected_database, name='selected_database'),
   
   path('selected_table/<str:selected_table>/', views.selected_table, name='selected_table'),
   
]
