# Generated by Django 5.1.7 on 2025-05-01 13:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('secmomo', '0011_alter_agents_status'),
    ]

    operations = [
        migrations.RenameField(
            model_name='agents',
            old_name='agent_code',
            new_name='agentCode',
        ),
    ]
