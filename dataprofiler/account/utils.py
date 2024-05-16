from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage
from django.conf import settings
import os


def send_verification_email(request,user,mail_subject,email_template):
    current_site = get_current_site(request) 
    from_email = settings.DEFAULT_FROM_EMAIL
    message = render_to_string(email_template,{
        'user' : user,
        'domain' : current_site,
        'uid' : urlsafe_base64_encode(force_bytes(user.pk)),
        'token' : default_token_generator.make_token(user)
    })
    to_email = user.email
    mail = EmailMessage(mail_subject,message,to=[to_email])
    mail.send()


def send_notification(mail_subject,mail_template,context):
    from_email = settings.DEFAULT_FROM_EMAIL
    message = render_to_string(mail_template,context)
    to_email = context['user'].email
    mail = EmailMessage(mail_subject,message,from_email,to=[to_email])
    mail.send()
    
def airflow_log(substring):
  directory_path = '/home/master/airflow/logs/dag_id=etl_pipeline'
  log = {}
  try:
    matching_folders = [name for name in os.listdir(directory_path) if os.path.isdir(os.path.join(directory_path, name)) and substring in name]
    for folder in matching_folders:
        match_folder_path = os.path.join(directory_path,folder)
        if os.path.exists(match_folder_path) and os.path.isdir(match_folder_path):
            directory_contents = os.listdir(match_folder_path)
            for content in directory_contents:
                
                final_path = os.path.join(match_folder_path,content)
                if os.path.exists(final_path) and os.path.isdir(final_path):
                    dirs = os.listdir(final_path)
                    for dir in dirs:
                        log_file_path = os.path.join(final_path, dir)
                        with open(log_file_path, 'r') as f:
                            lines = f.readlines()
                            combined_log = ""
                            for i, line in enumerate(lines):
                                if "INFO" in line:
                                    # Check if "INFO" is at the end of the line and there's more content in the next line
                                    if line.strip().endswith("INFO") and i < len(lines) - 1:
                                        combined_log += line.strip() + " " + lines[i + 1].strip() + "\n"
                                    else:
                                        combined_log += line.strip() + "\n"
                                log[content]=combined_log
        else:
            print("Directory '{}' does not exist or is not a directory.".format(directory_path))
    return log
  except:
    print("No Logs Found")