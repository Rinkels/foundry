from django.urls import path
from . import views

app_name = "sites_builder"

urlpatterns = [
    path("", views.site_dashboard, name="dashboard"),
    path("site/<int:pk>/", views.site_detail, name="site_detail"),
    path("site/<int:pk>/expand/", views.site_expand, name="site_expand"),
    path("site/<int:pk>/build/", views.site_build, name="site_build"),
    path("site/<int:pk>/convert-to-landing/", views.site_convert_to_landing, name="site_convert_to_landing"),
    path("site/<int:pk>/deploy/", views.site_deploy, name="site_deploy"),
    path("site/<int:pk>/theme/", views.site_theme_update, name="site_theme_update"),
    path("site/<int:pk>/backfill-heroes/", views.site_backfill_hero_images,
         name="site_backfill_hero_images"),
    path("site/<int:pk>/regenerate-heroes/", views.site_regenerate_hero_images,
         name="site_regenerate_hero_images"),
    path("sites/<int:pk>/audit/run/", views.site_audit_run, name="site_audit_run"),
    path("sites/<int:site_pk>/pages/<int:page_pk>/regenerate/", views.page_regenerate, name="page_regenerate"),
    path("download/", views.website_download_view, name="website_download"),
    path("site/<int:site_id>/plan-menu/", views.plan_menu, name="plan_menu"),
    path("site/<int:pk>/fill-content/", views.site_fill_content, name="site_fill_content"),
    path("site/<int:pk>/articles/", views.article_list, name="article_list"),
    path("site/<int:pk>/articles/new/", views.article_create, name="article_create"),
    path("site/<int:pk>/articles/<int:article_id>/edit/", views.article_edit, name="article_edit"),
    path("site/<int:pk>/articles/<int:article_id>/publish/", views.article_publish, name="article_publish"),
    path("site/<int:pk>/articles/<int:article_id>/archive/", views.article_archive, name="article_archive"),
    path("site/<int:pk>/articles/ai/", views.article_ai_studio, name="article_ai_studio"),
    path("site/<int:pk>/articles/ai/generate/", views.article_ai_generate, name="article_ai_generate"),
    path("site/<int:pk>/articles/ai/cluster/", views.article_ai_generate_cluster, name="article_ai_generate_cluster"),
    path("site/<int:pk>/articles/clusters/", views.article_clusters, name="article_clusters"),
    path("site/<int:pk>/articles/clusters/<int:cornerstone_id>/generate/", views.cluster_generate_supporting, name="cluster_generate_supporting"),
    path("site/<int:pk>/articles/clusters/<int:cornerstone_id>/publish-all/", views.cluster_publish_all, name="cluster_publish_all"),
]
