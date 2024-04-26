from django.urls import path
from . import views


urlpatterns = [
   
   path('db_warehouse/',views.db_warehouse,name='db_warehouse'),
   path('select_warehouse/', views.select_warehouse, name='select_warehouse'),
   path('check_connector/',views.check_connector,name='check_connector'),
   path('select_connector/', views.select_connector, name='select_connector'),
   path('delete_connector/', views.delete_connector, name='delete_connector'),
   path('select_table/',views.select_table,name = 'select_table'),
   
   path('list_mysql_db/',views.list_mysql_db,name='list_mysql_db'),
   path('select_mysql_db/',views.select_mysql_db,name='select_mysql_db'),
   
   path('list_postgres_db/',views.list_postgres_db,name='list_postgres_db'),
   path('select_postgres_db/',views.select_postgres_db,name='select_postgres_db'),
   
   path('Mysql_connection/',views.Mysql_connection,name='Mysql_connection'),
   path('postgresql_connection/',views.PostgreSQL_connection,name='PostgreSQL_connection'),
   
   path('select_table/',views.select_table,name = 'select_table'),
   path('table_list/', views.table_list, name='table_list'),
   path('selected_table/<str:selected_table>/', views.selected_table, name='selected_table'),
   
]

handler404 = 'connectors.views.custom_404_view'