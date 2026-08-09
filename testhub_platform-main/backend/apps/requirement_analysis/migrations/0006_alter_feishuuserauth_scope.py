# Generated manually for Feishu OAuth scope length

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('requirement_analysis', '0005_feishuoauthstate'),
    ]

    operations = [
        migrations.AlterField(
            model_name='feishuuserauth',
            name='scope',
            field=models.TextField(blank=True, default='', verbose_name='授权 scope'),
        ),
    ]
