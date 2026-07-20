from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from .views import fractals_home, global_search

app_name = 'fractals'

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path('', fractals_home, name='fractals_home'),
    path("builder/", include("apps.sites_builder.urls", namespace="sites_builder")),
    path("code-analyzer/", include("apps.code_analyzer.urls")),
    path("okr/", include("apps.okr.urls")),
    path("janus/", include("apps.janus.urls")),
    path("athena/", include("apps.athena.urls", namespace="athena")),
    path("newsletters/", include("apps.hermes.urls")),
    path("tasks/", include("apps.task.urls", namespace="tasks")),
    path("mnemos/", include("apps.mnemos.urls", namespace="mnemos")),
    path("atlas/", include("apps.atlas.urls", namespace="atlas")),
    path("argus/", include("apps.argus.urls", namespace="argus")),
    path("agpay/", include("platform_apps.apps.agpay.urls", namespace="agpay")),
    path("common/", include("apps.common.urls", namespace="common")),
    path("search/", global_search, name="global-search"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
