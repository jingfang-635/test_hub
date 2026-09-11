# Generated manually for AppProject hub_project link

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app_automation', '0002_initial'),
        ('projects', '0003_project_project_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='appproject',
            name='hub_project',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='app_project',
                to='projects.project',
                verbose_name='关联主项目',
            ),
        ),
    ]
