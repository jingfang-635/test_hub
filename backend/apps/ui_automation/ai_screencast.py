"""
AI 智能测试（Adhoc 执行）实时投屏

与 AI 探索测试的投屏共用同一套推送模式：
  - 前端订阅 ws/ui-automation/ai-screencast/<execution_id>/
  - 后端在 run_adhoc 的后台任务里启动一个独立截图推送循环（JPEG ~3fps），
    通过 channel layer 实时推送到浏览器。

独立 channel layer 实例绑定当前事件循环，避免与 daphne 主循环的全局 layer 冲突。
"""
import asyncio
import logging

logger = logging.getLogger('django')


def _make_ai_channel_layer():
    """创建独立的 channel layer 实例（绑定当前事件循环）"""
    try:
        from channels_redis.core import RedisChannelLayer
        from django.conf import settings
        hosts = settings.CHANNEL_LAYERS['default']['CONFIG'].get('hosts', ['redis://127.0.0.1:6379/0'])
        return RedisChannelLayer(hosts=hosts)
    except Exception as e:
        logger.warning(f"创建独立 channel layer 失败: {e}")
        return None


def get_browser_session(agent):
    """从 BrowserAgent 实例获取 browser-use Agent 的 browser_session"""
    # 优先从 _browser_use_agent（browser-use Agent 实例）获取
    bu_agent = getattr(agent, '_browser_use_agent', None)
    if bu_agent is not None:
        bs = getattr(bu_agent, 'browser_session', None)
        if bs is not None:
            return bs
    # 兼容：直接从 agent 获取
    return getattr(agent, 'browser_session', None)


async def push_screenshot_loop(agent, group_name, stop_event, wait_timeout=90):
    """独立截图推送循环：实时投屏（JPEG ~3fps，低延迟）

    Args:
        agent: BrowserAgent 实例（含 _browser_use_agent.browser_session）
        group_name: channel layer group 名
        stop_event: asyncio.Event，任务结束时置位以停止推送
        wait_timeout: 等待 browser_session 就绪的超时（秒）
    """
    channel_layer = _make_ai_channel_layer()
    if channel_layer is None:
        logger.error(f"❌ AI投屏: channel layer 创建失败，无法推送截图 (group={group_name})")
        return

    logger.info(f"📷 AI投屏循环已启动 (group={group_name})")

    # 等待 browser_session 就绪
    waited = 0.0
    while get_browser_session(agent) is None and waited < wait_timeout and not stop_event.is_set():
        await asyncio.sleep(0.5)
        waited += 0.5

    if get_browser_session(agent) is None:
        logger.warning(f"⚠️ AI投屏: 等待 {wait_timeout}s 后 browser_session 仍未就绪 (group={group_name})")
        return

    logger.info(f"📷 AI投屏: browser_session 已就绪，开始推送截图 (group={group_name})")
    push_count = 0
    error_count = 0

    while not stop_event.is_set():
        try:
            bs = get_browser_session(agent)
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
                        logger.info(f"📷 AI投屏: 首帧截图已推送 (group={group_name})")
        except Exception as e:
            error_count += 1
            if error_count <= 3 or error_count % 20 == 0:
                logger.warning(f"⚠️ AI投屏截图失败 (group={group_name}, count={error_count}): {e}")
        await asyncio.sleep(0.3)

    logger.info(f"📷 AI投屏循环结束 (group={group_name}, 推送 {push_count} 帧, 错误 {error_count} 次)")
