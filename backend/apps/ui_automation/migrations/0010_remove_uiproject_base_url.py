from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ui_automation', '0009_uiproject_login_credentials'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='uiproject',
            name='base_url',
        ),
    ]
