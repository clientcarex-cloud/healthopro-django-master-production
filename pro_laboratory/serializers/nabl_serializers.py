from rest_framework import serializers
from pro_laboratory.models.labtechnicians_models import LabTechnicians
from pro_laboratory.models.patient_models import Patient, LabPatientTests
from pro_laboratory.models.phlebotomists_models import LabPhlebotomist


class LabPhlebotomistSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabPhlebotomist
        fields = ['id', 'received_by', 'collected_by', 'added_on', 'received_at', 'collected_at']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        received_by_id = representation.get('received_by')
        if received_by_id is not None:
            received_by_name = instance.received_by.name
            representation['received_by'] = received_by_name

        collected_by_id = representation.get('collected_by')
        if collected_by_id is not None:
            collected_by_name = instance.collected_by.name
            representation['collected_by'] = collected_by_name

        return representation


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['id', 'name', 'added_on', 'visit_id']


class LabTechnicianSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTechnicians
        fields = ['id', 'completed_at', 'report_created_by']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        report_created_by_id = representation.get('report_created_by')

        if report_created_by_id is not None:
            report_created_by_name = instance.report_created_by.name
            representation['report_created_by'] = report_created_by_name
        return representation


class LabPatientTestsSerializer(serializers.ModelSerializer):
    phlebotomist = LabPhlebotomistSerializer(required=False)
    patient = PatientSerializer()
    labtechnician = serializers.SerializerMethodField()
    result = serializers.SerializerMethodField()

    class Meta:
        model = LabPatientTests
        fields = ['id', 'name', 'department', 'status_id', 'added_on', 'patient', 'phlebotomist', 'labtechnician',
                  'result']

    def get_labtechnician(self, instance):
        technicians = instance.labtechnician.all()
        if technicians:
            technician = technicians[0]
            technician_serializer = LabTechnicianSerializer(technician)
            return technician_serializer.data
        else:
            return None

    def get_result(self, instance):
        lab_technicians = instance.labtechnician.all()
        if lab_technicians:
            completed_at = lab_technicians[0].completed_at
            try:
                collected_at = instance.phlebotomist.collected_at
            except Exception as error:
                print(error)
                collected_at = None

            if collected_at and completed_at:
                time_diff = completed_at - collected_at
                total_seconds = abs(time_diff.total_seconds())

                # Convert seconds to days, hours, minutes, and seconds
                days = total_seconds // (24 * 3600)
                remaining_seconds = total_seconds % (24 * 3600)
                hours = remaining_seconds // 3600
                remaining_seconds %= 3600
                minutes = remaining_seconds // 60
                remaining_seconds %= 60

                if collected_at > completed_at:
                    return "1 sec"
                if total_seconds <= 10:
                    return "< 10 secs"
                elif total_seconds <= 60:
                    return f"{int(total_seconds)} secs"
                elif total_seconds <= 3600:
                    return f"{int(minutes)} mins {int(remaining_seconds)} secs" if int(remaining_seconds)>0 else  f"{int(minutes)} mins"
                elif total_seconds <= 86400:
                    return f"{int(hours)} hrs {int(minutes)} mins {int(remaining_seconds)} secs" if int(remaining_seconds)>0 else  f"{int(hours)} hrs {int(minutes)} mins"
                else:
                    return f"{int(days)} days {int(hours)} hrs {int(minutes)} mins"
        else:
            return None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        foreign_keys = ['department', 'status_id']
        for fk in foreign_keys:
            fk_id = representation.get(fk)
            if fk_id is not None:
                fk_name = getattr(instance, f'{fk}_name', None)
                if fk_name is None:
                    fk_name = getattr(instance, fk).name
                representation[fk] = fk_name
        return representation
