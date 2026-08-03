from django.urls import path

from . import views

app_name = "leaves"

urlpatterns = [
    path("", views.ManageLeavesView.as_view(), name="manage"),
    path("<int:pk>/delete/", views.LeaveDeleteView.as_view(), name="delete"),
]
