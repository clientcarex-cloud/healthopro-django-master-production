from django.db import transaction
from rest_framework import serializers
from pro_laboratory.models.pndtform_models import ProceduresPerformed, PNDTResults, RecommendedTests, \
    FamilyGeneticHistory, PrenatalScreening, MTPInfo


class FamilyGeneticHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FamilyGeneticHistory
        exclude = ['patient']


class PrenatalScreeningSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrenatalScreening
        exclude = ['patient']


class MTPInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MTPInfo
        exclude = ['patient']


class RecommendedTestsSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendedTests
        exclude = ['patient']


class ProceduresPerformedSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProceduresPerformed
        exclude = ['patient']


class PNDTResultsSerializer(serializers.ModelSerializer):
    family_genetic_history = FamilyGeneticHistorySerializer(required=False)
    prenatal_screening = PrenatalScreeningSerializer(required=False)
    mtp_info = MTPInfoSerializer(required=False)
    procedures_performed = ProceduresPerformedSerializer(required=False)
    recommended_tests = RecommendedTestsSerializer(required=False)

    class Meta:
        model = PNDTResults
        fields = '__all__'

    def create(self, validated_data):
        patient_id = validated_data.pop('patient')

        family_genetic_history_data = validated_data.pop('family_genetic_history', {})
        prenatal_screening_data = validated_data.pop('prenatal_screening', {})
        mtp_info_data = validated_data.pop('mtp_info', {})
        procedures_performed_data = validated_data.pop('procedures_performed', {})
        recommended_tests_data = validated_data.pop('recommended_tests', {})
        doctors = procedures_performed_data.pop('doctors', [])

        with transaction.atomic():
            pndt_results = PNDTResults.objects.create(patient=patient_id, **validated_data)
            FamilyGeneticHistory.objects.create(patient=patient_id, **family_genetic_history_data)
            PrenatalScreening.objects.create(patient=patient_id, **prenatal_screening_data)
            MTPInfo.objects.create(patient=patient_id, **mtp_info_data)
            procedures_performed_instance = ProceduresPerformed.objects.create(patient=patient_id,
                                                                               **procedures_performed_data)
            procedures_performed_instance.doctors.set(doctors)
            procedures_performed_instance.save()
            RecommendedTests.objects.create(patient=patient_id, **recommended_tests_data)
        return pndt_results

    def update(self, instance, validated_data):
        family_genetic_history_data = validated_data.pop('family_genetic_history', None)
        prenatal_screening_data = validated_data.pop('prenatal_screening', None)
        mtp_info_data = validated_data.pop('mtp_info', None)
        procedures_performed_data = validated_data.pop('procedures_performed', None)
        recommended_tests_data = validated_data.pop('recommended_tests', None)

        doctors = procedures_performed_data.pop('doctors', []) if procedures_performed_data else []

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if family_genetic_history_data:
            family_genetic_history_instance, _ = FamilyGeneticHistory.objects.get_or_create(patient=instance.patient)
            family_genetic_history_serializer = FamilyGeneticHistorySerializer(family_genetic_history_instance,
                                                                               data=family_genetic_history_data,
                                                                               partial=True)
            if family_genetic_history_serializer.is_valid():
                family_genetic_history_serializer.save()

        if prenatal_screening_data:
            prenatal_screening_instance, _ = PrenatalScreening.objects.get_or_create(patient=instance.patient)
            prenatal_screening_serializer = PrenatalScreeningSerializer(prenatal_screening_instance,
                                                                        data=prenatal_screening_data, partial=True)
            if prenatal_screening_serializer.is_valid():
                prenatal_screening_serializer.save()

        if mtp_info_data:
            mtp_info_instance, _ = MTPInfo.objects.get_or_create(patient=instance.patient)
            mtp_info_serializer = MTPInfoSerializer(mtp_info_instance, data=mtp_info_data, partial=True)
            if mtp_info_serializer.is_valid():
                mtp_info_serializer.save()

        if procedures_performed_data:
            if 'clinic_details' in procedures_performed_data:
                procedures_performed_data['clinic_details'] = procedures_performed_data['clinic_details'].id

            procedures_performed_instance, created = ProceduresPerformed.objects.get_or_create(patient=instance.patient)
            procedures_performed_serializer = ProceduresPerformedSerializer(procedures_performed_instance,
                                                                            data=procedures_performed_data,
                                                                            partial=True)

            if procedures_performed_serializer.is_valid():
                procedures_performed_serializer.save()
            procedures_performed_instance.doctors.set(doctors)

        if recommended_tests_data:
            recommended_tests_instance, _ = RecommendedTests.objects.get_or_create(patient=instance.patient)
            recommended_tests_serializer = RecommendedTestsSerializer(recommended_tests_instance,
                                                                      data=recommended_tests_data, partial=True)
            if recommended_tests_serializer.is_valid():
                recommended_tests_serializer.save()

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        patient_id = instance.patient_id
        family_genetic_history = FamilyGeneticHistory.objects.filter(patient_id=patient_id).first()
        prenatal_screening = PrenatalScreening.objects.filter(patient_id=patient_id).first()
        mtp_info = MTPInfo.objects.filter(patient_id=patient_id).first()
        recommended_tests = RecommendedTests.objects.filter(patient_id=patient_id).first()
        procedures_performed = ProceduresPerformed.objects.filter(patient_id=patient_id).first()

        representation['family_genetic_history'] = FamilyGeneticHistorySerializer(
            family_genetic_history).data if family_genetic_history else None
        representation['prenatal_screening'] = PrenatalScreeningSerializer(
            prenatal_screening).data if prenatal_screening else None
        representation['mtp_info'] = MTPInfoSerializer(mtp_info).data if mtp_info else None
        representation['recommended_tests'] = RecommendedTestsSerializer(
            recommended_tests).data if recommended_tests else None
        representation['procedures_performed'] = ProceduresPerformedSerializer(
            procedures_performed).data if procedures_performed else None
        return representation


