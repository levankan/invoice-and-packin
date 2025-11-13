# imports/forms.py
from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget

class ExporterCountryForm(forms.Form):
    exporter_country = CountryField(blank=True).formfield(
        widget=CountrySelectWidget(attrs={"class": "form-select"})
    )
