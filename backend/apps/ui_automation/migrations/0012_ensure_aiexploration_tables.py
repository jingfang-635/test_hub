# Generated manually: ensure AI exploration tables exist
# (0001/0002 recorded as applied but tables were missing in some DBs)

from django.conf import settings
from django.db import migrations


def ensure_exploration_tables(apps, schema_editor):
    connection = schema_editor.connection
    existing = set(connection.introspection.table_names())
    if 'ui_ai_exploration_tasks' in existing:
        return

    AIExplorationTask = apps.get_model('ui_automation', 'AIExplorationTask')
    AIExplorationCase = apps.get_model('ui_automation', 'AIExplorationCase')
    AIExplorationStep = apps.get_model('ui_automation', 'AIExplorationStep')

    schema_editor.create_model(AIExplorationTask)
    schema_editor.create_model(AIExplorationCase)
    schema_editor.create_model(AIExplorationStep)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('ui_automation', '0011_element_screenshot'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunPython(ensure_exploration_tables, noop_reverse),
            ],
        ),
    ]
