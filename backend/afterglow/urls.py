from django.urls import path

from . import views

urlpatterns = [
    path("auth/register/", views.register),
    path("auth/login/", views.login),
    path("auth/me/", views.me),
    path("auth/logout/", views.logout),
    path("universes/", views.universes),
    path("universes/<uuid:pk>/", views.universe_detail),
    path("universes/<uuid:pk>/invite/", views.rotate_invite),
    path("universes/<uuid:pk>/memories/", views.memories),
    path("memories/<uuid:pk>/moderate/", views.moderate_memory),
    path("memories/<uuid:pk>/media/", views.memory_media),
]
