"""UI 自动化 WebSocket Consumer（探索投屏 / 元素拾取投屏）"""
import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger(__name__)


class UIExplorationConsumer(AsyncJsonWebsocketConsumer):
    """探索任务实时投屏：前端订阅 ws/ui-automation/exploration/<task_id>/"""

    async def connect(self):
        try:
            self.task_id = self.scope["url_route"]["kwargs"]["task_id"]
            self.group_name = f"ui_exploration_{self.task_id}"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            logger.info(f"探索投屏 WS 已连接: task_id={self.task_id}")
        except Exception as e:
            logger.error(f"探索投屏 WS 连接失败: {e}")
            await self.close()

    async def disconnect(self, close_code):
        try:
            if hasattr(self, 'group_name'):
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
        except Exception:
            pass

    async def screenshot_update(self, event):
        """接收后端 group_send 的截图，转发给前端"""
        try:
            await self.send_json({
                'type': 'screenshot',
                'image': event.get('image', ''),
            })
        except Exception as e:
            logger.error(f"推送截图失败: {e}")

    async def plan_update(self, event):
        """用例矩阵规划完成推送（探索前先展示给用户）"""
        try:
            await self.send_json({
                'type': 'plan_update',
                'cases': event.get('cases', []),
            })
        except Exception as e:
            logger.error(f"推送用例矩阵失败: {e}")

    async def log_update(self, event):
        """实时日志推送"""
        try:
            await self.send_json({
                'type': 'log_update',
                'log': event.get('log', ''),
            })
        except Exception as e:
            logger.error(f"推送日志失败: {e}")

    async def exploration_status(self, event):
        """接收任务状态变更（开始/结束）"""
        try:
            await self.send_json({
                'type': 'status',
                'status': event.get('status', ''),
                'message': event.get('message', ''),
            })
        except Exception:
            pass

    async def step_update(self, event):
        """单步执行实时推送：含元素坐标、定位器、截图"""
        try:
            await self.send_json({
                'type': 'step_update',
                'case_id': event.get('case_id'),
                'case_name': event.get('case_name', ''),
                'step': event.get('step', {}),
            })
        except Exception as e:
            logger.error(f"推送步骤失败: {e}")

    async def case_update(self, event):
        """用例完成推送：含用例状态、步骤数"""
        try:
            await self.send_json({
                'type': 'case_update',
                'case_id': event.get('case_id'),
                'case_name': event.get('case_name', ''),
                'status': event.get('status', ''),
                'step_count': event.get('step_count', 0),
            })
        except Exception as e:
            logger.error(f"推使用例失败: {e}")

    async def test_result(self, event):
        """探索完成推送最终生成的测试用例代码"""
        try:
            await self.send_json({
                'type': 'test_result',
                'status': event.get('status', ''),
                'cases': event.get('cases', []),
                'generated_code': event.get('generated_code', ''),
            })
        except Exception as e:
            logger.error(f"推送测试结果失败: {e}")


class ElementPickerConsumer(AsyncJsonWebsocketConsumer):
    """元素拾取实时投屏：ws/ui-automation/element-picker/<session_id>/"""

    async def connect(self):
        try:
            self.session_id = self.scope['url_route']['kwargs']['session_id']
            self.group_name = f'ui_element_picker_{self.session_id}'
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            logger.info('元素拾取 WS 已连接: session_id=%s', self.session_id)
        except Exception as e:
            logger.error('元素拾取 WS 连接失败: %s', e)
            await self.close()

    async def disconnect(self, close_code):
        try:
            if hasattr(self, 'group_name'):
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
        except Exception:
            pass

    async def screenshot_update(self, event):
        try:
            await self.send_json({
                'type': 'screenshot',
                'image': event.get('image', ''),
                'page_url': event.get('page_url', ''),
            })
        except Exception as e:
            logger.error('拾取投屏推送失败: %s', e)
