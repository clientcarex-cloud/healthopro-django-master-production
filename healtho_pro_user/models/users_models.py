import datetime
import random

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models.signals import post_save
from django.utils import timezone
from django.core.validators import RegexValidator
from django.utils.text import slugify
from django.utils.translation import gettext
from rest_framework.response import Response
from healtho_pro_user.models.universal_models import UserType, State, City, Country, HealthcareRegistryType
from django_tenants.models import TenantMixin, DomainMixin


class Client(TenantMixin):
    name = models.CharField(max_length=100, unique=True)
    created_on = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, blank=True, null=True)

    # default true, schema will be automatically created and synced when it is saved
    auto_create_schema = True


class Domain(DomainMixin):
    url = models.CharField(max_length=253,default='https://healtho.pro/', blank=True, null=True)


class HealthOProUserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            return Response({"Error": "The Phone Number must be set"})

        user = self.model(phone_number=phone_number, **extra_fields)
        user.username = extra_fields.get('username', None)  # Ensure username is None if not provided
        user.set_password(password)
        user.save(using=self._db)
        return user

    # ... rest of the manager ...

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            return Response({"Error": "Superuser must have is_staff=True!"})

        if extra_fields.get('is_superuser') is not True:
            return Response({"Error": "Superuser must have is_superuser=True!"})

        return self.create_user(phone_number, password, **extra_fields)


class HealthOProUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=20, unique=True, blank=True, null=True)
    session_id = models.CharField(max_length=256, null=True, blank=True)
    phone_number = models.CharField(
        max_length=10,
        unique=True,
        validators=[
            RegexValidator(
                regex='^[0-9]*$',
                message='Phone number must be numeric',
                code='invalid_phone_number'
            ),
        ]
    )

    user_type = models.ForeignKey(UserType, on_delete=models.PROTECT, null=True)
    HealthcareRegistryType = models.ForeignKey(HealthcareRegistryType, on_delete=models.PROTECT, null=True)
    country = models.ForeignKey(Country, on_delete=models.PROTECT, blank=True, null=True)
    city = models.ForeignKey(City, on_delete=models.PROTECT, blank=True, null=True)
    state = models.ForeignKey(State, on_delete=models.PROTECT, blank=True, null=True)
    full_name = models.CharField(max_length=200, null=True)
    latitude = models.CharField(max_length=100, blank=True, null=True)
    longitude = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(null=True, blank=True, unique=True, )
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(default=timezone.now)
    last_updated = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(gettext('last login'), blank=True, null=True)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []

    objects = HealthOProUserManager()

    def __str__(self):
        return f"{self.full_name}" if self.full_name else f"User {self.id}"


class UserTenant(models.Model):
    user = models.ForeignKey(HealthOProUser, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    is_superadmin = models.BooleanField(default=False, blank=True)
    is_active = models.BooleanField(default=False, blank=True)


class HealthOProMessagingUser(models.Model):
    dp = models.TextField(null=True, blank=True)
    pro_user = models.ForeignKey(HealthOProUser, on_delete=models.PROTECT, null=True, blank=True, related_name='users')
    username = models.CharField(max_length=75, unique=True)
    display_name = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True, null=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, null=True, blank=True, related_name='client')

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        if not self.display_name:
            self.display_name = self.pro_user.full_name
        if (not self.username) or (not self.username.endswith('@healthO')):
            cleaned_username = slugify(self.pro_user.full_name)[:50]
            self.username = f"{cleaned_username}@healthO"
            while True:
                random_code = random.randint(100000, 999999)
                unique_username = f"{cleaned_username}_{random_code}@healthO"
                if not HealthOProMessagingUser.objects.filter(username=unique_username).exists():
                    break

            self.username = unique_username
        super().save(*args, **kwargs)

    class Meta:
        ordering = ('-timestamp',)


class UserSession(models.Model):
    pro_user = models.ForeignKey(HealthOProUser,
                                 on_delete=models.CASCADE)  # Ensure this matches your model and field names
    session_id = models.CharField(max_length=32)


class OTP(models.Model):
    pro_user_id = models.ForeignKey(HealthOProUser, on_delete=models.CASCADE)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.IntegerField(default=0)
    password_attempts = models.IntegerField(default=0)
    last_sent_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        expiration_time = datetime.timedelta(minutes=5)
        return timezone.now() - self.last_sent_at > expiration_time

    def increment_attempts(self):
        self.attempts += 1
        self.save()

    def increment_password_attempts(self):
        self.password_attempts += 1
        self.save()

    def can_resend(self):
        cooldown_time = datetime.timedelta(minutes=1)  # Cooldown period of 1 minutes
        return timezone.now() - self.last_sent_at > cooldown_time

    def reset_otp(self, new_otp):
        self.otp_code = new_otp
        self.attempts = 0
        self.password_attempts = 0
        self.last_sent_at = timezone.now()
        self.save()


class ULoginSliders(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='slider_images/')
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
