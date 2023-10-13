from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/recomender/(?P<product_id>\d+)/$', consumers.RecomenderConsumer.as_asgi()),
]