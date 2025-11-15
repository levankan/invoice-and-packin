from django.db import models
from django.utils import timezone
from django_countries.fields import CountryField
from admin_area.models import Forwarder  

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

    forwarder = models.ForeignKey(
    "admin_area.Forwarder",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="imports"
    )


    # --- New customs declaration fields ---
    declaration_c_number = models.CharField(max_length=100, blank=True, null=True)
    declaration_a_number = models.CharField(max_length=100, blank=True, null=True)
    declaration_date = models.DateField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        if not self.import_code:
            self.import_code = ImportSequence.next_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.import_code
