from django.http import HttpResponse
import  mysql.connector
from django.shortcuts import render, redirect
from django.contrib import messages


def connector(request):
  if request.method == 'POST':
      username = request.POST.get('username')
      password = request.POST.get('password')
      confirm_password = request.POST.get('confirm_password')
      if password != confirm_password:
        messages.warning(request,'Confirm password did not matched')
      else:
        try:
          conn = mysql.connector.connect(user=username,password = password,host = '0.0.0.0')
          if conn.is_connected():
              cursor = conn.cursor()
              query = 'show databases'
              cursor.execute(query)
              all_database = cursor.fetchall()
              database = [database[0] for database in all_database]
              
              return render(request,'connections/database.html',{'database':database})
          else:
              return HttpResponse("invalid credentials")
        except mysql.connector.Error as e:
          return HttpResponse("Error connecting to database: " + str(e))
  else:
    return render(request, 'connections/connector.html')


def select_database(request):
  if request.method == 'POST':
    selected_database = request.POST.get('selected_database')
    return redirect('selected_database', selected_database=selected_database)
  else:
    return HttpResponse("Invalid request method")

   
def selected_database(request, selected_database):
  return render(request, 'connections/selected_table.html', {'selected_database': selected_database})


def select_table(request):
  if request.method == 'POST':
    selected_table = request.POST.get('selected_table')
    return redirect('selected_table', selected_table=selected_table)
  else:
    return HttpResponse("Invalid request method")
      

def selected_table(request, selected_table):
  return render(request, 'connections/selected_table.html', {'selected_table': selected_table})

