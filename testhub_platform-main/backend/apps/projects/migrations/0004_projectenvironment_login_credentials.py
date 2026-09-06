from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0003_project_project_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectenvironment',
            name='login_username',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='登录账号'),
        ),
        migrations.AddField(
            model_name='projectenvironment',
            name='login_password',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='登录密码'),
        ),
    ]
