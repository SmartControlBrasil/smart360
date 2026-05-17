from django.urls import path

from .views import LoginView, MeView, MyMembershipListView

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="users-login"),
    path("me/", MeView.as_view(), name="users-me"),
    path("memberships/", MyMembershipListView.as_view(), name="users-memberships"),
]
