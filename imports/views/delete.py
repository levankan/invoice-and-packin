from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from ..models import Import



@login_required
def delete_import_confirm(request, pk):
    if not request.user.is_superuser:
        raise PermissionDenied

    imp = get_object_or_404(Import, pk=pk)

    if request.method == "POST":
        imp.delete()
        messages.success(request, f"Import {imp.import_code} deleted.")
        return redirect("imports_home")

    return render(
        request,
        "imports/partials/delete_confirm.html",
        {"imp": imp},
    )
