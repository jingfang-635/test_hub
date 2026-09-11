# Generated manually for Feishu OAuth state persistence

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('requirement_analysis', '0004_feishuuserauth'),
    ]

    operations = [
        migrations.CreateModel(
            name='FeishuOAuthState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('state', models.CharField(db_index=True, max_length=128, unique=True, verbose_name='state')),
                ('expires_at', models.DateTimeField(verbose_name='过期时间')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='feishu_oauth_states',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': '飞书 OAuth State',
                'verbose_name_plural': '飞书 OAuth State',
                'db_table': 'feishu_oauth_state',
            },
        ),
    ]
