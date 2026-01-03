from django.contrib import admin

from healtho_pro_user.models.subscription_models import BusinessBillCalculationType, BusinessSubscriptionPlans, \
    OverallBusinessSubscriptionStatus, OverallBusinessSubscriptionPlansPurchased, BusinessSubscriptionType
from healtho_pro_user.models.users_models import HealthOProUser, ULoginSliders, Client, UserTenant, OTP
from healtho_pro_user.models.universal_models import Country, State, City, UProDoctorSpecializations, \
    ProDoctorLanguageSpoken, ProDoctorAwardsRecognitions, ProDoctorResearchPublications, ProDoctorRecognitionsImages, \
    ProDoctorResearchPublicationsImages, ProDoctorClinic, ProDoctor, UserType, HealthcareRegistryType, \
    SupportInfoTutorials
from healtho_pro_user.models.business_models import BusinessProfiles, BContacts, BContactFor, BExecutive, \
    BusinessProfilesImages

admin.site.register(HealthOProUser)
admin.site.register(ULoginSliders)
admin.site.register(UserType)
admin.site.register(Country)
admin.site.register(State)
admin.site.register(City)
admin.site.register(UProDoctorSpecializations)
admin.site.register(ProDoctorLanguageSpoken)
admin.site.register(ProDoctorAwardsRecognitions)
admin.site.register(ProDoctorResearchPublications)
admin.site.register(ProDoctorRecognitionsImages)
admin.site.register(ProDoctorResearchPublicationsImages)
admin.site.register(ProDoctorClinic)
admin.site.register(ProDoctor)
admin.site.register(BusinessProfiles)
admin.site.register(BContacts)
admin.site.register(BContactFor)
admin.site.register(BExecutive)
admin.site.register(HealthcareRegistryType)
admin.site.register(SupportInfoTutorials)
admin.site.register(UserTenant)
admin.site.register(OTP)
admin.site.register(BusinessProfilesImages)
admin.site.register(Client)
admin.site.register(BusinessBillCalculationType)
admin.site.register(BusinessSubscriptionPlans)
admin.site.register(OverallBusinessSubscriptionStatus)
admin.site.register(OverallBusinessSubscriptionPlansPurchased)
admin.site.register(BusinessSubscriptionType)

