from django.db import models
from account.models import User
import base64

# Create your models here.
# class Connector(models.Model):

class Mysql_connector(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    service_name = models.CharField(default = 'mysql')
    username = models.CharField(max_length=100)
    host = models.GenericIPAddressField()
    password = models.CharField(max_length=100)
    
    

