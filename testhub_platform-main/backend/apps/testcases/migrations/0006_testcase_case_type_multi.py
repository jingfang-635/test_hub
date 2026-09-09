from django.db import migrations, models
import json


def encode_case_type_as_json_string(apps, schema_editor):
    """在仍为 CharField 时，把单值写成合法 JSON 数组字符串。"""
    TestCase = apps.get_model('testcases', 'TestCase')
    for tc in TestCase.objects.all().iterator():
        value = tc.case_type
        if isinstance(value, list):
            encoded = json.dumps(value or ['manual'], ensure_ascii=False)
        else:
            text = str(value or '').strip()
            if not text:
                parts = ['manual']
            elif text.startswith('['):
                try:
                    parsed = json.loads(text)
                    parts = parsed if isinstance(parsed, list) and parsed else ['manual']
                except (TypeError, ValueError, json.JSONDecodeError):
                    parts = ['manual']
            else:
                parts = [p.strip() for p in text.replace('、', ',').split(',') if p.strip()] or ['manual']
            encoded = json.dumps(parts, ensure_ascii=False)
        # CharField 存 JSON 文本，下一步 AlterField 才能正确解析
        TestCase.objects.filter(pk=tc.pk).update(case_type=encoded)


def decode_case_type_to_plain_string(apps, schema_editor):
    TestCase = apps.get_model('testcases', 'TestCase')
    for tc in TestCase.objects.all().iterator():
        value = tc.case_type
        if isinstance(value, list):
            plain = ','.join(value) if value else 'manual'
        else:
            text = str(value or '').strip()
            if text.startswith('['):
                try:
                    parsed = json.loads(text)
                    plain = ','.join(parsed) if isinstance(parsed, list) and parsed else 'manual'
                except (TypeError, ValueError, json.JSONDecodeError):
                    plain = 'manual'
            else:
                plain = text or 'manual'
        TestCase.objects.filter(pk=tc.pk).update(case_type=plain)


def default_case_types():
    return ['manual']


class Migration(migrations.Migration):

    dependencies = [
        ('testcases', '0005_testcase_case_type'),
    ]

    operations = [
        migrations.RunPython(encode_case_type_as_json_string, decode_case_type_to_plain_string),
        migrations.AlterField(
            model_name='testcase',
            name='case_type',
            field=models.JSONField(default=default_case_types, verbose_name='用例类型'),
        ),
    ]
