from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('requirement_analysis', '0009_knowledgebase_vector_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='knowledgedocument',
            name='chunk_count',
            field=models.PositiveIntegerField(default=0, verbose_name='分块数量'),
        ),
        migrations.AddField(
            model_name='knowledgedocument',
            name='is_vectorized',
            field=models.BooleanField(default=False, verbose_name='是否已向量化'),
        ),
        migrations.CreateModel(
            name='KnowledgeDocumentChunk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chunk_index', models.PositiveIntegerField(verbose_name='分块序号')),
                ('content', models.TextField(verbose_name='分块内容')),
                ('embedding', models.JSONField(blank=True, default=list, verbose_name='向量')),
                ('char_count', models.PositiveIntegerField(default=0, verbose_name='字符数')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='创建时间')),
                ('document', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='chunks',
                    to='requirement_analysis.knowledgedocument',
                    verbose_name='所属文档',
                )),
                ('knowledge_base', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='chunks',
                    to='requirement_analysis.knowledgebase',
                    verbose_name='所属知识库',
                )),
            ],
            options={
                'verbose_name': '知识库文档分块',
                'verbose_name_plural': '知识库文档分块',
                'db_table': 'knowledge_document_chunks',
                'ordering': ['document_id', 'chunk_index'],
                'unique_together': {('document', 'chunk_index')},
            },
        ),
    ]
