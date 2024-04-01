from django.urls import path
from . import views


urlpatterns = [
   path('db_connection/',views.db_connection,name='db_connection'),
   path('db_list/',views.db_list,name='db_list'),
   
   path('select_table/',views.select_table,name = 'select_table'),
   path('select_database/',views.select_database,name='select_database'),
   path('table_list/<str:database>/', views.table_list, name='table_list'),
   
   path('selected_table/<str:selected_table>/', views.selected_table, name='selected_table'),
   
]
