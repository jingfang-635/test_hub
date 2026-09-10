from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('requirement_analysis', '0008_knowledgebasellmconfig'),
    ]

    operations = [
        migrations.AddField(
            model_name='knowledgebase',
            name='chunk_size',
            field=models.PositiveIntegerField(default=500, verbose_name='分块大小'),
        ),
        migrations.AddField(
            model_name='knowledgebase',
            name='chunk_overlap',
            field=models.PositiveIntegerField(default=50, verbose_name='分块重叠'),
        ),
        migrations.AddField(
            model_name='knowledgebase',
            name='enable_vectorization',
            field=models.BooleanField(default=True, verbose_name='是否向量化'),
        ),
    ]
