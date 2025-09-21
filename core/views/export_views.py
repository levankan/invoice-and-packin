from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from core.models import Export
from core.forms import ExportForm


@login_required
def exports_view(request):
    """List and search exports"""
    q = request.GET.get("q", "")
    exports = Export.objects.all().order_by("-created_at")
    if q:
        exports = exports.filter(
            Q(invoice_number__icontains=q) |
            Q(project_no__icontains=q) |
            Q(export_number__icontains=q)
        )
    return render(request, "core/exports.html", {"exports": exports})


@login_required
def edit_export(request, export_id):
    """Edit a single export"""
    export = get_object_or_404(Export, id=export_id)
    if request.method == "POST":
        form = ExportForm(request.POST, instance=export)
        if form.is_valid():
            form.save()
            messages.success(request, "Export updated successfully ✅")
            return redirect("exports_view")
    else:
        form = ExportForm(instance=export)
    return render(request, "core/edit_export.html", {"form": form, "export": export})


@login_required
def delete_export(request, export_id):
    export = get_object_or_404(Export, id=export_id)
    export.delete()
    messages.success(request, "Export deleted successfully 🗑")
    return redirect("exports_view")

