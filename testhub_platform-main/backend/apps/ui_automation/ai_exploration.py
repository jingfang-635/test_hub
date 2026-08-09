"""
AI探索测试执行器
基于 browser-use 自主探索，采集每个步骤的元素坐标(bounding rect + 点击点)和截图。
"""
import asyncio
import base64
import logging
import os
import uuid

from asgiref.sync import sync_to_async
from django.conf import settings

from .models import AIExplorationTask, AIExplorationCase, AIExplorationStep
from .ai_agent import BrowserAgent

logger = logging.getLogger('django')

# 探索任务停止信号（内存级，与 AI 智能模式的 STOP_SIGNALS 独立）
EXPLORATION_STOP_SIGNALS = {}


def _build_task_description(task):
    """根据数据来源 + 意图 + 代码仓库构造给 AI 的任务描述"""
    url = task.start_url
    ds = task.data_source
    case_content = (task.data_content or '').strip()
    intent = (task.intent_content or '').strip()
    repo = (task.repo_content or '').strip()
    env = task.environment or '默认'

    parts = [f"请访问 {url}。环境: {env}。"]
    if ds == 'autonomous':
        parts.append(
            "请自主探索页面功能，从首页开始，识别主要功能模块，"
            "逐个点击探索可交互元素（链接、按钮、表单、菜单），记录每个操作步骤，每完成一个功能点归纳总结。"
        )
    elif ds == 'case_driven':
        parts.append(f"根据以下功能用例描述执行测试：\n{case_content}\n按用例顺序执行，每条用例的每个步骤都要实际操作。")

    if intent:
        parts.append(f"参考用户的自然语言意图：{intent}。")
    if repo:
        parts.append(f"参考代码仓库信息：{repo}。")

    return ' '.join(parts)


def _extract_element_rect(element):
    """容错地从 browser-use 元素提取 bounding rect {x,y,width,height}"""
    if element is None:
        return {}
    # 尝试 rect / bounding_rect / bbox 属性
    for attr in ('rect', 'bounding_rect', 'bbox'):
        r = getattr(element, attr, None)
        if r is None:
            continue
        # 对象形式
        x = getattr(r, 'x', None)
        y = getattr(r, 'y', None)
        w = getattr(r, 'width', None)
        h = getattr(r, 'height', None)
        if x is not None and y is not None:
            return {'x': float(x), 'y': float(y), 'width': float(w or 0), 'height': float(h or 0)}
        # dict 形式
        if isinstance(r, dict) and 'x' in r:
            return {k: float(r.get(k, 0)) for k in ('x', 'y', 'width', 'height')}
    # 元素本身直接带坐标
    x = getattr(element, 'x', None)
    y = getattr(element, 'y', None)
    if x is not None and y is not None:
        return {
            'x': float(x), 'y': float(y),
            'width': float(getattr(element, 'width', 0) or 0),
            'height': float(getattr(element, 'height', 0) or 0),
        }
    return {}


def _rect_to_click_point(rect):
    """由 bounding rect 计算中心点击点"""
    if not rect or 'x' not in rect:
        return {}
    return {
        'x': rect['x'] + rect.get('width', 0) / 2,
        'y': rect['y'] + rect.get('height', 0) / 2,
    }


async def _take_screenshot(agent_instance):
    """采集当前页面截图，返回可访问的媒体URL路径"""
    try:
        bs = getattr(agent_instance, 'browser_session', None)
        if bs is None:
            return ''
        # browser-use BrowserSession 的 current_page 是 async 方法 get_current_page
        page = None
        if hasattr(bs, 'get_current_page'):
            page = await bs.get_current_page()
        else:
            for attr in ('current_page', 'page', '_current_page'):
                page = getattr(bs, attr, None)
                if page is not None:
                    break
        if page is None:
            return ''
        # browser-use Page.screenshot 返回 base64 字符串，需要 decode 为 bytes 再写入文件
        img_b64 = await page.screenshot(format='png')
        img_bytes = base64.b64decode(img_b64)
        folder = os.path.join(settings.MEDIA_ROOT, 'exploration_screenshots')
        os.makedirs(folder, exist_ok=True)
        fname = f"{uuid.uuid4().hex[:12]}.png"
        with open(os.path.join(folder, fname), 'wb') as f:
            f.write(img_bytes)
        return f"{settings.MEDIA_URL}exploration_screenshots/{fname}"
    except Exception as e:
        logger.warning(f"⚠️ 探索截图失败: {e}")
        return ''