#
# class PNDTResultsSerializer(serializers.ModelSerializer):
#     family_genetic_history = FamilyGeneticHistorySerializer(required=False)
#     prenatal_screening = PrenatalScreeningSerializer(required=False)
#     mtp_info = MTPInfoSerializer(required=False)
#     procedures_performed = ProceduresPerformedSerializer(required=False)
#     recommended_tests = RecommendedTestsSerializer(required=False)
#
#     class Meta:
#         model = PNDTResults
#         fields = '__all__'
#
#     def create(self, validated_data):
#         patient_id = validated_data.pop('patient')
#
#         family_genetic_history_data = validated_data.pop('family_genetic_history', {})
#         prenatal_screening_data = validated_data.pop('prenatal_screening', {})
#         mtp_info_data = validated_data.pop('mtp_info', {})
#         procedures_performed_data = validated_data.pop('procedures_performed', {})
#         recommended_tests_data = validated_data.pop('recommended_tests', {})
#         doctors = procedures_performed_data.pop('doctors', [])
#
#         with transaction.atomic():
#             pndt_results = PNDTResults.objects.create(patient=patient_id, **validated_data)
#             FamilyGeneticHistory.objects.create(patient=patient_id, **family_genetic_history_data)
#             PrenatalScreening.objects.create(patient=patient_id, **prenatal_screening_data)
#             MTPInfo.objects.create(patient=patient_id, **mtp_info_data)
#             procedures_performed_instance = ProceduresPerformed.objects.create(patient=patient_id, **procedures_performed_data)
#             procedures_performed_instance.doctors.set(doctors)
#             procedures_performed_instance.save()
#             RecommendedTests.objects.create(patient=patient_id, **recommended_tests_data)
#
#         return pndt_results
#
#     def update(self, instance, validated_data):
#         family_genetic_history_data = validated_data.pop('family_genetic_history', None)
#         prenatal_screening_data = validated_data.pop('prenatal_screening', None)
#         mtp_info_data = validated_data.pop('mtp_info', None)
#         procedures_performed_data = validated_data.pop('procedures_performed', None)
#         print(procedures_performed_data)
#         recommended_tests_data = validated_data.pop('recommended_tests', None)
#
#         doctors = procedures_performed_data.pop('doctors', []) if procedures_performed_data else None
#         print(doctors)
#
#         for attr, value in validated_data.items():
#             setattr(instance, attr, value)
#         instance.save()
#
#         if family_genetic_history_data:
#             family_genetic_history_instance, _ = FamilyGeneticHistory.objects.get_or_create(patient=instance.patient)
#             print(family_genetic_history_instance.patient.id)
#             family_genetic_history_serializer = FamilyGeneticHistorySerializer(family_genetic_history_instance,
#                                                                                data=family_genetic_history_data)
#             if family_genetic_history_serializer.is_valid():
#                 family_genetic_history_serializer.save()
#
#         if prenatal_screening_data:
#             prenatal_screening_instance, _ = PrenatalScreening.objects.get_or_create(patient=instance.patient)
#             print(prenatal_screening_instance.patient.id)
#             prenatal_screening_serializer = PrenatalScreeningSerializer(prenatal_screening_instance,
#                                                                         data=prenatal_screening_data)
#             if prenatal_screening_serializer.is_valid():
#                 prenatal_screening_serializer.save()
#
#         if mtp_info_data:
#             mtp_info_instance, _ = MTPInfo.objects.get_or_create(patient=instance.patient)
#             print(mtp_info_instance.patient.id)
#             mtp_info_serializer = MTPInfoSerializer(mtp_info_instance, data=mtp_info_data)
#             if mtp_info_serializer.is_valid():
#                 # print(mtp_info_serializer)
#                 mtp_info_serializer.save()
#
#         if procedures_performed_data:
#             procedures_performed_instance, _ = ProceduresPerformed.objects.get_or_create(patient=instance.patient)
#             print(procedures_performed_instance.patient.id)
#             print(procedures_performed_instance.registration_number)
#             print(procedures_performed_instance.pndt_number)
#             print(procedures_performed_instance.clinic_details)
#             print(procedures_performed_data)
#             procedures_performed_serializer = ProceduresPerformedSerializer(procedures_performed_instance,
#                                                                          data=procedures_performed_data)
#
#             # print(procedures_performed_serializer)
#             if procedures_performed_serializer.is_valid():
#                 # print('1')
#                 # print(procedures_performed_serializer.is_valid())
#                 procedures_performed_serializer.save()
#                 print(procedures_performed_serializer.data)
#             procedures_performed_instance.doctors.set(doctors)
#             print('higlfdlelfdfkewffkdroffrvkvfkbbog')
#             print(procedures_performed_instance)
#
#         if recommended_tests_data:
#             recommended_tests_instance, _ = RecommendedTests.objects.get_or_create(patient=instance.patient)
#             recommended_tests_serializer = RecommendedTestsSerializer(recommended_tests_instance,
#                                                                       data=recommended_tests_data)
#             if recommended_tests_serializer.is_valid():
#                 recommended_tests_serializer.save()
#         return instance
#
#     def to_representation(self, instance):
#         representation = super().to_representation(instance)
#         patient_id = instance.patient_id
#         family_genetic_history = FamilyGeneticHistory.objects.filter(patient_id=patient_id).first()
#         prenatal_screening = PrenatalScreening.objects.filter(patient_id=patient_id).first()
#         mtp_info = MTPInfo.objects.filter(patient_id=patient_id).first()
#         recommended_tests = RecommendedTests.objects.filter(patient_id=patient_id).first()
#         procedures_performed = ProceduresPerformed.objects.filter(patient_id=patient_id).first()
#
#         representation['family_genetic_history'] = FamilyGeneticHistorySerializer(
#             family_genetic_history).data if family_genetic_history else None
#         representation['prenatal_screening'] = PrenatalScreeningSerializer(
#             prenatal_screening).data if prenatal_screening else None
#         representation['mtp_info'] = MTPInfoSerializer(mtp_info).data if mtp_info else None
#         representation['recommended_tests'] = RecommendedTestsSerializer(
#             recommended_tests).data if recommended_tests else None
#         representation['procedures_performed'] = ProceduresPerformedSerializer(
#             procedures_performed).data if procedures_performed else None
#         return representation


class GeneratePndtpdfSerializer(serializers.Serializer):
    patient_id = serializers.CharField()
    client_id = serializers.CharField()

    class Meta:
        fields = '__all__'
