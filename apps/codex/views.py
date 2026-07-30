from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import ListView

try:
    import markdown as _md
except Exception:  # pragma: no cover
    _md = None

from .models import MarkdownDoc
from .scanner import scan


class DocListView(LoginRequiredMixin, ListView):
    model = MarkdownDoc
    template_name = "codex/doc_list.html"
    context_object_name = "docs"
    paginate_by = 60

    def get_queryset(self):
        qs = MarkdownDoc.objects.all()
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q) | Q(rel_path__icontains=q)
                | Q(excerpt__icontains=q) | Q(project__icontains=q)
            )
        proj = (self.request.GET.get("project") or "").strip()
        if proj:
            qs = qs.filter(project=proj)
        flt = self.request.GET.get("filter")
        if flt == "unread":
            qs = qs.filter(read=False)
        elif flt == "pinned":
            qs = qs.filter(pinned=True)
        return qs

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        c["q"] = self.request.GET.get("q", "")
        c["filter"] = self.request.GET.get("filter", "")
        c["active_project"] = self.request.GET.get("project", "")
        c["projects"] = (MarkdownDoc.objects.values("project")
                         .annotate(n=Count("id")).order_by("-n", "project"))
        c["total"] = MarkdownDoc.objects.count()
        c["unread"] = MarkdownDoc.objects.filter(read=False).count()
        return c


@login_required
def doc_detail(request, pk):
    doc = get_object_or_404(MarkdownDoc, pk=pk)
    p = Path(doc.path)
    if not p.exists():
        messages.error(request, "That file no longer exists on disk — run a rescan to prune it.")
        return redirect("codex:list")
    text = p.read_text(encoding="utf-8", errors="ignore")
    if _md is not None:
        html = _md.markdown(text, extensions=["extra", "tables", "toc", "fenced_code", "sane_lists"])
    else:
        html = "<pre>" + text.replace("<", "&lt;") + "</pre>"
    if not doc.read:
        doc.read = True
        doc.save(update_fields=["read"])
    return render(request, "codex/doc_detail.html", {"doc": doc, "html": html})


@login_required
@require_POST
def rescan(request):
    s = scan()
    messages.success(
        request,
        f"Codex scan complete — {s['total']} docs "
        f"({s['added']} new, {s['updated']} updated, {s['pruned']} pruned).",
    )
    return redirect("codex:list")


@login_required
@require_POST
def toggle(request, pk):
    doc = get_object_or_404(MarkdownDoc, pk=pk)
    field = request.POST.get("field")
    if field in ("read", "pinned"):
        setattr(doc, field, not getattr(doc, field))
        doc.save(update_fields=[field])
    return redirect(request.META.get("HTTP_REFERER") or "codex:list")
