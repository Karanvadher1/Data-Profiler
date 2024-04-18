# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractBaseUser,BaseUserManager


class UserManager(BaseUserManager):
  def create_user(self, username, email, password=None):
    if not email:
      raise ValueError('user must have an E-mail address')

    if not username:
      raise ValueError('user must have an username')

    user = self.model(
      email = self.normalize_email(email),
      username = username,
    )
    user.set_password(password)
    user.save(using=self._db)
    return user
  
  
  def create_superuser(self,username, email, password=None):
    user = self.create_user(
      email = self.normalize_email(email),
      username = username,
      password = password,
    )   
    user.is_active = True
    user.is_staff = True
    user.is_superadmin = True
    user.save(using = self._db)
    return user


class User(AbstractBaseUser):
  username = models.CharField(max_length=50,unique=True)
  email = models.EmailField(max_length=100,unique=True)

  #required static fields
  date_joined = models.DateTimeField(auto_now_add=True)
  last_login = models.DateTimeField(auto_now_add=True)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)
  is_active = models.BooleanField(default=False)
  is_staff = models.BooleanField(default=False)
  is_superadmin = models.BooleanField(default=False)
  
  USERNAME_FIELD = 'email'
  REQUIRED_FIELDS = ['username']

  objects = UserManager()
  
  def __str__(self):
      return self.email
    
  def has_perm(self, perm, obj=None):
    return self.is_staff

  def has_module_perms(self, app_label):
    return True



