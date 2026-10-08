from django.urls import re_path
from .consumers import ItemsConsumer

websocket_urlpatterns = [
    re_path(r"ws/items/$", ItemsConsumer.as_asgi()),
]
