# Generated manually for UiProject hub_project link

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ui_automation', '0004_alter_uischeduledtask_trigger_type'),
        ('projects', '0003_project_project_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='uiproject',
            name='hub_project',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='ui_project',
                to='projects.project',
                verbose_name='关联主项目',
            ),
        ),
    ]
