from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import (
    Sum, Count, F, ExpressionWrapper, Value, DecimalField, IntegerField
)
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, render

from core.models import Export, LineItem


@login_required
def invoice_view(request, export_id):
    export = get_object_or_404(Export, id=export_id)

    # Group LineItems like a pivot table
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
            total_qty=Coalesce(Sum("qty"), Value(0), output_field=IntegerField()),
            row_count=Count("id"),
            total_value=ExpressionWrapper(
                Coalesce(F("price"), Value(Decimal("0.00"))) * F("total_qty"),
                output_field=DecimalField(max_digits=18, decimal_places=2),
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

    # Grand totals (DB-side)
    totals = LineItem.objects.filter(export=export).aggregate(
        grand_total_qty=Coalesce(Sum("qty"), Value(0), output_field=IntegerField()),
        grand_total_value=Coalesce(
            Sum(
                ExpressionWrapper(
                    Coalesce(F("price"), Value(Decimal("0.00")))
                    * Coalesce(F("qty"), Value(0), output_field=IntegerField()),
                    output_field=DecimalField(max_digits=18, decimal_places=2),
                )
            ),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
        grand_total_count=Count("id"),
    )

    return render(
        request,
        "core/invoice.html",
        {
            "export": export,
            "grouped_items": grouped_items,
            "grand_total_qty": totals["grand_total_qty"],
            "grand_total_value": totals["grand_total_value"],
            "grand_total_count": totals["grand_total_count"],
        },
    )
