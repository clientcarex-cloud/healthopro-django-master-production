import datetime
from django.db import models, transaction
from django.utils import timezone

from healtho_pro_user.models.business_models import BusinessAddresses
from healtho_pro_user.models.users_models import Client
from pro_laboratory.models.b2b_models import Company, CompanyWorkPartnership
from pro_laboratory.models.doctors_models import LabDoctors
from pro_laboratory.models.global_models import LabGlobalTests, LabDiscountType, LabStaff, LabDepartments, \
    LabGlobalPackages

from pro_laboratory.models.sourcing_lab_models import SourcingLabRegistration

from pro_universal_data.models import ULabPaymentModeType, ULabTestStatus, ULabPatientAge, \
    ULabPatientAttenderTitles, ULabPatientTitles, ULabPatientGender, PaymentFor, PatientType


class Patient(models.Model):
    title = models.ForeignKey(ULabPatientTitles, on_delete=models.PROTECT, null=True)
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    dob = models.DateField(null=True, blank=True)
    ULabPatientAge = models.ForeignKey(ULabPatientAge, on_delete=models.PROTECT, null=True)
    gender = models.ForeignKey(ULabPatientGender, on_delete=models.PROTECT, null=True)
    referral_doctor = models.ForeignKey(LabDoctors, on_delete=models.PROTECT, null=True, blank=True,
                                        related_name='patient')
    attender_name = models.CharField(max_length=100, blank=True, null=True)
    attender_relationship_title = models.ForeignKey(ULabPatientAttenderTitles, on_delete=models.PROTECT, null=True,
                                                    blank=True)
    mobile_number = models.CharField(max_length=15)
    email = models.EmailField(null=True, blank=True)
    area = models.CharField(max_length=200, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    prescription_attach = models.TextField(null=True, blank=True)
    department = models.ForeignKey(LabDepartments, on_delete=models.PROTECT, null=True)
    mr_no = models.CharField(max_length=50, null=True)
    visit_id = models.CharField(max_length=50, unique=True,null=True)
    created_by = models.ForeignKey(LabStaff, on_delete=models.CASCADE, null=True,)
    last_updated_by = models.ForeignKey(LabStaff, related_name='patient_last_updated_by', on_delete=models.PROTECT,
                                        null=True, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)
    visit_count = models.IntegerField(null=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, blank=True, null=True)
    is_sourcing_lab=models.BooleanField(default=False)
    referral_lab=models.ForeignKey(SourcingLabRegistration, on_delete=models.PROTECT,blank=True, null=True)
    privilege_membership=models.ForeignKey('pro_laboratory.PrivilegeCardMemberships',on_delete=models.PROTECT, blank=True, null=True)
    partner = models.ForeignKey(CompanyWorkPartnership, on_delete=models.PROTECT, null=True, blank=True)
    branch = models.ForeignKey(BusinessAddresses, on_delete=models.PROTECT, blank=True, null=True)
    patient_type = models.ForeignKey(PatientType, on_delete=models.PROTECT, blank=True, null=True)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f'{self.id},{self.visit_id},{self.title}, {self.name},  {self.created_by}'

    def save(self, *args, **kwargs):
        if not self.visit_id:
            patient_added_on = self.added_on or timezone.now()

            current_date = patient_added_on.strftime('%y%m%d')
            today = patient_added_on.date()

            existing_patients = Patient.objects.filter(name=self.name, mobile_number=self.mobile_number).first()

            patients = Patient.objects.filter(added_on__date__gte=today,
                                              added_on__date__lt=today + timezone.timedelta(days=1))
            patients_count = patients.count() + 1

            if existing_patients:
                self.mr_no = existing_patients.mr_no
                self.visit_id = f'{current_date}-{patients_count}'
            else:
                self.mr_no = f'{current_date}-{patients_count}'
                self.visit_id = f'{current_date}-{patients_count}'

        super().save(*args, **kwargs)





class HomeService(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE)
    is_required = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)



class LabPatientInvoice(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE)
    invoice_id = models.CharField(max_length=500, null=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    total_lab_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, null=True)
    total_ref_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, null=True)
    total_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    discountType = models.ForeignKey(LabDiscountType, on_delete=models.PROTECT, null=True)
    total_due = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    invoice_upload = models.ImageField(upload_to='payment_invoice/')
    total_refund = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.invoice_id} - {self.patient.name}"

    def save(self, *args, **kwargs):
        if not self.invoice_id:
            with transaction.atomic():
                date = timezone.now().date().strftime('%y%m%d')
                today_invoice_count = LabPatientInvoice.objects.filter(added_on__date=timezone.now().date()).count() + 1
                self.invoice_id = f"INV{date}{today_invoice_count:04d}"
        super().save(*args, **kwargs)



class LabPatientPayments(models.Model):
    pay_mode = models.ForeignKey(ULabPaymentModeType, on_delete=models.PROTECT)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)


