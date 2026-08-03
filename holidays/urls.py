from django.urls import path

from . import views

app_name = "holidays"

urlpatterns = [
    path("", views.ManageHolidaysView.as_view(), name="manage"),
    path("<int:pk>/delete/", views.HolidayDeleteView.as_view(), name="delete"),
]
