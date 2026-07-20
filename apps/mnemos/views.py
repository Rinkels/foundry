# apps/files/views.py
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from platform_apps.apps.common.mixins import TenantAwareViewMixin  # 👈 this one
from .models import FileAsset, FileAttachment

@login_required
def upload_and_attach(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    f = request.FILES.get("file")
    if not f:
        return HttpResponseBadRequest("No file")

    app_label = request.POST.get("app_label")
    model = request.POST.get("model")
    object_id = request.POST.get("object_id")
    label = request.POST.get("label", "")

    if not (app_label and model and object_id):
        return HttpResponseBadRequest("Missing target")

    ct = get_object_or_404(ContentType, app_label=app_label, model=model)
    asset = FileAsset.objects.create(
        file=f,
        original_name=f.name,
        size_bytes=f.size,
        uploaded_by=request.user,
    )
    FileAttachment.objects.create(
        file_asset=asset,
        content_type=ct,
        object_id=int(object_id),
        label=label,
    )

    return redirect(request.POST.get("next") or "/")

class FileAssetListView(LoginRequiredMixin, PermissionRequiredMixin, TenantAwareViewMixin, ListView):
    model = FileAsset
    template_name = "mnemos/file_list.html"
    context_object_name = "files"
    paginate_by = 50
    permission_required = "mnemos.view_fileasset"  # or your custom perm

    def get_queryset(self):
        qs = super().get_queryset().select_related("uploaded_by").order_by("-created_at")

        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(original_name__icontains=q) |
                Q(mime_type__icontains=q) |
                Q(uploaded_by__username__icontains=q)
            )
        return qs
