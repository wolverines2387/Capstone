"""
ASGI config for airbnb_app project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import django
django.setup()

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "airbnb_app.settings")

application = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
#import auction.routers # Do I really need this?
from channels.auth import AuthMiddlewareStack
import recomender.routers

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            recomender.routers.websocket_urlpatterns
        )
    ),
})
