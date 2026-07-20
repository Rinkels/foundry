from django.urls import path
from .views import upload_and_attach, FileAssetListView

app_name = "mnemos"

urlpatterns = [
    path("upload-and-attach/", upload_and_attach, name="upload_attach"),
    path("files/", FileAssetListView.as_view(), name="file-list"),
]
