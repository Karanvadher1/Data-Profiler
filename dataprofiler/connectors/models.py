from datetime import datetime, timedelta
from django.db import models
from account.models import User



# Create your models here.
# class Connector(models.Model):



class Mysql_connector(models.Model):
  user = models.ForeignKey(User, on_delete=models.CASCADE)
  service_name = models.CharField(max_length=100,default = 'mysql')
  username = models.CharField(max_length=100)
  host = models.GenericIPAddressField()
  password = models.CharField(max_length=100)
    
    
class Ingestion(models.Model):
  user = models.ForeignKey(User, on_delete=models.CASCADE)
  connector = models.ForeignKey(Mysql_connector,on_delete=models.CASCADE)
  conf = models.TextField()
  dag_id = models.CharField(max_length=255)
  dag_run_id = models.CharField(max_length=255)
  data_interval_start = models.DateTimeField()
  data_interval_end = models.DateTimeField()
  end_date = models.DateTimeField(null=True, blank=True)
  external_trigger = models.BooleanField()
  last_scheduling_decision = models.CharField(max_length=255,null=True)
  logical_date = models.DateTimeField()
  run_type = models.CharField(max_length=255)
  start_date = models.DateTimeField()
  state = models.CharField(max_length=50)
  box_plot_data = models.JSONField(null=True, blank=True)
  
  @classmethod
  def create_ingestion(cls, **kwargs):
    return cls.objects.create(**kwargs)
  
  def __str__(self):
      return f"DAG Run ID: {self.dag_run_id}, State: {self.state}"
    
  def save(self, *args, **kwargs):
    self.data_interval_start = datetime.now()
    self.data_interval_end = datetime.now()
    self.start_date = datetime.now()
    self.logical_date = datetime.now()
    
    # Add 5 hours and 30 minutes to data_interval_start
    self.data_interval_start += timedelta(hours=5, minutes=30)
    self.data_interval_end +=timedelta(hours=5,minutes=30)
    self.start_date += timedelta(hours=5,minutes=30)
    self.logical_date += timedelta(hours=5,minutes=30)
    super().save(*args, **kwargs)
    
    
class Matrix(models.Model):
  user =  models.ForeignKey(User, on_delete=models.CASCADE)
  ingestion = models.ForeignKey(Ingestion,on_delete=models.CASCADE)
  connector = models.ForeignKey(Mysql_connector,on_delete=models.CASCADE)
  dataset = models.CharField(max_length=100)
  num_rows = models.IntegerField()
  num_columns = models.IntegerField()
  num_duplicate_rows = models.IntegerField()
  null_values_per_column = models.JSONField(max_length=1000)
  std_per_column_dict = models.JSONField(max_length=1000)
  status = models.CharField(max_length=100)




class Data_Warehouse(models.Model):
  warehouse_name = models.CharField(max_length=100)
  warehouse_image = models.ImageField(upload_to='data_warehouse',blank=True,null=True)