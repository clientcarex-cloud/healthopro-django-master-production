from django.db import models

from pro_laboratory.models.global_models import LabGlobalTests, LabGlobalPackages


class Company(models.Model):
    name = models.CharField(max_length=500)
    address = models.TextField(null=True, blank=True)
    po_number = models.CharField(max_length=50, null=True, blank=True)
    grn_number = models.CharField(max_length=50, null=True, blank=True)
    cin_number = models.CharField(max_length=50, null=True, blank=True)
    tin_number = models.CharField(max_length=50, null=True, blank=True)
    print_count = models.IntegerField(default=0)
    contact_person = models.CharField(max_length=1000, null=True, blank=True)
    mobile_number = models.CharField(max_length=15, null=True, blank=True)
    email = models.CharField(blank=True, null=True)
    gstin = models.CharField(max_length=100, null=True, blank=True)
    invoice_number = models.CharField(max_length=50, null=True, blank=True)
    pan_number = models.CharField(max_length=100, null=True, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name}'


class CompanyRevisedPrices(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    LabGlobalTestId = models.ForeignKey(LabGlobalTests, on_delete=models.PROTECT)
    LabGlobalPackageId = models.ForeignKey(LabGlobalPackages, on_delete=models.PROTECT, null=True, blank=True)
    revised_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class CompanyWorkPartnership(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='partners')
    name = models.CharField(max_length=100)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
