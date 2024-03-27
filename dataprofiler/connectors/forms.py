from django import forms

class DatabaseConnectionForm(forms.Form):
  service = forms.CharField(label='Service', max_length=100)
  user_host = forms.CharField(label='Host', max_length=100)
  user_port = forms.IntegerField(label='Port', initial=5432)  # Default PostgreSQL port is 5432
  user_username = forms.CharField(label='Username', max_length=100)
  user_password = forms.CharField(label='Password', widget=forms.PasswordInput)
  user_db_name = forms.CharField(label='Database Name', max_length=100)
