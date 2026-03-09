# admin_area/models.py
from django.db import models

class Item(models.Model):
    number = models.CharField(max_length=64, unique=True, db_index=True)
    description = models.CharField(max_length=255, blank=True)
    parent_item_category = models.CharField(max_length=128, blank=True)
    base_unit_of_measure = models.CharField(max_length=32, blank=True)
    item_category_code = models.CharField(max_length=64, blank=True)
    type = models.CharField(max_length=64, blank=True)
    length = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    width = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    height = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    weight = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    volumetric_weight = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    material = models.CharField(max_length=128, blank=True)
    hs_code = models.CharField(max_length=32, blank=True)
    additional_measurement = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.number} — {self.description[:40]}"

class Vendor(models.Model):
    number = models.CharField(max_length=50, unique=True, db_index=True)  # "No."
    name = models.CharField(max_length=255)
    vat_registration_no = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.number} — {self.name}"




class Forwarder(models.Model):
    # Short “system” name – e.g. “DSV”, “Schenker Germany”
    name = models.CharField(max_length=255, unique=True, db_index=True)

    # Full legal company name
    legal_name = models.CharField(max_length=255, blank=True)

    vat_registration_no = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        # show both if available
        if self.legal_name:
            return f"{self.name} — {self.legal_name}"
        return self.name




from django.db import models


class DeliveryEmailConfiguration(models.Model):

    description = models.CharField(
        max_length=255,
        help_text="Internal name for this email configuration"
    )

    email_subject = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Email subject line"
    )

    email_to = models.TextField(
        help_text="Enter email addresses separated by commas"
    )

    cc = models.TextField(
        blank=True,
        null=True,
        help_text="Optional CC emails separated by commas"
    )

    bcc = models.TextField(
        blank=True,
        null=True,
        help_text="Optional BCC emails separated by commas"
    )

    email_text = models.TextField(
        help_text="Email message template"
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Turn ON/OFF email sending"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Delivery Email Configuration"
        verbose_name_plural = "Delivery Email Configurations"
        ordering = ["-created_at"]

    def __str__(self):
        return self.description