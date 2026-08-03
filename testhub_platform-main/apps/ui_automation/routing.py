from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/ui-automation/exploration/(?P<task_id>\d+)/$', consumers.UIExplorationConsumer.as_asgi()),
]
