from django.urls import path
from . import views1


urlpatterns = [
    path('db_warehouse/',views1.DataWarehouseListView.as_view(),name='db_warehouse'),
    path('check_connector/',views1.CheckConnectorView.as_view(),name='check_connector'),
    path('select_warehouse/',views1.SelectWarehouseView.as_view(),name='select_warehouse'),
    path('Mysql_connection/',views1.MySQLConnectionView.as_view(),name='Mysql_connection'),
    path('list_mysql_db/',views1.ListMysqldbView.as_view(),name='list_mysql_db'),
    path('select_mysql_db/',views1.ListMysqldbView.as_view(),name='select_mysql_db'),
    path('table_list/',views1.ListTableView.as_view(),name='table_list'),
    path('select_table/',views1.ListTableView.as_view(),name='select_table'),
    path('select_connector/',views1.CheckConnectorView.as_view(),name='select_connector'),
    path('delete_connector/',views1.DeleteConnectorView.as_view(),name='delete_connector'),
    path('404/', views1.Custom404View.as_view(), name='custom_404'),
]



handler404 = 'connectors.views.custom_404_view'