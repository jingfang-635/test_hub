from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/ui-automation/exploration/(?P<task_id>\d+)/$', consumers.UIExplorationConsumer.as_asgi()),
    re_path(
        r'^ws/ui-automation/element-picker/(?P<session_id>[\w-]+)/$',
        consumers.ElementPickerConsumer.as_asgi(),
    ),
]
