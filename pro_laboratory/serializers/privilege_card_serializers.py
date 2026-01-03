from django.db.models import Sum
from django.forms import model_to_dict
from rest_framework import serializers

from pro_laboratory.models.patient_models import Patient, LabPatientReceipts
from pro_laboratory.models.privilege_card_models import PrivilegeCards, PrivilegeCardFor, \
    PrivilegeCardMembers, PrivilegeCardMemberships, PrivilegeCardsApplicableBenefits, PrivilegeCardsLabTestBenefits, \
    PrivilegeCardsLabDepartmentsBenefits, PrivilegeCardsMembershipApplicableBenefits
from pro_laboratory.serializers.global_serializers import LabStaffSerializer, LabDepartmentsSerializer

from pro_universal_data.serializers import TimeDurationTypesSerializer, \
    ULabPatientGenderSerializer, ULabRelationsSerializer, PrivilegeCardBenefitsSerializer, ULabPatientTitlesSerializer


class PrivilegeCardForSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivilegeCardFor
        fields = '__all__'


class PrivilegeCardsApplicableBenefitsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivilegeCardsApplicableBenefits
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['benefit'] = PrivilegeCardBenefitsSerializer(instance.benefit).data

        return representation

class PrivilegeCardsMembershipApplicableBenefitsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivilegeCardsMembershipApplicableBenefits
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['benefit'] = PrivilegeCardBenefitsSerializer(instance.benefit).data

        return representation


class PrivilegeCardsLabTestBenefitsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivilegeCardsLabTestBenefits
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        test = instance.test

        representation['test']={"id":test.id, "name":test.name,"price":test.price }

        return representation




class PrivilegeCardsLabDepartmentsBenefitsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivilegeCardsLabDepartmentsBenefits
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        department = instance.department

        representation['department']={"id":department.id, "name":department.name}

        return representation




class PrivilegeCardsSerializer(serializers.ModelSerializer):
    benefits = PrivilegeCardsApplicableBenefitsSerializer(many=True, write_only=True, required=False, allow_null=True)

    class Meta:
        model = PrivilegeCards
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        benefits = PrivilegeCardsApplicableBenefits.objects.filter(card=instance)
        if benefits:
            representation['benefits'] = PrivilegeCardsApplicableBenefitsSerializer(benefits, many=True).data

        if instance.duration_type:
            representation['duration_type'] = TimeDurationTypesSerializer(instance.duration_type).data

        if instance.card_for:
            representation['card_for'] = PrivilegeCardForSerializer(instance.card_for).data

        created_by = instance.created_by
        if created_by:
            representation['created_by'] = {"id": created_by.id, "name": created_by.name,
                                            "mobile_number": created_by.mobile_number}

        last_updated_by = instance.last_updated_by
        if created_by:
            representation['last_updated_by'] = {"id": last_updated_by.id, "name": last_updated_by.name,
                                                 "mobile_number": last_updated_by.mobile_number}

        test_wise_benefits = PrivilegeCardsLabTestBenefits.objects.filter(card=instance)

        representation['test_wise_benefits']=PrivilegeCardsLabTestBenefitsSerializer(test_wise_benefits, many=True).data if test_wise_benefits else []

        department_wise_benefits = PrivilegeCardsLabDepartmentsBenefits.objects.filter(card=instance)

        representation['department_wise_benefits'] = PrivilegeCardsLabDepartmentsBenefitsSerializer(department_wise_benefits,
                                                                                       many=True).data if department_wise_benefits else []

        return representation


class PrivilegeCardMembersSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivilegeCardMembers
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        gender = representation.get('gender')
        if gender:
            representation['gender'] = ULabPatientGenderSerializer(instance.gender).data

        return representation


class PrivilegeCardMembershipSerializer(serializers.ModelSerializer):
    card_holder=PrivilegeCardMembersSerializer(write_only=True)

    class Meta:
        model = PrivilegeCardMemberships
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        representation['card_holder'] = PrivilegeCardMembersSerializer(instance.card_holder).data
        representation['card'] = PrivilegeCardsSerializer(instance.card).data
        gender = representation.get('gender')
        if gender:
            representation['gender'] = ULabPatientGenderSerializer(instance.gender).data

        if instance.duration_type:
            representation['duration_type'] = TimeDurationTypesSerializer(instance.duration_type).data

        if instance.card_for:
            representation['card_for'] = PrivilegeCardForSerializer(instance.card_for).data

        created_by = representation.get('created_by')
        if created_by:
            representation['created_by_name'] = instance.created_by.name

        last_updated_by = representation.get('last_updated_by')
        if last_updated_by:
            representation['last_updated_by_name'] = instance.last_updated_by.name

        applicable_benefits = PrivilegeCardsMembershipApplicableBenefits.objects.filter(membership=instance)

        representation['benefits']=PrivilegeCardsMembershipApplicableBenefitsSerializer(applicable_benefits, many=True).data if applicable_benefits else []

        card = instance.card

        test_wise_benefits = PrivilegeCardsLabTestBenefits.objects.filter(card=card)

        representation['test_wise_benefits'] = PrivilegeCardsLabTestBenefitsSerializer(test_wise_benefits,
                                                                                       many=True).data if test_wise_benefits else []

        department_wise_benefits = PrivilegeCardsLabDepartmentsBenefits.objects.filter(card=card)

        representation['department_wise_benefits'] = PrivilegeCardsLabDepartmentsBenefitsSerializer(
            department_wise_benefits, many=True).data if department_wise_benefits else []

        return representation



class PrivilegeCardUsageOfPatientSerializer(serializers.ModelSerializer):
    lab_tests = serializers.SerializerMethodField()
    bill = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = ['id','name', 'lab_tests', 'added_on', 'created_by', 'mr_no','visit_id', 'email', 'privilege_membership',
                  'age', 'mobile_number', 'gender', 'referral_doctor', 'ULabPatientAge', 'address', 'visit_count', 'bill']


    def get_lab_tests(self, obj):
        from pro_laboratory.serializers.patient_serializers import StandardViewLabTestSerializer
        lab_tests = obj.labpatienttests_set.exclude(is_package_test=True)
        return StandardViewLabTestSerializer(instance=lab_tests, many=True, context={"context": self.context}).data

    def get_bill(self, obj):
        total_cost = obj.labpatientinvoice.total_cost
        privilege_card_discount=LabPatientReceipts.objects.filter(patient=obj,discount_type__name='Privilege Card Discount').aggregate(total_discount=Sum('discount_amt'))['total_discount']

        benefit_type = 'Free' if total_cost == privilege_card_discount else 'Discount'

        return {"total_cost":total_cost, "privilege_card_discount":privilege_card_discount, "benefit_type":benefit_type}



        return StandardViewLabTestSerializer(instance=lab_tests, many=True, context={"context": self.context}).data


    def to_representation(self, instance):
        representation = super().to_representation(instance)
        created_by_id = representation.get('created_by')
        if created_by_id is not None:
            created_by_name = instance.created_by.name
            representation['created_by'] = created_by_name
        return representation

