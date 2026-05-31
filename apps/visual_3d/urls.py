from django.urls import path

from . import views


app_name = "visual_3d"

urlpatterns = [
    path("demo/", views.demo, name="demo"),
]
