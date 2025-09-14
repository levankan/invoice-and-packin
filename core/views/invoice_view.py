from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F, FloatField, ExpressionWrapper
from core.models import Export, LineItem

@login_required
def invoice_view(request, export_id):
    export = get_object_or_404(Export, id=export_id)

    # Group LineItems like pivot
    grouped_items = (
        LineItem.objects.filter(export=export)
        .values(
            "pallet_number",
            "box_number",
            "customer_po",
            "po_line",
            "cross_reference",
            "description",
            "price",
        )
        .annotate(
            total_qty=Sum("qty"),
            count_cross_ref=Count("id"),
            total_value=ExpressionWrapper(
                F("price") * Sum("qty"), output_field=FloatField()
            ),
        )
        .order_by(
            "pallet_number",
            "box_number",
            "customer_po",
            "po_line",
            "cross_reference",
            "price",
        )
    )

    # Grand totals
    grand_total_qty = sum(item["total_qty"] for item in grouped_items)
    grand_total_value = sum(item["total_value"] for item in grouped_items)
    grand_total_count = sum(item["count_cross_ref"] for item in grouped_items)

    return render(
        request,
        "core/invoice.html",
        {
            "export": export,
            "grouped_items": grouped_items,
            "grand_total_qty": grand_total_qty,
            "grand_total_value": grand_total_value,
            "grand_total_count": grand_total_count,
        },
    )
