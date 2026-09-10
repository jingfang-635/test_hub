"""元素拾取 API（测试步骤旁「拾取」按钮）。"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import element_picker_service as picker


class ElementPickerViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='start')
    def start(self, request):
        data = request.data or {}
        project_id = data.get('project_id') or data.get('project')
        url = data.get('url') or ''
        try:
            project_id_int = int(project_id)
        except (TypeError, ValueError):
            return Response({'error': '请指定有效的 project_id'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            sess = picker.start_for_user(request.user.id, project_id_int, url=url)
            session = sess.to_dict()
            # 首帧随 HTTP 返回，避免 WS 入组竞态导致「已启动但白屏」
            if sess._last_image:
                session['image'] = sess._last_image
            return Response({
                'message': '拾取会话已启动（检查元素模式，点击仅用于选元素）',
                'session': session,
            })
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except RuntimeError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001
            return Response({'error': f'启动失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='status')
    def status_view(self, request):
        sess = picker.get_session_for_user(request.user.id)
        if not sess:
            return Response({'session': None})
        return Response({'session': sess.to_dict()})

    @action(detail=False, methods=['post'], url_path='inspect')
    def inspect(self, request):
        sess = picker.get_session_for_user(request.user.id)
        if not sess or sess.status != 'ready':
            return Response({'error': '拾取会话未就绪'}, status=status.HTTP_400_BAD_REQUEST)
        data = request.data or {}
        try:
            x = float(data.get('x', 0))
            y = float(data.get('y', 0))
            img_w = float(data.get('img_w') or data.get('width') or 1)
            img_h = float(data.get('img_h') or data.get('height') or 1)
            result = sess.inspect(x, y, img_w, img_h)
            return Response({'result': result, 'session': sess.to_dict()})
        except Exception as exc:  # noqa: BLE001
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='click')
    def click(self, request):
        """非检查态：把投屏点击转发到真实页面。"""
        sess = picker.get_session_for_user(request.user.id)
        if not sess or sess.status != 'ready':
            return Response({'error': '拾取会话未就绪'}, status=status.HTTP_400_BAD_REQUEST)
        data = request.data or {}
        try:
            x = float(data.get('x', 0))
            y = float(data.get('y', 0))
            img_w = float(data.get('img_w') or data.get('width') or 1)
            img_h = float(data.get('img_h') or data.get('height') or 1)
            button = (data.get('button') or 'left').strip().lower()
            click_count = int(data.get('click_count') or 1)
            image = sess.click(x, y, img_w, img_h, button=button, click_count=click_count)
            return Response({'ok': True, 'image': image, 'session': sess.to_dict()})
        except Exception as exc:  # noqa: BLE001
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='type')
    def type_keys(self, request):
        """非检查态：向页面输入文字或按键。"""
        sess = picker.get_session_for_user(request.user.id)
        if not sess or sess.status != 'ready':
            return Response({'error': '拾取会话未就绪'}, status=status.HTTP_400_BAD_REQUEST)
        data = request.data or {}
        text = data.get('text')
        key = (data.get('key') or '').strip()
        try:
            image = ''
            if text is not None and str(text) != '':
                image = sess.type_text(str(text))
            elif key:
                image = sess.press(key)
            else:
                return Response({'error': '缺少 text 或 key'}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'ok': True, 'image': image})
        except Exception as exc:  # noqa: BLE001
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='scroll')
    def scroll(self, request):
        sess = picker.get_session_for_user(request.user.id)
        if not sess or sess.status != 'ready':
            return Response({'error': '拾取会话未就绪'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            delta_y = float((request.data or {}).get('delta_y', 0))
            image = sess.scroll(delta_y)
            return Response({'ok': True, 'image': image})
        except Exception as exc:  # noqa: BLE001
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='navigate')
    def navigate(self, request):
        sess = picker.get_session_for_user(request.user.id)
        if not sess or sess.status != 'ready':
            return Response({'error': '拾取会话未就绪'}, status=status.HTTP_400_BAD_REQUEST)
        url = ((request.data or {}).get('url') or '').strip()
        if not url:
            return Response({'error': '缺少 url'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            result = sess.navigate(url)
            page_url = result.get('page_url') if isinstance(result, dict) else result
            image = result.get('image', '') if isinstance(result, dict) else ''
            return Response({'page_url': page_url, 'image': image, 'session': sess.to_dict()})
        except Exception as exc:  # noqa: BLE001
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='save-element')
    def save_element(self, request):
        """一键填入：根据检查结果创建/更新元素（含控件截图、页面、名称）。"""
        sess = picker.get_session_for_user(request.user.id)
        if not sess or sess.status != 'ready':
            return Response({'error': '拾取会话未就绪'}, status=status.HTTP_400_BAD_REQUEST)
        data = request.data or {}
        strategy = (data.get('strategy') or '').strip()
        value = (data.get('value') or '').strip()
        if not strategy or not value:
            return Response({'error': '缺少 strategy/value'}, status=status.HTTP_400_BAD_REQUEST)
        backups = data.get('backup_locators') or data.get('backups') or []
        if not isinstance(backups, list):
            backups = []
        tag = (data.get('tag') or '').strip()
        try:
            result = sess.save_element(
                strategy=strategy,
                value=value,
                backup_locators=backups,
                tag=tag,
                user=request.user,
            )
            return Response(result)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001
            return Response({'error': f'保存元素失败: {exc}'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='stop')
    def stop(self, request):
        sess = picker.stop_for_user(request.user.id)
        if not sess:
            return Response({'message': '当前没有拾取会话', 'session': None})
        return Response({'message': '已结束拾取', 'session': sess.to_dict()})
