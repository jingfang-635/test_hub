"""一次性脚本：直接跑 case 8，验证收藏幂等点击。"""
import asyncio
import json
import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent
_PROJECT_ROOT = str(_BACKEND.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.ui_automation.models import TestCase
from apps.ui_automation.playwright_engine import PlaywrightTestEngine


def build_steps():
    tc = TestCase.objects.get(id=8)
    steps_data = []
    for step in tc.steps.all().order_by('step_number'):
        element_data = None
        if step.element:
            element_data = {
                'locator_strategy': step.element.locator_strategy.name if step.element.locator_strategy else 'css',
                'locator_value': step.element.locator_value,
                'name': step.element.name,
                'wait_timeout': step.element.wait_timeout,
                'force_action': step.element.force_action,
                'backup_locators': step.element.backup_locators or [],
            }
        # 预取 step 字段，避免 async 里再访问 ORM
        steps_data.append({
            'step_number': step.step_number,
            'action_type': step.action_type,
            'description': step.description,
            'input_value': step.input_value,
            'wait_time': step.wait_time,
            'assert_type': step.assert_type,
            'assert_value': step.assert_value,
            'element_data': element_data,
            'step': step,
        })
    return steps_data


async def run_async(steps_data):
    # 与前端 /run/ 默认一致：有头模式（列表点商品偶发不跳转）
    engine = PlaywrightTestEngine(browser_type='chromium', headless=False)
    await engine.start()
    results = []
    ok_all = True
    try:
        for item in steps_data:
            step = item['step']
            success, log, shot = await engine.execute_step(step, item['element_data'] or {})
            results.append({
                'step_number': item['step_number'],
                'action_type': item['action_type'],
                'description': item['description'],
                'success': success,
                'log': (log or '')[:500],
            })
            print(f"[{'OK' if success else 'FAIL'}] step {item['step_number']}: {item['description']}")
            if log:
                print(log[:300])
            if not success:
                ok_all = False
                break
    finally:
        await engine.stop()
    return ok_all, results


if __name__ == '__main__':
    steps = build_steps()
    ok, results = asyncio.run(run_async(steps))
    with open('case8_direct_result.json', 'w', encoding='utf-8') as f:
        json.dump({'success': ok, 'steps': results}, f, ensure_ascii=False, indent=2)
    print('FINAL:', ok)
