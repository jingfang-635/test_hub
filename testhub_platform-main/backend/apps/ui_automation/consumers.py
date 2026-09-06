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
