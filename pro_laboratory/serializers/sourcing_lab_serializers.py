from django_tenants.utils import schema_context
from rest_framework import serializers

from healtho_pro_user.models.users_models import Client
from pro_laboratory.models.global_models import LabGlobalTests, LabStaff
from pro_laboratory.models.patient_models import Patient, LabPatientTests
from pro_laboratory.models.phlebotomists_models import LabPhlebotomist
from pro_laboratory.models.sourcing_lab_models import SourcingLabRegistration, SourcingLabRevisedTestPrice, \
    SourcingLabTestsTracker, SourcingLabPatientReportUploads, SourcingLabPayments, SourcingLabLetterHeadSettings
from rest_framework import serializers
from healtho_pro_user.models.business_models import BusinessProfiles
from pro_universal_data.serializers import SourcingLabTypeSerializer


class SourcingLabRegistrationSerializer(serializers.ModelSerializer):
    b_id = serializers.PrimaryKeyRelatedField(queryset=BusinessProfiles.objects.all(), required=False)
    partner = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    lab_staff_login_access = serializers.SerializerMethodField()

    class Meta:
        model = SourcingLabRegistration
        fields = '__all__'

    def get_partner(self, obj):
        request = self.context.get('request')
        if request:
            client = request.client
            b_id = BusinessProfiles.objects.get(organization_name=client.name)
            if b_id:
                if obj.initiator and obj.acceptor:
                    if obj.initiator == b_id:
                        return BusinessProfilesSerializer(obj.acceptor).data
                    elif obj.acceptor == b_id:
                        return BusinessProfilesSerializer(obj.initiator).data
                else:
                    return {"id": None, "organization_name": obj.organization_name, "phone_number": obj.phone_number,
                            "address": obj.address}
        return None

    def get_can_edit(self, obj):
        request = self.context.get('request')
        if request:
            client = request.client
            b_id = BusinessProfiles.objects.get(organization_name=client.name)
            if b_id:
                if obj.initiator and obj.acceptor:
                    if obj.initiator == b_id:
                        return False
                    elif obj.acceptor == b_id:
                        return True
                else:
                    return True
        return None

    def get_lab_staff_login_access(self,obj):
        lab_staff=LabStaff.objects.filter(name=obj.organization_name,mobile_number=obj.phone_number).first()

        if lab_staff:
            return lab_staff.is_login_access
        else:
            return False

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        letterhead_settings = SourcingLabLetterHeadSettings.objects.filter(sourcing_lab=instance).first()

        representation['type'] = SourcingLabTypeSerializer(instance.type).data if instance.type else None

        representation['letterhead_settings'] = SourcingLabLetterHeadSettingsSerializer(letterhead_settings).data if letterhead_settings else ""

        return representation


class SourcingLabPaymentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourcingLabPayments
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if instance.created_by:
            representation['created_by'] = {"id":instance.created_by.id, "name":instance.created_by.name}

        return representation



class SourcingLabLetterHeadSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourcingLabLetterHeadSettings
        fields = '__all__'


