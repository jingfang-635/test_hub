from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ui_automation', '0010_remove_uiproject_base_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='element',
            name='screenshot',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='ui-automation/elements/',
                verbose_name='控件截图',
            ),
        ),
    ]
