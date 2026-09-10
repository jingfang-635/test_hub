from collections import defaultdict

from django.db import migrations, models


def dedupe_locator_strategies(apps, schema_editor):
    LocatorStrategy = apps.get_model('ui_automation', 'LocatorStrategy')
    Element = apps.get_model('ui_automation', 'Element')

    by_name = defaultdict(list)
    for strategy in LocatorStrategy.objects.all().order_by('id'):
        by_name[strategy.name].append(strategy)

    for items in by_name.values():
        if len(items) < 2:
            continue
        keep, dups = items[0], items[1:]
        for dup in dups:
            Element.objects.filter(locator_strategy_id=dup.id).update(locator_strategy_id=keep.id)
            dup.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('ui_automation', '0007_element_order'),
    ]

    operations = [
        migrations.RunPython(dedupe_locator_strategies, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='locatorstrategy',
            name='name',
            field=models.CharField(max_length=50, unique=True, verbose_name='策略名称'),
        ),
    ]
