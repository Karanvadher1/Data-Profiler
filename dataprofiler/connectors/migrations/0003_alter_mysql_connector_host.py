# Generated by Django 5.0.3 on 2024-04-01 11:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('connectors', '0002_alter_mysql_connector_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mysql_connector',
            name='host',
            field=models.GenericIPAddressField(),
        ),
    ]