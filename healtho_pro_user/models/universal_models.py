from django.db import models
from django.utils import timezone


class Country(models.Model):
    name = models.CharField(max_length=100)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Country"
        verbose_name_plural = "Countries"

    def __str__(self):
        return self.name


class State(models.Model):
    name = models.CharField(max_length=100)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "State"
        verbose_name_plural = "States"

    def __str__(self):
        return self.name


class City(models.Model):
    name = models.CharField(max_length=100)
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "City"
        verbose_name_plural = "Cities"

    def __str__(self):
        return self.name


class UserType(models.Model):  # A Doctor, Healthcare Professional, Healthcare Personnel
    type_name = models.CharField(max_length=100)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.type_name


class UProDoctorSpecializations(models.Model):  # if others then add API
    name = models.CharField(max_length=200)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Universal Pro Doctor Specialization"
        verbose_name_plural = "Universal Pro Doctor Specializations"

    def __str__(self):
        return self.name


class ProDoctorLanguageSpoken(models.Model):
    name = models.CharField(max_length=200)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Language Spoken by Pro Doctor"
        verbose_name_plural = "Languages Spoken by Pro Doctors"

    def __str__(self):
        return self.name


class ProDoctorAwardsRecognitions(models.Model):
    pro_user_id = models.ForeignKey('healtho_pro_user.HealthOProUser', on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    datetime = models.DateField()
    link = models.URLField(max_length=200)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pro Doctor Award and Recognition"
        verbose_name_plural = "Pro Doctor Awards and Recognitions"

    def __str__(self):
        return self.name


class ProDoctorResearchPublications(models.Model):
    pro_user_id = models.ForeignKey('healtho_pro_user.HealthOProUser', on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    datetime = models.DateField()
    link = models.URLField(max_length=200)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pro Doctor Research and Publication"
        verbose_name_plural = "Pro Doctor Research and Publications"

    def __str__(self):
        return self.name


class ProDoctorRecognitionsImages(models.Model):
    ProDoctorAwardsRecognitionsID = models.ForeignKey(ProDoctorAwardsRecognitions,
                                                      related_name='proDoctorsRecognitionImages',
                                                      on_delete=models.CASCADE)
    image = models.ImageField(upload_to='ProDoctorRecognitionsImages_Uploads/', null=True, blank=True)

    class Meta:
        verbose_name = "Pro Doctor Recognitions Image"
        verbose_name_plural = "Pro Doctor Recognitions Images"


class ProDoctorResearchPublicationsImages(models.Model):
    ProDoctorResearchPublicationsID = models.ForeignKey(ProDoctorResearchPublications,
                                                        related_name='proDoctorsRecognitionImages',
                                                        on_delete=models.CASCADE)
    image = models.ImageField(upload_to='ProDoctorResearchPublicationsImages_Uploads/', null=True, blank=True)

    class Meta:
        verbose_name = "Pro Doctor Research Publications Image"
        verbose_name_plural = "Pro Doctor Research Publications Images"


class ProDoctorClinic(models.Model):
    office_address = models.TextField(blank=True)  # Doctor's office address
    availability = models.CharField(max_length=100, blank=True)  # Example: "Mondays and Thursdays, 9am-4pm"

    class Meta:
        verbose_name = "Pro Doctor Clinic"
        verbose_name_plural = "Pro Doctor Clinics"


class Shift(models.Model):
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name}'


class Consultation(models.Model):
    name = models.CharField(max_length=100)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Consultation"
        verbose_name_plural = "Consultations"

    def __str__(self):
        return f'{self.name}'


class ProDoctor(models.Model):
    pro_user_id = models.OneToOneField('healtho_pro_user.HealthOProUser', on_delete=models.PROTECT)
    license_number = models.CharField(max_length=100, unique=True, null=True)
    years_of_experience = models.IntegerField(blank=True, null=True)
    medical_school = models.CharField(max_length=500, blank=True, null=True)
    graduation_year = models.IntegerField(blank=True, null=True)
    latitude = models.CharField(max_length=100, blank=True, null=True)
    longitude = models.CharField(max_length=100, blank=True, null=True)
    profile_image = models.TextField(null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pro Doctor Personal Info"
        verbose_name_plural = "Pro Doctor Personal Info"


class ProDoctorProfessionalDetails(models.Model):
    pro_doctor = models.ForeignKey(ProDoctor, on_delete=models.CASCADE, related_name='professional_details')
    geo_area = models.CharField(max_length=100, null=True, blank=True)
    specialization = models.ForeignKey(UProDoctorSpecializations, on_delete=models.PROTECT, null=True)
    languages_spoken = models.ManyToManyField(ProDoctorLanguageSpoken, blank=True)
    awards_and_recognitions = models.ManyToManyField(ProDoctorAwardsRecognitions, blank=True)
    research_and_publications = models.ManyToManyField(ProDoctorResearchPublicationsImages, blank=True)

    class Meta:
        verbose_name = "Pro Doctor Professional Details"
        verbose_name_plural = "Pro Doctor Professional Details"


class HealthcareRegistryType(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class SupportInfoTutorials(models.Model):
    slug = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=500)
    youtube_link = models.TextField()
    article_link = models.URLField()
    quick_steps = models.CharField(max_length=800)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class DeliveryMode(models.Model):
    name = models.CharField(max_length=500)
    is_selected = models.BooleanField(default=False)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
