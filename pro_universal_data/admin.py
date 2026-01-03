from django.contrib import admin

from pro_laboratory.models.privilege_card_models import PrivilegeCardFor
from pro_universal_data.models import ULabMenus, ULabTestStatus, ULabPaymentModeType, ULabReportType, ULabPatientAge, \
    ULabMethodology, ULabPatientGender, MessagingServiceTypes, MessagingVendors, MessagingSendType, \
    MessagingCategory, MessagingFor, Tag, PrintTemplateType, \
    TimeDurationTypes, ULabRelations, ULabFonts, UserPermissions, ULabReportsGender

# Register your models here.
admin.site.register(ULabTestStatus)
admin.site.register(ULabPaymentModeType)
admin.site.register(ULabReportType)
admin.site.register(ULabPatientAge)
admin.site.register(ULabMethodology)
admin.site.register(ULabPatientGender)
admin.site.register(PrintTemplateType)
admin.site.register(PrivilegeCardFor)
admin.site.register(TimeDurationTypes)
admin.site.register(ULabRelations)

@admin.register(UserPermissions)
class UserPermissionsAdmin(admin.ModelAdmin):
    list_display = ('name', 'ordering', 'description', 'label', 'is_active')
    list_editable = ('ordering', 'description', 'label', 'is_active')

@admin.register(ULabMenus)
class ULabMenusAdmin(admin.ModelAdmin):
    list_display = ('id','label', 'ordering', 'icon', 'link', 'is_active', 'health_care_registry_type')
    list_editable = ('ordering', 'icon', 'link', 'is_active', 'health_care_registry_type')

# third party api models
from django.contrib import admin
from pro_universal_data.models import MessagingTemplates

# Register your models here.
admin.site.register(MessagingTemplates)
admin.site.register(MessagingServiceTypes)
admin.site.register(MessagingVendors)
admin.site.register(MessagingSendType)
admin.site.register(MessagingCategory)
admin.site.register(MessagingFor)
admin.site.register(ULabFonts)
admin.site.register(ULabReportsGender)


class TagAdmin(admin.ModelAdmin):
    list_display = ('messaging_send_type', 'tag_name', 'tag_formula', 'is_collection')

admin.site.register(Tag, TagAdmin)
