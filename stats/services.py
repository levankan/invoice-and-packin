from django.db.models import Q
from imports.models import Import


def _apply_date_range(qs, date_from=None, date_to=None):
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    return qs


def _shipping_method_filter(method_name):
    method_name = (method_name or "").lower().strip()

    if method_name == "air":
        return (
            Q(shipping_method__icontains="air")
        )

    if method_name == "sea":
        return (
            Q(shipping_method__icontains="sea") |
            Q(shipping_method__icontains="ocean") |
            Q(shipping_method__icontains="vessel")
        )

    if method_name == "road":
        return (
            Q(shipping_method__icontains="road") |
            Q(shipping_method__icontains="truck") |
            Q(shipping_method__icontains="land")
        )

    if method_name == "courier":
        return (
            Q(shipping_method__icontains="fedex") |
            Q(shipping_method__icontains="dhl") |
            Q(shipping_method__icontains="ups") |
            Q(shipping_method__icontains="tnt") |
            Q(shipping_method__icontains="courier")
        )

    if method_name == "other":
        return ~(
            _shipping_method_filter("air") |
            _shipping_method_filter("sea") |
            _shipping_method_filter("road") |
            _shipping_method_filter("courier")
        )

    return Q()


def _status_filter(status_name):
    """
    Flexible matching because statuses in DB may vary.
    Adjust later if your exact status values are different.
    """
    status_name = (status_name or "").lower().strip()

    if status_name == "planned":
        return (
            Q(shipment_status__iexact="planned") |
            Q(shipment_status__icontains="plan")
        )

    if status_name == "in_transit":
        return (
            Q(shipment_status__iexact="in transit") |
            Q(shipment_status__iexact="in_transit") |
            Q(shipment_status__icontains="transit")
        )

    if status_name == "at_customs":
        return (
            Q(shipment_status__iexact="at customs") |
            Q(shipment_status__iexact="at_customs") |
            Q(shipment_status__icontains="customs")
        )

    if status_name == "delivered":
        return (
            Q(shipment_status__iexact="delivered") |
            Q(shipment_status__icontains="deliver")
        )

    return Q()


def _count_shipments(base_qs, status=None, shipping_method=None):
    qs = base_qs

    if status:
        qs = qs.filter(_status_filter(status))

    if shipping_method:
        qs = qs.filter(_shipping_method_filter(shipping_method))

    return qs.count()


def get_import_statistics(date_from=None, date_to=None):
    base_qs = Import.objects.all()
    base_qs = _apply_date_range(base_qs, date_from, date_to)

    methods = ["air", "sea", "road", "courier", "other"]

    def method_counts(status=None):
        data = {"all": _count_shipments(base_qs, status=status)}

        for m in methods:
            data[m] = _count_shipments(base_qs, status=status, shipping_method=m)

        return data

    stats = {
        "total_registered": method_counts(),
        "planned": method_counts("planned"),
        "in_transit": method_counts("in_transit"),
        "at_customs": method_counts("at_customs"),
        "delivered": method_counts("delivered"),
    }

    return stats