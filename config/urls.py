from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("timesheets/", include("timesheets.urls")),
    path("leaves/", include("leaves.urls")),
    path("holidays/", include("holidays.urls")),
    path("projects/", include("projects.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("claims/", include("claims.urls")),
    path("", RedirectView.as_view(pattern_name="accounts:redirect_by_role", permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
