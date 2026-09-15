from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_deactivate_legacy_bot_configs'),
        ('ui_automation', '0020_repair_codegen_conversion_table'),
    ]

    operations = [
        migrations.AddField(
            model_name='uischeduledtask',
            name='notification_template',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='ui_scheduled_tasks',
                to='core.notificationtemplate',
                verbose_name='通知模板',
            ),
        ),
    ]
