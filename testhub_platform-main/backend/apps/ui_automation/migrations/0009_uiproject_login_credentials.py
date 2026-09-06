from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ui_automation', '0008_locatorstrategy_name_unique'),
    ]

    operations = [
        migrations.AddField(
            model_name='uiproject',
            name='login_username',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='登录账号'),
        ),
        migrations.AddField(
            model_name='uiproject',
            name='login_password',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='登录密码'),
        ),
    ]
