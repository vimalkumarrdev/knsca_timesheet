from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("redirect/", views.redirect_by_role, name="redirect_by_role"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("profile/password/", views.AccountPasswordChangeView.as_view(), name="password_change"),
    path("profile/password/done/", views.AccountPasswordChangeDoneView.as_view(), name="password_change_done"),
]