async def _get_page_url(agent_instance):
    """获取当前页面URL"""
    try:
        bs = getattr(agent_instance, 'browser_session', None)
        if bs is None:
            return ''
        # browser-use BrowserSession 的 current_page 是 async 方法 get_current_page
        page = None
        if hasattr(bs, 'get_current_page'):
            page = await bs.get_current_page()
        else:
            page = getattr(bs, 'current_page', None) or getattr(bs, 'page', None)
        if page is not None:
            return str(getattr(page, 'url', '') or '')
        return ''
    except Exception:
        return ''


def _action_info(actions):
    """从 actions 列表提取首个带 index 的动作信息"""
    idx = None
    action_type = 'other'
    element_text = ''
    for a in actions:
        adict = a.model_dump() if hasattr(a, 'model_dump') else getattr(a, '_action_dict', {})
        for k in ('click', 'input', 'select_option', 'hover'):
            if k in adict and adict[k]:
                if k == 'click':
                    action_type = 'click'
                elif k == 'input':
                    action_type = 'input'
                elif k == 'select_option':
                    action_type = 'select'
                else:
                    action_type = 'other'
                params = adict[k] or {}
                idx = params.get('index')
                element_text = params.get('text', '') or ''
                return idx, action_type, element_text
        # 导航类
        for k in ('navigate', 'go_to_url', 'open_new_tab'):
            if k in adict and adict[k]:
                return None, 'navigate', str(adict[k].get('url', '') or '')
    return idx, action_type, element_text


def _make_exploration_channel_layer():
    """创建独立的 channel layer 实例（绑定当前事件循环，避免与 daphne 主循环的全局 layer 冲突）"""
    try:
        from channels_redis.core import RedisChannelLayer
        from django.conf import settings
        hosts = settings.CHANNEL_LAYERS['default']['CONFIG'].get('hosts', ['redis://127.0.0.1:6379/0'])
        return RedisChannelLayer(hosts=hosts)
    except Exception as e:
        logger.warning(f"创建独立 channel layer 失败: {e}")
        return None


def _get_browser_session(agent):
    """从 BrowserAgent 实例获取 browser-use Agent 的 browser_session"""
    # 优先从 _browser_use_agent（browser-use Agent 实例）获取
    bu_agent = getattr(agent, '_browser_use_agent', None)
    if bu_agent is not None:
        bs = getattr(bu_agent, 'browser_session', None)
        if bs is not None:
            return bs
    # 兼容：直接从 agent 获取
    return getattr(agent, 'browser_session', None)


async def _push_screenshot(agent, task_id, stop_event):
    """独立截图推送循环：实时投屏（JPEG ~3fps，低延迟）"""
    channel_layer = _make_exploration_channel_layer()
    if channel_layer is None:
        logger.error(f"❌ 探索投屏: channel layer 创建失败，无法推送截图 (task_id={task_id})")
        return
    group_name = f"ui_exploration_{task_id}"
    logger.info(f"📷 探索投屏循环已启动 (task_id={task_id}, group={group_name})")

    # 等待 browser_session 就绪（最多 90s）
    waited = 0.0
    while _get_browser_session(agent) is None and waited < 90 and not stop_event.is_set():
        await asyncio.sleep(0.5)
        waited += 0.5

    if _get_browser_session(agent) is None:
        logger.warning(f"⚠️ 探索投屏: 等待 90s 后 browser_session 仍未就绪 (task_id={task_id})")
        return

    logger.info(f"📷 探索投屏: browser_session 已就绪，开始推送截图 (task_id={task_id})")
    push_count = 0
    error_count = 0

    while not stop_event.is_set() and not EXPLORATION_STOP_SIGNALS.get(task_id, False):
        try:
            bs = _get_browser_session(agent)
            if bs is not None:
                # browser-use BrowserSession 的 current_page 是 async 方法 get_current_page，
                # 不是属性，必须 await 调用
                page = None
                if hasattr(bs, 'get_current_page'):
                    page = await bs.get_current_page()
                else:
                    page = getattr(bs, 'current_page', None) or getattr(bs, 'page', None)
                if page is not None:
                    # browser-use Page.screenshot(format=..., quality=...) 返回 base64 字符串
                    img_b64 = await page.screenshot(format='jpeg', quality=70)
                    await channel_layer.group_send(group_name, {
                        'type': 'screenshot_update',
                        'image': f"data:image/jpeg;base64,{img_b64}",
                    })
                    push_count += 1
                    if push_count == 1:
                        logger.info(f"📷 探索投屏: 首帧截图已推送 (task_id={task_id})")
        except Exception as e:
            error_count += 1
            if error_count <= 3 or error_count % 20 == 0:
                logger.warning(f"⚠️ 探索投屏截图失败 (task_id={task_id}, count={error_count}): {e}")
        await asyncio.sleep(0.3)

    logger.info(f"📷 探索投屏循环结束 (task_id={task_id}, 推送 {push_count} 帧, 错误 {error_count} 次)")


