from django.db import migrations, models


def copy_owner_username_to_text(apps, schema_editor):
    """将外键 owner 的用户名复制到临时文本字段 owner_text"""
    Version = apps.get_model('versions', 'Version')
    User = apps.get_model('users', 'User')
    for version in Version.objects.select_related('owner').all():
        # owner 此时还是外键（在 AlterField 之前执行）
        if version.owner_id:
            try:
                user = User.objects.get(id=version.owner_id)
                version.owner_text = user.username
            except User.DoesNotExist:
                version.owner_text = ''
        else:
            version.owner_text = ''
        version.save(update_fields=['owner_text'])


def reverse_copy(apps, schema_editor):
    """回滚操作：无操作"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('versions', '0003_version_owner'),
    ]

    operations = [
        # 1. 添加临时文本字段 owner_text
        migrations.AddField(
            model_name='version',
            name='owner_text',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='负责人(文本)'),
        ),
        # 2. 数据迁移：把外键 owner 的 username 复制到 owner_text
        migrations.RunPython(copy_owner_username_to_text, reverse_copy),
        # 3. 删除外键 owner
        migrations.RemoveField(
            model_name='version',
            name='owner',
        ),
        # 4. 重命名 owner_text 为 owner
        migrations.RenameField(
            model_name='version',
            old_name='owner_text',
            new_name='owner',
        ),
        # 5. 调整 owner 字段属性（确保 verbose_name 等元数据正确）
        migrations.AlterField(
            model_name='version',
            name='owner',
            field=models.CharField(blank=True, default='', max_length=200, verbose_name='负责人'),
        ),
    ]
