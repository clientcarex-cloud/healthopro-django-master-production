from django.db import models
from healtho_pro_user.models.users_models import HealthOProUser, Client
from interoperability.models import LabTpaSecretKeys
from pro_laboratory.models.global_models import LabStaff
from pro_laboratory.models.patient_models import Patient
from pro_universal_data.models import PrintTemplateType, DashBoardOptions


class TpaUltrasoundConfig(models.Model):
    lab_tpa_secret_keys = models.ForeignKey(LabTpaSecretKeys, on_delete=models.PROTECT)
    directory_path = models.CharField(max_length=100)
    processing_date = models.DateTimeField()
    last_updated = models.DateTimeField(auto_now=True)


class TpaUltrasoundImages(models.Model):
    image = models.ImageField(upload_to='ultrasound_images/', blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True, blank=True, null=True)


class TpaUltrasound(models.Model):
    date = models.DateField()
    main_folder = models.CharField(max_length=300)
    sub_folder = models.CharField(max_length=300, blank=True, null=True)
    xml_data = models.TextField(null=True, blank=True)
    meta_info = models.TextField(null=True, blank=True)
    images = models.ManyToManyField(TpaUltrasoundImages, blank=True)
    is_status = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)



class PrintTemplate(models.Model):
    name = models.CharField(max_length=100)
    print_template_type = models.ForeignKey(PrintTemplateType, on_delete=models.PROTECT, null=True, blank=True)
    is_default = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_default:
            # Set is_default=False for other templates of the same TemplateTypeID
            PrintTemplate.objects.filter(
                print_template_type=self.print_template_type
            ).exclude(
                id=self.id
            ).update(
                is_default=False
            )
        super(PrintTemplate, self).save(*args, **kwargs)


class PrintDataTemplate(models.Model):
    print_template = models.ForeignKey(PrintTemplate, on_delete=models.PROTECT)
    header = models.TextField(blank=True, null=True)
    header_height = models.DecimalField(max_digits=6, decimal_places=1, blank=True, null=True)
    footer = models.TextField(blank=True, null=True)
    data = models.TextField(blank=True)
    rtf_content = models.TextField(blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class ChangesInModels(models.Model):
    field_name = models.CharField(max_length=500, null=True, blank=True)
    before_value = models.TextField(null=True, blank=True)
    after_value = models.TextField(null=True, blank=True)


class ActivityLogs(models.Model):
    user = models.ForeignKey(HealthOProUser, on_delete=models.PROTECT, null=True, blank=True)
    lab_staff = models.ForeignKey(LabStaff, on_delete=models.PROTECT, null=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, null=True, blank=True)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, null=True, blank=True)
    operation = models.CharField(max_length=20, null=True, blank=True)
    url = models.CharField(max_length=100, null=True, blank=True)
    model = models.CharField(max_length=300, null=True, blank=True)
    model_instance_id = models.PositiveBigIntegerField(blank=True, null=True)
    activity = models.CharField(max_length=2000, null=True, blank=True)
    changes = models.ManyToManyField(ChangesInModels, blank=True)
    response_code = models.PositiveIntegerField(null=True, blank=True)
    duration = models.CharField(max_length=20, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.timestamp} - {self.user} in {self.client}, {self.operation}, {self.url}'

#
class DashBoardSettings(models.Model):
    dash_board = models.ForeignKey(DashBoardOptions, on_delete=models.PROTECT, blank=True, null=True)
    lab_staff = models.ForeignKey(LabStaff, on_delete=models.PROTECT)
    graph_size = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    ordering = models.IntegerField(null=True, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)