class SourcingLabTestsTrackerSerializer(serializers.ModelSerializer):
    sourcing_lab = serializers.SerializerMethodField()
    patient = serializers.SerializerMethodField()
    test_status = serializers.SerializerMethodField()

    class Meta:
        model = SourcingLabTestsTracker
        fields = '__all__'

    def get_sourcing_lab(self, obj):
        request = self.context.get('request')
        if request:
            if obj.sourcing_lab:
                return SourcingLabRegistrationSerializer(obj.sourcing_lab, context={"request": request}).data

        return None

    def get_test_status(self, obj):
        try:
            test = LabPatientTests.objects.get(pk=obj.lab_patient_test)
            test_name = test.name
            test_id = test.id
            patient_id = obj.patient_id

            acceptor_business = obj.sourcing_lab.acceptor
            acceptor_client = Client.objects.get(name=acceptor_business.organization_name)

            initiator_business = obj.sourcing_lab.initiator

            with schema_context(acceptor_client.schema_name):
                client_sourcing_lab = SourcingLabRegistration.objects.filter(initiator=initiator_business,
                                                                             acceptor=acceptor_business).last()
                tracker = SourcingLabTestsTracker.objects.filter(sourcing_lab=client_sourcing_lab,
                                                                 patient_id=patient_id,
                                                                 lab_patient_test=test_id).last()
                if tracker:
                    if tracker.patient_id_at_client:
                        patient = Patient.objects.get(pk=tracker.patient_id_at_client)

                        test = LabPatientTests.objects.filter(patient=patient, name=test_name).last()

                        if test:
                            return test.status_id.name
                        else:
                            return None
        except Exception as error:
            return None
        return None

    def get_patient(self, obj):
        patient_id = obj.patient_id
        if obj.to_send:
            patient = Patient.objects.get(pk=patient_id)
            test = LabPatientTests.objects.get(pk=obj.lab_patient_test)
            phlebotomist = LabPhlebotomist.objects.filter(LabPatientTestID=test).last()
            assession_number = phlebotomist.assession_number if phlebotomist else ""
            collected_at = phlebotomist.collected_at if phlebotomist else ""
            return {"id": obj.patient_id,
                    "name": patient.name,
                    "title": patient.title.name,
                    "gender": patient.gender.name,
                    "age": patient.age,
                    "ULabPatientAge": patient.ULabPatientAge.name,
                    "mr_no": patient.mr_no,
                    "visit_id": patient.visit_id,
                    "added_on": patient.added_on,
                    "test": test.name,
                    "assession_number": assession_number,
                    "collected_at": collected_at
                    }
        else:
            request = self.context.get('request')
            if request:
                present_client = request.client
                present_business = BusinessProfiles.objects.get(organization_name=present_client.name)
                client_business = obj.sourcing_lab.initiator

                client = Client.objects.get(name=client_business.organization_name)
                with schema_context(client.schema_name):
                    try:
                        patient = Patient.objects.get(pk=patient_id)
                        test = LabPatientTests.objects.get(pk=obj.lab_patient_test)
                        phlebotomist = LabPhlebotomist.objects.filter(LabPatientTestID=test).last()
                        assession_number = phlebotomist.assession_number if phlebotomist else ""
                        collected_at = phlebotomist.collected_at if phlebotomist else ""
                        return {"id": obj.patient_id,
                                "name": patient.name,
                                "title": patient.title.name,
                                "gender": patient.gender.name,
                                "age": patient.age,
                                "ULabPatientAge": patient.ULabPatientAge.name,
                                "mr_no": patient.mr_no,
                                "visit_id": patient.visit_id,
                                "added_on": patient.added_on,
                                "test": test.name,
                                "assession_number": assession_number,
                                "collected_at": collected_at
                                }
                    except Patient.DoesNotExist:
                        return None
                    except Exception as error:
                        print(error)
                        return None
            return None


class SourcingLabTestsTrackerForGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourcingLabTestsTracker
        fields = '__all__'


