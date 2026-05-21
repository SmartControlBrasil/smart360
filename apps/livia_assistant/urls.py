from django.urls import path

from . import views


app_name = "livia_assistant"

urlpatterns = [
    path("chat/", views.chat, name="chat"),
]
