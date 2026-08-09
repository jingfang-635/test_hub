import asyncio
import logging
import time

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger(__name__)


class AppExecutionConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        try:
            self.execution_id = self.scope["url_route"]["kwargs"]["execution_id"]
            self.group_name = f"app_execution_{self.execution_id}"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            logger.info(f"WebSocket 连接成功: execution_id={self.execution_id}")
        except Exception as e:
            logger.error(f"WebSocket 连接失败: {e}")
            await self.close()

    async def disconnect(self, close_code):
        try:
            if hasattr(self, 'group_name'):
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
                logger.info(f"WebSocket 断开: execution_id={self.execution_id}, code={close_code}")
        except Exception as e:
            logger.error(f"WebSocket 断开处理失败: {e}")

    async def execution_update(self, event):
        try:
            await self.send_json(event)
        except Exception as e:
            logger.error(f"WebSocket 推送消息失败: {e}")


class AppDeviceRemoteConsumer(AsyncJsonWebsocketConsumer):
    """
    设备远程投屏 / 控制。
    路径: ws/app-automation/devices/<device_pk>/remote/
    """

    FRAME_INTERVAL = 0.35  # ~3fps，兼顾延迟与 ADB 压力
    QUALITY_MAP = {
        'low': 35,
        'balanced': 55,
        'high': 75,
    }

    async def connect(self):
        self.device_pk = self.scope["url_route"]["kwargs"]["device_pk"]
        self._stream_task = None
        self._fg_task = None
        self._running = False
        self.screen_width = 0
        self.screen_height = 0
        self.adb_path = 'adb'
        self.serial = None
        self.device_name = ''
        self.jpeg_quality = self.QUALITY_MAP['balanced']

        device = await self._load_device()
        if not device:
            await self.close(code=4404)
            return

        if device['status'] == 'offline':
            await self.accept()
            await self.send_json({
                'type': 'status',
                'status': 'error',
                'message': '设备离线，无法远程连接',
            })
            await self.close(code=4400)
            return

        self.serial = device['device_id']
        self.device_name = device['name'] or device['device_id']
        self.adb_path = await self._get_adb_path()

        await self.accept()
        await self.send_json({
            'type': 'device_info',
            'id': device['id'],
            'name': self.device_name,
            'device_id': self.serial,
            'status': device['status'],
            'android_version': device.get('android_version') or '',
        })
        await self.send_json({
            'type': 'status',
            'status': 'connected',
            'message': '远程连接已建立，正在获取画面...',
        })

        self._running = True
        self._stream_task = asyncio.create_task(self._stream_frames())
        self._fg_task = asyncio.create_task(self._poll_foreground())
        logger.info(f"设备远程投屏已连接: pk={self.device_pk}, serial={self.serial}")

    async def disconnect(self, close_code):
        self._running = False
        for task in (self._stream_task, self._fg_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._stream_task = None
        self._fg_task = None
        logger.info(f"设备远程投屏断开: pk={self.device_pk}, code={close_code}")

    async def receive_json(self, content, **kwargs):
        msg_type = (content or {}).get('type')
        if not msg_type or not self.serial:
            return

        try:
            if msg_type == 'tap':
                x, y = self._to_device_xy(content.get('x'), content.get('y'))
                if x is None:
                    return
                ok = await asyncio.to_thread(
                    self._tap, x, y
                )
                if not ok:
                    await self.send_json({'type': 'status', 'status': 'warn', 'message': '点击指令发送失败'})

            elif msg_type == 'swipe':
                x1, y1 = self._to_device_xy(content.get('x1'), content.get('y1'))
                x2, y2 = self._to_device_xy(content.get('x2'), content.get('y2'))
                if None in (x1, y1, x2, y2):
                    return
                duration = int(content.get('duration') or 300)
                ok = await asyncio.to_thread(
                    self._swipe, x1, y1, x2, y2, duration
                )
                if not ok:
                    await self.send_json({'type': 'status', 'status': 'warn', 'message': '滑动指令发送失败'})

            elif msg_type == 'key':
                key = content.get('keycode') or content.get('key')
                ok = await asyncio.to_thread(self._key, key)
                if not ok:
                    await self.send_json({'type': 'status', 'status': 'warn', 'message': f'按键失败: {key}'})

            elif msg_type == 'text':
                text = content.get('text') or ''
                ok = await asyncio.to_thread(self._text, text)
                if not ok:
                    await self.send_json({'type': 'status', 'status': 'warn', 'message': '文本输入失败'})

            elif msg_type == 'set_quality':
                level = str(content.get('quality') or 'balanced').lower()
                self.jpeg_quality = self.QUALITY_MAP.get(level, self.QUALITY_MAP['balanced'])
                await self.send_json({
                    'type': 'status',
                    'status': 'connected',
                    'message': f'画质已切换: {level}',
                })

            elif msg_type == 'get_foreground':
                pkg = await asyncio.to_thread(self._foreground)
                await self.send_json({'type': 'foreground', 'package': pkg or ''})

            elif msg_type == 'ping':
                await self.send_json({'type': 'pong', 'ts': time.time()})

        except Exception as e:
            logger.error(f'处理远程控制消息失败: {e}')
            await self.send_json({
                'type': 'status',
                'status': 'warn',
                'message': f'控制指令异常: {e}',
            })

    async def _poll_foreground(self):
        while self._running:
            try:
                pkg = await asyncio.to_thread(self._foreground)
                await self.send_json({'type': 'foreground', 'package': pkg or ''})
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.debug(f'轮询前台应用失败: {e}')
            await asyncio.sleep(3)

    async def _stream_frames(self):
        from .utils.remote_control import capture_screen_jpeg, to_data_url_jpeg

        consecutive_errors = 0
        while self._running:
            started = time.monotonic()
            try:
                result = await asyncio.to_thread(
                    capture_screen_jpeg, self.adb_path, self.serial, self.jpeg_quality
                )
                if result:
                    jpeg_bytes, width, height = result
                    self.screen_width = width
                    self.screen_height = height
                    consecutive_errors = 0
                    await self.send_json({
                        'type': 'frame',
                        'image': to_data_url_jpeg(jpeg_bytes),
                        'width': width,
                        'height': height,
                    })
                else:
                    consecutive_errors += 1
                    if consecutive_errors == 1 or consecutive_errors % 5 == 0:
                        await self.send_json({
                            'type': 'status',
                            'status': 'warn',
                            'message': '获取画面失败，请检查设备 ADB 连接',
                        })
                    if consecutive_errors >= 20:
                        await self.send_json({
                            'type': 'status',
                            'status': 'error',
                            'message': '连续截图失败，已断开远程连接',
                        })
                        await self.close(code=4408)
                        return
            except asyncio.CancelledError:
                raise
            except Exception as e:
                consecutive_errors += 1
                logger.error(f'投屏推帧异常: {e}')
                if consecutive_errors >= 20:
                    await self.send_json({
                        'type': 'status',
                        'status': 'error',
                        'message': f'投屏异常: {e}',
                    })
                    await self.close(code=4500)
                    return

            elapsed = time.monotonic() - started
            await asyncio.sleep(max(0.05, self.FRAME_INTERVAL - elapsed))

    def _to_device_xy(self, nx, ny):
        """将归一化坐标 (0~1) 转为设备像素坐标。"""
        try:
            nx = float(nx)
            ny = float(ny)
        except (TypeError, ValueError):
            return None, None

        if self.screen_width <= 0 or self.screen_height <= 0:
            return None, None

        # 兼容误传像素坐标
        if nx > 1.5 or ny > 1.5:
            return int(nx), int(ny)

        nx = min(max(nx, 0.0), 1.0)
        ny = min(max(ny, 0.0), 1.0)
        return int(nx * self.screen_width), int(ny * self.screen_height)

    def _tap(self, x, y):
        from .utils.remote_control import adb_input_tap
        return adb_input_tap(self.adb_path, self.serial, x, y)

    def _swipe(self, x1, y1, x2, y2, duration):
        from .utils.remote_control import adb_input_swipe
        return adb_input_swipe(self.adb_path, self.serial, x1, y1, x2, y2, duration)

    def _key(self, key):
        from .utils.remote_control import adb_input_key
        return adb_input_key(self.adb_path, self.serial, key)

    def _text(self, text):
        from .utils.remote_control import adb_input_text
        return adb_input_text(self.adb_path, self.serial, text)

    def _foreground(self):
        from .utils.remote_control import get_foreground_package
        return get_foreground_package(self.adb_path, self.serial)

    @database_sync_to_async
    def _load_device(self):
        from .models import AppDevice
        try:
            device = AppDevice.objects.get(pk=self.device_pk)
            return {
                'id': device.id,
                'device_id': device.device_id,
                'name': device.name,
                'status': device.status,
                'android_version': device.android_version,
            }
        except AppDevice.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f'加载设备失败: {e}')
            return None

    @database_sync_to_async
    def _get_adb_path(self):
        try:
            from .models import AppTestConfig
            config = AppTestConfig.objects.first()
            return config.adb_path if config and config.adb_path else 'adb'
        except Exception:
            return 'adb'