class LabPatientReceipts(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, null=True)
    invoiceid = models.ForeignKey(LabPatientInvoice, on_delete=models.PROTECT, null=True, blank=True)
    Receipt_id = models.CharField(max_length=500, null=True, blank=True)
    remarks = models.CharField(max_length=500, blank=True, null=True)
    discount_type = models.ForeignKey(LabDiscountType, on_delete=models.PROTECT, blank=True, null=True)
    discount_amt = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    is_discount_amt_by_ref_doc = models.BooleanField(default=False)
    payments = models.ManyToManyField(LabPatientPayments, blank=True)
    receipt_upload = models.FileField(upload_to='payment_receipts/', blank=True, null=True)
    is_refund = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(LabStaff, on_delete=models.CASCADE, null=True)
    payment_for = models.ForeignKey(PaymentFor, models.PROTECT,blank=True, null=True)
    tests = models.ManyToManyField('LabPatientTests', blank=True)
    packages = models.ManyToManyField('LabPatientPackages', blank=True)
    consultations = models.ManyToManyField('pro_hospital.PatientDoctorConsultationDetails', blank=True)
    services = models.ManyToManyField('pro_hospital.PatientServices', blank=True)
    rooms = models.ManyToManyField('pro_hospital.IPRoomBooking', blank=True)
    medicines = models.ManyToManyField('pro_pharmacy.PatientMedicine', blank=True)
    before_payment_due = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    after_payment_due = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)

    def __str__(self):
        return f"Receipt({self.Receipt_id}) for {self.invoiceid}"

    def save(self, *args, **kwargs):
        date = timezone.now().date()
        receipts = LabPatientReceipts.objects.filter(added_on__date=date)
        receipt_number = receipts.count() + 1
        date = date.strftime('%y%m%d')
        receipt_id = f"RC{date}{receipt_number:04d}"
        self.Receipt_id = receipt_id
        super().save(*args, **kwargs)


class LabPatientTests(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT)
    LabGlobalTestId = models.ForeignKey(LabGlobalTests, on_delete=models.PROTECT, null=True)
    name = models.CharField(max_length=250, null=True)
    display_name = models.CharField(max_length=250, blank=True, null=True)
    short_code = models.CharField(max_length=250, null=True, blank=True)
    status_id = models.ForeignKey(ULabTestStatus, on_delete=models.PROTECT, null=True, blank=True)
    department = models.ForeignKey(LabDepartments, on_delete=models.PROTECT, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_after_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_authorization = models.BooleanField(default=False)
    is_package_test = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(null=True, blank=True)
    is_outsourcing = models.BooleanField(default=False, null=True, blank=True)
    sourcing_lab = models.ForeignKey(SourcingLabRegistration, on_delete=models.PROTECT, blank=True, null=True)
    branch = models.ForeignKey(BusinessAddresses, on_delete=models.PROTECT, blank=True, null=True)

    def __str__(self):
        return f"{self.id}. {self.name}"

    def save(self, *args, **kwargs):
        self.price_after_discount = self.price - self.discount
        super().save(*args, **kwargs)


class LabPatientPackages(models.Model):  #api
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, null=True)
    LabGlobalPackageId = models.ForeignKey(LabGlobalPackages, on_delete=models.PROTECT, null=True)
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=500, blank=True, null=True)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_discount = models.DecimalField(max_digits=10, decimal_places=2)
    is_disc_percentage = models.BooleanField(default=False)
    package_image = models.ImageField(upload_to='package_images/', null=True, blank=True)
    lab_tests = models.ManyToManyField(LabPatientTests, blank=True)
    is_package_cancelled = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(LabStaff, on_delete=models.PROTECT, null=True)
    last_updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.last_updated = timezone.now()
        super().save(*args, **kwargs)


class LabPatientRefund(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT)
    tests = models.ManyToManyField(LabPatientTests, blank=True)
    refund = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True)
    refund_mode = models.ForeignKey(ULabPaymentModeType, on_delete=models.PROTECT)
    add_refund_to_due = models.BooleanField(default=False)
    remarks = models.CharField(max_length=500, blank=True, null=True)
    remarks_from_staff = models.CharField(max_length=1000, blank=True, null=True)
    created_by = models.ForeignKey(LabStaff, on_delete=models.CASCADE, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    packages = models.ManyToManyField(LabPatientPackages, blank=True)
    refund_id = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return f"Refund ({self.refund_id})"

    def save(self, *args, **kwargs):
        date = timezone.now().date()
        refunds = LabPatientRefund.objects.filter(added_on__date=date)
        refunds_number = refunds.count() + 1
        date = date.strftime('%y%m%d')
        refund_id = f"REF{date}{refunds_number:03d}"
        self.refund_id = refund_id

        super().save(*args, **kwargs)


class PatientOTP(models.Model):
    mobile_number = models.CharField(max_length=15, null=True)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.IntegerField(default=0)
    last_sent_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        expiration_time = datetime.timedelta(minutes=5)
        return timezone.now() - self.last_sent_at > expiration_time

    def increment_attempts(self):
        self.attempts += 1
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

class PatientPDFs(models.Model):
    pdf_file = models.FileField(upload_to='pdf_files/')
    added_on = models.DateTimeField(auto_now_add=True)
    receipt_pdf = models.FileField(upload_to='receipt_pdfs/', null=True, blank=True)
