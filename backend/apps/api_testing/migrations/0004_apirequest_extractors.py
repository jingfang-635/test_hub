from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api_testing', '0003_apiproject_hub_project'),
    ]

    operations = [
        migrations.AddField(
            model_name='apirequest',
            name='extractors',
            field=models.JSONField(default=list, verbose_name='变量提取规则'),
        ),
    ]
