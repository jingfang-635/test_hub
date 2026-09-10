# Generated manually: add generated_code to AIExplorationTask and locator fields to AIExplorationStep

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ui_automation', '0013_add_ai_model_config_to_exploration_task'),
    ]

    operations = [
        migrations.AddField(
            model_name='aiexplorationtask',
            name='generated_code',
            field=models.CharField(max_length=10000, blank=True, default='', verbose_name='生成的测试代码'),
        ),
        migrations.AddField(
            model_name='aiexplorationstep',
            name='locator_strategy',
            field=models.CharField(blank=True, default='', max_length=50, verbose_name='定位策略'),
        ),
        migrations.AddField(
            model_name='aiexplorationstep',
            name='locator_value',
            field=models.CharField(blank=True, default='', max_length=500, verbose_name='定位值'),
        ),
    ]