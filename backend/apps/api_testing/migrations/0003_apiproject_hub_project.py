from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0003_project_project_types'),
        ('api_testing', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='apiproject',
            name='hub_project',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='api_project',
                to='projects.project',
                verbose_name='关联主项目',
            ),
        ),
    ]
