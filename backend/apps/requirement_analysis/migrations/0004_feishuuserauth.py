# Generated manually for Feishu user OAuth

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('requirement_analysis', '0003_testcasegenerationtask_source_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='FeishuUserAuth',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('access_token', models.TextField(verbose_name='user_access_token')),
                ('refresh_token', models.TextField(blank=True, default='', verbose_name='refresh_token')),
                ('token_expires_at', models.DateTimeField(blank=True, null=True, verbose_name='access_token 过期时间')),
                ('refresh_expires_at', models.DateTimeField(blank=True, null=True, verbose_name='refresh_token 过期时间')),
                ('scope', models.CharField(blank=True, default='', max_length=500, verbose_name='授权 scope')),
                ('open_id', models.CharField(blank=True, default='', max_length=100, verbose_name='飞书 open_id')),
                ('union_id', models.CharField(blank=True, default='', max_length=100, verbose_name='飞书 union_id')),
                ('feishu_name', models.CharField(blank=True, default='', max_length=100, verbose_name='飞书显示名')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='feishu_auth',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='用户',
                )),
            ],
            options={
                'verbose_name': '飞书用户授权',
                'verbose_name_plural': '飞书用户授权',
                'db_table': 'feishu_user_auth',
            },
        ),
    ]
