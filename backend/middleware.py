import time
from django.utils.deprecation import MiddlewareMixin


class DisableCSRFMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # 对所有API路径禁用CSRF检查
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)


class PerformanceLoggingMiddleware(MiddlewareMixin):
    """请求性能采集中间件：记录每个请求的响应时间、状态码、用户、IP 等"""
    # 排除静态资源、媒体、健康检查等路径，避免日志膨胀
    EXCLUDE_PREFIXES = ('/static/', '/media/', '/admin/jsi18n/', '/favicon.ico')

    def process_request(self, request):
        request._perf_start_time = time.time()

    def process_response(self, request, response):
        try:
            start = getattr(request, '_perf_start_time', None)
            if start is None:
                return response
            path = request.path
            if path.startswith(self.EXCLUDE_PREFIXES):
                return response
            response_time = (time.time() - start) * 1000  # ms
            from apps.core.models import RequestPerformanceLog
            user = None
            if getattr(request, 'user', None) and request.user.is_authenticated:
                user = request.user
            # 获取真实 IP（兼容代理）
            ip = request.META.get('HTTP_X_FORWARDED_FOR')
            if ip:
                ip = ip.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR')
            RequestPerformanceLog.objects.create(
                path=path[:500],
                method=request.method,
                response_time=response_time,
                status_code=response.status_code,
                user=user,
                ip_address=ip,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
        except Exception:
            pass
        return response