from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='project_types',
            field=models.JSONField(blank=True, default=list, verbose_name='关联项目类型'),
        ),
    ]
