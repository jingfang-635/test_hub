from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api_testing', '0004_apirequest_extractors'),
    ]

    operations = [
        migrations.AddField(
            model_name='testsuiterequest',
            name='extractors',
            field=models.JSONField(default=list, verbose_name='变量提取规则'),
        ),
        migrations.AddField(
            model_name='testsuiterequest',
            name='skip_condition',
            field=models.TextField(blank=True, default='', verbose_name='跳过条件'),
        ),
    ]
