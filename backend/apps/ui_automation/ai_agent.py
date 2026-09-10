import logging
import asyncio
from .ai_base import BaseBrowserAgent

logger = logging.getLogger('django')

class BrowserAgent(BaseBrowserAgent):
    """
    Standard Browser Agent for Text Mode.
    Inherits all base functionality without applying dangerous visual patches.
    """
    def __init__(self, execution_mode='text', enable_gif=True, case_name=None):
        self.enable_gif = enable_gif
        self.case_name = case_name or "Adhoc Task"
        super().__init__(execution_mode='text')

# ============================================================================
# EXPORTED FUNCTIONS (FACTORY)
# ============================================================================

def get_agent_class(execution_mode='text'):
    # 始终返回文本模式实现
    return BrowserAgent

def run_ai_task_sync(task_description: str, planned_tasks=None, callback=None, should_stop=None, execution_mode='text', on_agent_ready=None):
    agent = BrowserAgent(execution_mode='text')
    return asyncio.run(agent.run_task(
        task_description, planned_tasks, callback, should_stop, on_agent_ready=on_agent_ready
    ))
    
def analyze_task_sync(task_description: str, execution_mode='text'):
    agent = BrowserAgent(execution_mode='text')
    return asyncio.run(agent.analyze_task(task_description))

def run_full_process_sync(task_description: str, analysis_callback=None, step_callback=None, should_stop=None, execution_mode='text', enable_gif=True, case_name=None, screencast_group=None, planned_tasks=None, on_agent_ready=None, storage_state=None, initial_url=None, capture_recorder=None):
    logger.info(f"DEBUG: Entering run_full_process_sync with execution_mode=text, enable_gif={enable_gif}")

    agent = BrowserAgent(execution_mode='text', enable_gif=enable_gif, case_name=case_name)
    # 「AI生成步骤」元素采集器（控件截图 + 备用选择器），在 on_step_end 中消费
    if capture_recorder is not None:
        agent.capture_recorder = capture_recorder

    logger.info(f"DEBUG: Agent created successfully ({type(agent).__name__}), starting asyncio.run")

    if screencast_group is None:
        return asyncio.run(agent.run_full_process(
            task_description, analysis_callback, step_callback, should_stop,
            planned_tasks=planned_tasks, on_agent_ready=on_agent_ready,
            storage_state=storage_state, initial_url=initial_url
        ))

    # 启用实时投屏：在同一事件循环中并行推送截图
    from .ai_screencast import push_screenshot_loop

    async def run_with_screencast():
        stop_event = asyncio.Event()

        async def _should_stop():
            # 投屏停止信号由外部置位，或在任务结束/用户停止时触发
            return stop_event.is_set()

        # 若调用方未提供 should_stop，构造一个合并信号；否则使用调用方的
        def _wrap_should_stop(inner):
            if inner is None:
                return _should_stop

            async def _merged_stop():
                if stop_event.is_set():
                    return True
                if asyncio.iscoroutinefunction(inner):
                    return await inner()
                return inner()
            return _merged_stop

        screencast_task = asyncio.create_task(
            push_screenshot_loop(agent, screencast_group, stop_event)
        )
        try:
            return await agent.run_full_process(
                task_description, analysis_callback, step_callback,
                _wrap_should_stop(should_stop), planned_tasks=planned_tasks,
                on_agent_ready=on_agent_ready,
                storage_state=storage_state, initial_url=initial_url
            )
        finally:
            stop_event.set()
            try:
                await asyncio.wait_for(screencast_task, timeout=5)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                screencast_task.cancel()

    return asyncio.run(run_with_screencast())


def run_ai_task_sync_screencast(task_description, group_name=None, analysis_callback=None, step_callback=None,
                                should_stop=None, execution_mode='text', enable_gif=True, case_name=None,
                                planned_tasks=None, on_agent_ready=None):
    """带实时投屏的执行：在同一个 asyncio 事件循环里并行启动截图推送循环。

    Returns:
        (history, agent)
    """
    logger.info(f"[screencast] Entering run with screencast, group={group_name}")
    agent = BrowserAgent(execution_mode='text', enable_gif=enable_gif, case_name=case_name)
    history = None

    async def _run_with_screencast():
        nonlocal history
        from .ai_screencast import push_screenshot_loop
        stop_event = asyncio.Event()
        group = group_name or f"ui_ai_{id(agent)}"
        task = None
        if group_name:
            task = asyncio.create_task(push_screenshot_loop(agent, group, stop_event))
        try:
            history = await agent.run_full_process(
                task_description,
                analysis_callback=analysis_callback,
                step_callback=step_callback,
                should_stop=should_stop,
                planned_tasks=planned_tasks,
                on_agent_ready=on_agent_ready,
            )
        finally:
            if group_name:
                stop_event.set()
                try:
                    await asyncio.wait_for(task, timeout=5)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    if task:
                        task.cancel()
        return history

    asyncio.run(_run_with_screencast())
    return history, agent
