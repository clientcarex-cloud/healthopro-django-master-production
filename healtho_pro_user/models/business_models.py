from django.db import models

from healtho_pro_user.models.universal_models import HealthcareRegistryType, State, City, Country
from healtho_pro_user.models.users_models import HealthOProUser
from pro_universal_data.models import MessagingServiceTypes, ULabMenus
from super_admin.models import HealthOProSuperAdmin


class BContactFor(models.Model):  # Appointment, Emergency Care, Admin Contact
    reason = models.CharField(max_length=100)

    def __str__(self):
        return self.reason


class BContacts(models.Model):
    b_id = models.ForeignKey('BusinessProfiles', on_delete=models.PROTECT, blank=True, null=True)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone_number = models.CharField(max_length=10)
    contact_for = models.ForeignKey(BContactFor, on_delete=models.PROTECT)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Check if this contact is set as primary and is_active
        if self.is_primary and self.is_active:
            # Set all other contacts with the same contact_for as not primary
            BContacts.objects.filter(
                b_id=self.b_id,
                contact_for=self.contact_for,
                is_primary=True,
                is_active=True
            ).exclude(pk=self.pk).update(is_primary=False)

        super().save(*args, **kwargs)


class BusinessType(models.Model):  # labs, hospitals
    type_name = models.CharField(max_length=100)

    def __str__(self):
        return self.type_name


class BusinessProfiles(models.Model):
    id = models.AutoField(primary_key=True)
    pro_user_id = models.ForeignKey(HealthOProUser, on_delete=models.PROTECT, null=True)
    organization_name = models.CharField(max_length=500, blank=True, unique=True)
    phone_number = models.CharField(max_length=15, unique=True)
    provider_type = models.ForeignKey(HealthcareRegistryType, on_delete=models.PROTECT)
    country = models.ForeignKey(Country, on_delete=models.PROTECT, blank=True, null=True)
    city = models.ForeignKey(City, on_delete=models.PROTECT, blank=True, null=True)
    pin_code = models.CharField(max_length=20, blank=True, null=True)
    state = models.ForeignKey(State, on_delete=models.PROTECT, blank=True, null=True)
    address = models.CharField(max_length=2000, blank=True, null=True)
    address2 = models.CharField(max_length=2000, blank=True, null=True)
    geo_location = models.CharField(max_length=100, blank=True, null=True)
    latitude = models.CharField(max_length=100, blank=True, null=True)
    longitude = models.CharField(max_length=100, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    referral_amount_per_patient = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    b_logo = models.TextField(blank=True, null=True)
    b_letterhead = models.TextField(blank=True, null=True)
    blue_verification = models.BooleanField(default=False)
    is_open_outsource = models.BooleanField(default=False)
    is_head_branch = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_onboarded = models.BooleanField(default=False, blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    is_account_disabled = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.organization_name}'



class DeletedBusinessProfiles(models.Model):
    deleted_id = models.IntegerField()
    deleted_client_id=models.IntegerField(null=True, blank=True)
    organization_name = models.CharField(max_length=500, blank=True)
    phone_number = models.CharField(max_length=15)
    provider_type = models.ForeignKey(HealthcareRegistryType, on_delete=models.PROTECT)
    country = models.ForeignKey(Country, on_delete=models.PROTECT, blank=True, null=True)
    city = models.ForeignKey(City, on_delete=models.PROTECT, blank=True, null=True)
    pin_code = models.CharField(max_length=20, blank=True, null=True)
    state = models.ForeignKey(State, on_delete=models.PROTECT, blank=True, null=True)
    address = models.CharField(max_length=2000, blank=True, null=True)
    latitude = models.CharField(max_length=100, blank=True, null=True)
    longitude = models.CharField(max_length=100, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    b_logo = models.TextField(blank=True, null=True)
    business_added_on = models.DateTimeField()
    business_deleted_on = models.DateTimeField(auto_now_add=True)
    deleted_by=models.ForeignKey(HealthOProSuperAdmin, on_delete=models.PROTECT)

    def __str__(self):
        return f'{self.organization_name}'


class BusinessAddresses(models.Model):
    b_id = models.ForeignKey(BusinessProfiles, on_delete=models.PROTECT,blank=True, null=True)
    address = models.CharField(max_length=2000)
    clinic_reg_no = models.CharField(max_length=100, blank=True, null=True)
    is_head_branch = models.BooleanField(default=False)
    branch_name=models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)





class BusinessProfilesImages(models.Model):
    b_id = models.ForeignKey(BusinessProfiles, related_name='images', on_delete=models.PROTECT, blank=True, null=True)
    logo = models.TextField(blank=True)
    letterhead = models.TextField(blank=True)
    header = models.TextField(blank=True)
    footer = models.TextField(blank=True)

    def __str__(self):
        return f"{self.b_id}"


class BusinessWorkingDays(models.Model):
    # b_id = models.ForeignKey(BusinessProfiles, on_delete=models.PROTECT, null=True, blank=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}"


class BusinessTimings(models.Model):
    b_id = models.ForeignKey(BusinessProfiles, on_delete=models.PROTECT,blank=True, null=True, related_name='business_timings')
    day = models.ForeignKey(BusinessWorkingDays, on_delete=models.PROTECT)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"Open {self.day} {self.start_time.strftime('%I:%M %p')} to {self.end_time.strftime('%I:%M %p')}"


class BExecutive(models.Model):
    b_id = models.ForeignKey(BusinessProfiles, on_delete=models.PROTECT, blank=True, null=True)
    name = models.CharField(max_length=255)
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class BHealthcareService(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class GlobalMessagingSettings(models.Model):
    type = models.ForeignKey(MessagingServiceTypes, on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    remarks = models.CharField(max_length=1000, blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    last_updated_by = models.ForeignKey(HealthOProUser, on_delete=models.PROTECT, blank=True, null=True)


class GlobalBusinessSettings(models.Model):
    business = models.ForeignKey(BusinessProfiles, on_delete=models.PROTECT, blank=True, null=True)
    is_sms_active = models.BooleanField(default=True)
    is_whatsapp_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    last_updated_by = models.ForeignKey(HealthOProUser, on_delete=models.PROTECT, blank=True, null=True)


class BusinessModules(models.Model):
    business = models.OneToOneField(BusinessProfiles, on_delete=models.PROTECT, blank=True, null=True)
    modules = models.ManyToManyField(ULabMenus, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    last_updated_by = models.ForeignKey(HealthOProUser, on_delete=models.PROTECT,blank=True, null=True)
