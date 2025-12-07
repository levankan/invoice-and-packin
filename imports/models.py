from django.db import models
from django.utils import timezone
from django_countries.fields import CountryField
from admin_area.models import Forwarder  
from decimal import Decimal

class ImportSequence(models.Model):
    """Keeps a single counter for generating sequential import codes."""
    counter = models.PositiveIntegerField(default=0)

    @classmethod
    def next_code(cls):
        seq, _ = cls.objects.get_or_create(id=1)
        seq.counter += 1
        seq.save()
        return f"IMP{seq.counter:06d}"  # IMP000001, IMP000002, ...


class Import(models.Model):
    import_code = models.CharField(max_length=20, unique=True, editable=False)
    vendor_name = models.CharField(max_length=255)
    exporter_country = CountryField(blank=True, null=True)
    incoterms = models.CharField(max_length=20, blank=True, null=True)
    currency_code = models.CharField(max_length=10, blank=True, null=True)
    goods_price = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    tracking_no = models.CharField(max_length=255, blank=True, null=True)
    shipping_method = models.CharField(max_length=20, blank=True, null=True)
    shipment_status = models.CharField(max_length=20, blank=True, null=True)
    pickup_address = models.TextField(blank=True, null=True)
    is_danger = models.BooleanField(default=False)
    is_stackable = models.BooleanField(default=True)
    expected_receipt_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    # --- TRANSPORTATION ---
    transport_invoice_no = models.CharField(max_length=100, blank=True, null=True)
    transport_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    transport_currency = models.CharField(max_length=10, blank=True, null=True)
    transport_payment_date = models.DateField(blank=True, null=True)

    # --- BROKERAGE ---
    brokerage_invoice_no = models.CharField(max_length=100, blank=True, null=True)
    brokerage_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    brokerage_currency = models.CharField(max_length=10, blank=True, null=True)
    brokerage_payment_date = models.DateField(blank=True, null=True)

    # --- INTERNAL DELIVERY ---
    internal_delivery_invoice_no = models.CharField(max_length=100, blank=True, null=True)
    internal_delivery_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    internal_delivery_currency = models.CharField(max_length=10, blank=True, null=True)
    internal_delivery_payment_date = models.DateField(blank=True, null=True)

    # --- OTHER CHARGES #1 ---
    other1_invoice_no = models.CharField(max_length=100, blank=True, null=True)
    other1_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    other1_currency = models.CharField(max_length=10, blank=True, null=True)
    other1_payment_date = models.DateField(blank=True, null=True)

    # --- OTHER CHARGES #2 ---
    other2_invoice_no = models.CharField(max_length=100, blank=True, null=True)
    other2_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    other2_currency = models.CharField(max_length=10, blank=True, null=True)
    other2_payment_date = models.DateField(blank=True, null=True)


    forwarder = models.ForeignKey(
    "admin_area.Forwarder",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="imports"
    )

    vendor_reference = models.CharField(max_length=100, blank=True, null=True)
    forwarder_reference = models.CharField(max_length=100, blank=True, null=True)

    # --- New customs declaration fields ---
    declaration_c_number = models.CharField(max_length=100, blank=True, null=True)
    declaration_a_number = models.CharField(max_length=100, blank=True, null=True)
    declaration_date = models.DateField(blank=True, null=True)

    total_gross_weight_kg = models.DecimalField(max_digits=14, decimal_places=3, blank=True, null=True)
    total_volumetric_weight_kg = models.DecimalField(max_digits=14, decimal_places=3, blank=True, null=True)



    created_at = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        if not self.import_code:
            self.import_code = ImportSequence.next_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.import_code







class ImportLine(models.Model):
    """
    Lines uploaded from Excel for an Import.
    Columns:
    Document No., Line No., No., Description, Quantity, Unit of Measure,
    Direct Unit Cost Excl. VAT, Line Amount Excl. VAT, Expected Receipt Date, Delivery Date
    """
    import_header = models.ForeignKey(
        Import,
        on_delete=models.CASCADE,
        related_name="lines",
    )

    document_no = models.CharField(max_length=100, blank=True, null=True)
    line_no = models.CharField(max_length=50, blank=True, null=True)
    item_no = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    quantity = models.DecimalField(max_digits=14, decimal_places=3, blank=True, null=True)
    unit_of_measure = models.CharField(max_length=50, blank=True, null=True)

    unit_cost = models.DecimalField(max_digits=14, decimal_places=4, blank=True, null=True)
    line_amount = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)

    expected_receipt_date = models.DateField(blank=True, null=True)
    delivery_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.import_header.import_code} / {self.document_no or ''} / {self.line_no or ''}"






from decimal import Decimal

# ... your existing imports/models above ...

class ImportPackage(models.Model):
    UNIT_SYSTEM_CHOICES = [
        ("metric", "Metric (cm/kg)"),
        ("imperial", "Imperial (in/lbs)"),
    ]

    PACKAGE_TYPE_CHOICES = [
        ("BOX", "Box"),
        ("PALLET", "Pallet"),
        ("SKID", "Skid"),
        ("ROLL", "Roll"),
        ("ENVELOPE", "Envelope"),
    ]

    import_header = models.ForeignKey(
        Import,
        on_delete=models.CASCADE,
        related_name="packages",
    )

    package_type = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=PACKAGE_TYPE_CHOICES,
    )

    # We will store everything in METRIC units in DB (cm / kg)
    length_cm = models.DecimalField(max_digits=14, decimal_places=3, blank=True, null=True)
    width_cm  = models.DecimalField(max_digits=14, decimal_places=3, blank=True, null=True)
    height_cm = models.DecimalField(max_digits=14, decimal_places=3, blank=True, null=True)
    gross_weight_kg = models.DecimalField(max_digits=14, decimal_places=3, blank=True, null=True)

    unit_system = models.CharField(
        max_length=10,
        choices=UNIT_SYSTEM_CHOICES,
        default="metric",
    )

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.import_header.import_code} – {self.package_type or 'Package'}"