async def run_exploration(task_id):
    """执行探索任务（在 asyncio 事件循环中）"""
    task = await sync_to_async(AIExplorationTask.objects.get)(id=task_id)

    # 创建探索用例
    case = await sync_to_async(AIExplorationCase.objects.create)(
        task=task,
        name=f"{task.name}-探索用例",
        description="",
        order=0,
        status='running',
    )

    task_description = _build_task_description(task)
    step_counter = [0]
    logs_collector = []

    async def step_callback(payload):
        """接收 run_task 内部的 log/task 事件，收集日志"""
        if isinstance(payload, dict) and payload.get('type') == 'log':
            logs_collector.append(payload.get('content', ''))

    async def step_recorder(agent_instance, step_index, actions, action_str):
        """采集单步元素坐标和截图，写入 AIExplorationStep"""
        idx, action_type, element_text = _action_info(actions)

        # 从 agent state 获取元素 bounding rect
        rect = {}
        if idx is not None:
            try:
                state = getattr(agent_instance, 'state', None)
                elements = getattr(state, 'elements', None) or []
                if elements and idx < len(elements):
                    rect = _extract_element_rect(elements[idx])
            except Exception:
                pass

        click_point = _rect_to_click_point(rect)
        screenshot = await _take_screenshot(agent_instance)
        page_url = await _get_page_url(agent_instance)

        step_counter[0] += 1
        await sync_to_async(AIExplorationStep.objects.create)(
            case=case,
            order=step_counter[0],
            action_type=action_type,
            action_description=action_str,
            element_index=idx,
            element_text=element_text[:500],
            rect=rect,
            click_point=click_point,
            screenshot=screenshot,
            page_url=page_url[:1000],
            status='done',
        )

    agent = BrowserAgent(execution_mode='text', enable_gif=False, case_name=task.name)
    agent.step_recorder = step_recorder

    async def should_stop():
        return EXPLORATION_STOP_SIGNALS.get(task_id, False)

    # 启动实时投屏截图循环
    stop_event = asyncio.Event()
    screenshot_task = asyncio.create_task(_push_screenshot(agent, task_id, stop_event))

    try:
        result = await agent.run_full_process(
            task_description,
            step_callback=step_callback,
            should_stop=should_stop,
        )
        await sync_to_async(_finish_task)(task.id, case.id, 'passed', logs_collector)
        return result
    except KeyboardInterrupt:
        await sync_to_async(_finish_task)(task.id, case.id, 'stopped', logs_collector)
        return None
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"探索任务执行失败: {e}\n{tb}")
        await sync_to_async(_finish_task)(task.id, case.id, 'failed', logs_collector, f"{e}\n{tb}")
        return None
    finally:
        # 停止投屏循环
        stop_event.set()
        try:
            await asyncio.wait_for(screenshot_task, timeout=5)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            screenshot_task.cancel()
        # 推送任务结束状态
        try:
            _layer = _make_exploration_channel_layer()
            if _layer is not None:
                await _layer.group_send(f"ui_exploration_{task_id}", {
                    'type': 'exploration_status',
                    'status': 'finished',
                    'message': '探索任务已结束',
                })
        except Exception:
            pass


def _finish_task(task_id, case_id, status, logs_collector=None, error=''):
    """收尾：更新任务和用例状态"""
    from django.utils import timezone
    task = AIExplorationTask.objects.get(id=task_id)
    task.status = status
    task.end_time = timezone.now()
    if task.start_time:
        task.duration = (task.end_time - task.start_time).total_seconds()
    log_text = ''.join(logs_collector) if logs_collector else ''
    if error:
        log_text += f"\n[错误] {error}\n"
    task.logs = (task.logs or '') + log_text
    task.save()

    case_status = 'passed' if status == 'passed' else ('failed' if status == 'failed' else 'stopped')
    AIExplorationCase.objects.filter(id=case_id).update(status=case_status)


def run_exploration_sync(task_id):
    """同步入口（供后台线程调用）"""
    import sys
    if sys.platform == 'win32':
        # Windows: daphne/twisted 强制 SelectorEventLoop 不支持 subprocess，
        # 显式用 ProactorEventLoop 以支持 browser-use 启动浏览器子进程
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(run_exploration(task_id))
        finally:
            loop.close()
    return asyncio.run(run_exploration(task_id))
