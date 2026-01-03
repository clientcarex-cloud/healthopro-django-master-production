from django.db import models

from pro_laboratory.models.global_models import LabStaff
from pro_universal_data.models import UniversalFuelTypes, UniversalVehicleTypes, MarketingVisitTypes, \
    MarketingVisitStatus, MarketingTargetTypes, MarketingTargetDurations


class LabStaffVehicleDetails(models.Model):
    labstaff = models.ForeignKey(LabStaff, null=True, blank=True, on_delete=models.PROTECT)
    vehicle_type = models.ForeignKey(UniversalVehicleTypes, on_delete=models.PROTECT, blank=True, null=True)
    fuel_type = models.ForeignKey(UniversalFuelTypes, on_delete=models.PROTECT, blank=True, null=True)
    fuel_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    vehicle_reg_no = models.CharField(max_length=50, null=True, blank=True)
    driving_license_no = models.CharField(max_length=50, null=True, blank=True)
    variable_mileage = models.CharField(max_length=50, null=True, blank=True)
    vehicle_reg_img = models.TextField(null=True, blank=True)
    driving_license_img = models.TextField(null=True, blank=True)


class MarketingExecutiveVisits(models.Model):
    lab_staff = models.ForeignKey(LabStaff, null=True, blank=True, on_delete=models.PROTECT)
    date = models.DateField(blank=True, null=True)
    visit_type = models.ForeignKey(MarketingVisitTypes, null=True, blank=True, on_delete=models.PROTECT)
    name = models.CharField(max_length=300, blank=True, null=True)
    mobile_number = models.CharField(max_length=15, null=True, blank=True)
    address = models.CharField(max_length=1000, blank=True, null=True)

    start_time = models.DateTimeField(blank=True, null=True)
    latitude_at_start = models.CharField(max_length=50, blank=True, null=True)
    longitude_at_start = models.CharField(max_length=50, blank=True, null=True)
    address_at_start = models.CharField(max_length=500, blank=True, null=True)

    end_time = models.DateTimeField(blank=True, null=True)
    latitude_at_end = models.CharField(max_length=50, blank=True, null=True)
    longitude_at_end = models.CharField(max_length=50, blank=True, null=True)
    address_at_end = models.CharField(max_length=500, blank=True, null=True)

    visit_img = models.TextField(blank=True, null=True)
    remarks = models.CharField(max_length=1000, blank=True, null=True)
    total_time_taken = models.DurationField(null=True, blank=True)
    total_distance_travelled = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, null=True)
    status = models.ForeignKey(MarketingVisitStatus, null=True, blank=True, on_delete=models.PROTECT)
    created_by = models.ForeignKey(LabStaff, null=True, blank=True, on_delete=models.PROTECT,
                                   related_name='visit_created_by')
    last_updated_by = models.ForeignKey(LabStaff, null=True, blank=True, on_delete=models.PROTECT,
                                        related_name='visit_updated_by')
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.start_time and self.end_time:
            self.total_time_taken = self.end_time - self.start_time
        super().save(*args, **kwargs)


class MarketingExecutiveLocationTracker(models.Model):
    lab_staff = models.OneToOneField(LabStaff, null=True, blank=True, on_delete=models.PROTECT)
    last_seen_on = models.DateTimeField(auto_now=True)
    latitude_at_last_seen = models.CharField(max_length=50, blank=True, null=True)
    longitude_at_last_seen = models.CharField(max_length=50, blank=True, null=True)
    address_at_last_seen = models.CharField(max_length=500, blank=True, null=True)


class MarketingExecutiveTargets(models.Model):
    labstaff = models.ForeignKey(LabStaff, on_delete=models.PROTECT, null=True, blank=True)
    assigned_areas = models.CharField(max_length=1000, null=True, blank=True)
    target_type = models.ForeignKey(MarketingTargetTypes, on_delete=models.PROTECT, null=True, blank=True)
    target_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    no_of_referrals = models.IntegerField(null=True, blank=True)
    target_duration = models.ForeignKey(MarketingTargetDurations, on_delete=models.PROTECT, null=True, blank=True)
    from_date = models.DateField(null=True, blank=True)
    to_date = models.DateField(null=True, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
