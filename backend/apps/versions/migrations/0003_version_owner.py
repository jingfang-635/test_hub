from django.db import migrations, models
import django.db.models.deletion


def populate_owner_from_created_by(apps, schema_editor):
    """将已有版本的 owner 设置为 created_by"""
    Version = apps.get_model('versions', 'Version')
    User = apps.get_model('users', 'User')
    for version in Version.objects.all():
        if version.created_by_id and not version.owner_id:
            version.owner = version.created_by
            version.save(update_fields=['owner'])


def reverse_populate_owner(apps, schema_editor):
    """回滚操作：无操作"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
        ('versions', '0002_version_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='version',
            name='owner',
            field=models.ForeignKey(
                default=None,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='owned_versions',
                to='users.user',
                verbose_name='负责人',
            ),
            preserve_default=False,
        ),
        migrations.RunPython(populate_owner_from_created_by, reverse_populate_owner),
        migrations.AlterField(
            model_name='version',
            name='owner',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='owned_versions',
                to='users.user',
                verbose_name='负责人',
            ),
        ),
    ]
