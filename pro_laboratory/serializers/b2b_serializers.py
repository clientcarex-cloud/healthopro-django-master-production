from rest_framework import serializers

from pro_laboratory.models.b2b_models import Company, CompanyRevisedPrices, CompanyWorkPartnership
from pro_laboratory.models.global_models import LabGlobalTests, LabGlobalPackages
from pro_laboratory.serializers.global_serializers import LabGlobalTestsSerializer


class CompanyRevisedPricesSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyRevisedPrices
        fields = '__all__'


class LabGlobalTestsRevisedPricesSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabGlobalTests
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['department'] = instance.department.name if instance.department else None
        representation['revised_price'] = None
        company = self.context.get('company')
        if company:
            revised_price = CompanyRevisedPrices.objects.filter(company__id=company, LabGlobalTestId=instance).first()
            if revised_price:
                representation['revised_price'] = CompanyRevisedPricesSerializer(revised_price).data
        return representation


class LabGlobalPackagesRevisedPricesSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabGlobalPackages
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['revised_price'] = None

        lab_tests = instance.lab_tests.all()

        representation['lab_tests'] = LabGlobalTestsRevisedPricesSerializer(lab_tests, many=True,
                                                           context={'company': instance.id}).data

        company = self.context.get('company')
        if company:
            revised_price = CompanyRevisedPrices.objects.filter(company__id=company, LabGlobalPackageId=instance).first()
            if revised_price:
                representation['revised_price'] = CompanyRevisedPricesSerializer(revised_price).data
        return representation



class CompanyWorkPartnershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyWorkPartnership
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['company'] = {"id":instance.company.id,
                                     "name":instance.company.name} if instance.company else None

        return representation


class CompanyWorkPartnershipGetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyWorkPartnership
        fields = '__all__'


class CompanySerializer(serializers.ModelSerializer):
    partners = CompanyWorkPartnershipGetSerializer(many=True, required=False)

    class Meta:
        model = Company
        fields = '__all__'


class GenerateCompanyInvoiceSerializer(serializers.Serializer):
    patient_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )
    partner_id = serializers.CharField()

    class Meta:
        fields = '__all__'