class GroupedSourcingLabTestsTrackerSerializer(serializers.ModelSerializer):
    sourcing_lab = serializers.SerializerMethodField()
    data = serializers.SerializerMethodField()
    patient = serializers.SerializerMethodField()
    test_status = serializers.SerializerMethodField()

    class Meta:
        model = SourcingLabTestsTracker
        fields = ['patient_id', 'patient_id_at_client', 'patient', 'sourcing_lab', 'data']

    def get_sourcing_lab(self, obj):
        request = self.context.get('request')
        if request:
            if obj.sourcing_lab:
                return SourcingLabRegistrationSerializer(obj.sourcing_lab, context={"request": request}).data

        return None

    def get_test_status(self, obj):
        test = LabPatientTests.objects.get(pk=obj.lab_patient_test)
        test_name = test.name
        test_id = test.id
        patient_id = obj.patient_id

        acceptor_business = obj.sourcing_lab.acceptor
        acceptor_client = Client.objects.get(name=acceptor_business.organization_name)

        initiator_business = obj.sourcing_lab.initiator

        with schema_context(acceptor_client.schema_name):
            client_sourcing_lab = SourcingLabRegistration.objects.filter(acceptor=acceptor_business,
                                                                         initiator=initiator_business).last()
            tracker = SourcingLabTestsTracker.objects.filter(sourcing_lab=client_sourcing_lab,
                                                             patient_id=patient_id,
                                                             lab_patient_test=test_id).last()
            if tracker.patient_id_at_client:
                patient = Patient.objects.get(pk=tracker.patient_id_at_client)

                test = LabPatientTests.objects.filter(patient=patient, name=test_name).last()

                if test:
                    return test.status_id.name
        return None

    def get_data(self, obj):
        instances = SourcingLabTestsTracker.objects.filter(patient_id=obj.patient_id, sourcing_lab=obj.sourcing_lab)
        return SourcingLabTestsTrackerForGroupSerializer(instances, many=True).data

    def get_patient(self, obj):
        patient_id = obj.patient_id
        if obj.to_send:
            patient = Patient.objects.get(pk=patient_id)
            test = LabPatientTests.objects.get(pk=obj.lab_patient_test)
            phlebotomist = LabPhlebotomist.objects.filter(LabPatientTestID=test).last()
            assession_number = phlebotomist.assession_number if phlebotomist else ""
            collected_at = phlebotomist.collected_at if phlebotomist else ""
            return {"id": obj.patient_id,
                    "name": patient.name,
                    "title": patient.title.name,
                    "gender": patient.gender.name,
                    "age": patient.age,
                    "ULabPatientAge": patient.ULabPatientAge.name,
                    "mr_no": patient.mr_no,
                    "visit_id": patient.visit_id,
                    "added_on": patient.added_on,
                    "test": test.name,
                    "assession_number": assession_number,
                    "collected_at": collected_at
                    }
        else:
            request = self.context.get('request')
            if request:
                present_client = request.client
                present_business = BusinessProfiles.objects.get(organization_name=present_client.name)
                client_business = obj.sourcing_lab.initiator

                client = Client.objects.get(name=client_business.organization_name)
                with schema_context(client.schema_name):
                    try:
                        patient = Patient.objects.get(pk=patient_id)
                        test = LabPatientTests.objects.get(pk=obj.lab_patient_test)
                        phlebotomist = LabPhlebotomist.objects.filter(LabPatientTestID=test).last()
                        assession_number = phlebotomist.assession_number if phlebotomist else ""
                        collected_at = phlebotomist.collected_at if phlebotomist else ""
                        return {"id": obj.patient_id,
                                "name": patient.name,
                                "title": patient.title.name,
                                "gender": patient.gender.name,
                                "age": patient.age,
                                "ULabPatientAge": patient.ULabPatientAge.name,
                                "mr_no": patient.mr_no,
                                "visit_id": patient.visit_id,
                                "added_on": patient.added_on,
                                "test": test.name,
                                "assession_number": assession_number,
                                "collected_at": collected_at
                                }
                    except Patient.DoesNotExist:
                        return None
                    except Exception as error:
                        print(error)
                        return None
            return None


class SourcingLabRevisedTestPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourcingLabRevisedTestPrice
        fields = '__all__'


class SourcingLabRevisedLabGlobalTestsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabGlobalTests
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        foreign_keys = ['department']
        for fk in foreign_keys:
            fk_id = representation.get(fk)
            if fk_id is not None:
                fk_name = getattr(instance, f'{fk}_name', None)
                if fk_name is None:
                    fk_name = getattr(instance, fk).name
                representation[fk] = fk_name

        representation['revised_price'] = None

        sourcing_lab = self.context.get('sourcing_lab')
        if sourcing_lab:
            revised_price = SourcingLabRevisedTestPrice.objects.filter(sourcing_lab=sourcing_lab,
                                                                       LabGlobalTestId=instance).first()
            if revised_price:
                representation['revised_price'] = SourcingLabRevisedTestPriceSerializer(revised_price).data
        return representation


class BusinessProfilesSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessProfiles
        fields = ['id', 'organization_name', 'address', 'phone_number']


class SourcingLabPatientReportUploadsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourcingLabPatientReportUploads
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        patient = instance.patient

        representation['patient'] = {"id": patient.id, "name": patient.name, "mobile_number": patient.mobile_number}

        tests = instance.tests.all()

        tests_data = []

        for test in tests:
            tests_data.append({"id": test.id, "name": test.name})

        representation['tests'] = tests_data

        return representation
