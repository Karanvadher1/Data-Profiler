from django.urls import path
from . import views


urlpatterns = [
   
   path('check_connector/',views.check_connector,name='check_connector'),
   path('db_connection/',views.db_connection,name='db_connection'),
   path('select_table/',views.select_table,name = 'select_table'),
   path('table_list/', views.table_list, name='table_list'),
   path('selected_table/<str:selected_table>/', views.selected_table, name='selected_table'),
   path('select-connector/<int:connector_id>', views.select_connector, name='select_connector'),
   
]
