from rest_framework import serializers

from pro_hospital.models.patient_wise_models import IPRoomBooking
from pro_hospital.models.universal_models import CaseType, GlobalServices, RoomType, Floor, GlobalRoom, \
    DoctorConsultationDetails, GlobalPackages, GlobalPackageLabTest, GlobalPackageConsultation, GlobalPackageService, \
    GlobalPackageRoom, GlobalRoomBeds
from pro_laboratory.models.global_models import LabGlobalTests


class CaseTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseType
        fields = "__all__"


class DoctorConsultationDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorConsultationDetails
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        case_type = instance.case_type

        representation['case_type']={"id": case_type.id, "name":case_type.name} if case_type else None

        return representation


class DoctorConsultationDetailsForPatientsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorConsultationDetails
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        case_type = instance.case_type
        labdoctors=instance.labdoctors

        representation['labdoctors']={"id": labdoctors.id, "name":labdoctors.name} if labdoctors else None

        representation['case_type']={"id": case_type.id, "name":case_type.name} if case_type else None

        return representation

class GlobalServicesSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalServices
        fields = "__all__"
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['department'] = {
            "id": instance.department.id,
            "name": instance.department.name
        } if instance.department else None
        return representation

class RoomTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomType
        fields = "__all__"

class FloorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Floor
        fields = "__all__"

class GlobalRoomBedsSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalRoomBeds
        fields = '__all__'

    def to_representation(self, instance):
        room_booking = IPRoomBooking.objects.filter(patient=instance.patient, booked_bed_number=instance).first()
        admitted_date = None
        if room_booking:
            admitted_date = room_booking.admitted_date
        representation = super().to_representation(instance)
        if instance.patient:
            representation['patient'] = {"id":instance.patient.id,"name":instance.patient.name,"mobile_number":instance.patient.mobile_number,"admitted_date":admitted_date, "mr_no":instance.patient.mr_no, "visit_id": instance.patient.visit_id}
        return representation


class GlobalRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalRoom
        fields = "__all__"

    def to_representation(self, instance):
        beds_data = GlobalRoomBeds.objects.filter(global_room=instance).order_by('bed_number')
        representation = super().to_representation(instance)
        representation['room_type'] = {"id":instance.room_type.id,"name":instance.room_type.name} if instance.room_type else None
        representation['time_category'] = {"id":instance.time_category.id,"name":instance.time_category.name} if instance.time_category else None
        representation['floor'] = {"id":instance.floor.id,"name":instance.floor.name} if instance.floor else None
        representation['beds'] = GlobalRoomBedsSerializer(beds_data, many=True).data

        return representation

class GlobalTestsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabGlobalTests
        fields =['id', 'name', 'price', 'short_code']


class GlobalPackagesSerializer(serializers.ModelSerializer):
    lab_tests = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=False
    )
    consultations = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=False
    )
    services = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=False
    )
    rooms = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=False
    )

    class Meta:
        model = GlobalPackages
        fields = [
            'id', 'name', 'description', 'offer_price', 'total_amount',
            'total_discount', 'is_disc_percentage', 'package_image',
            'is_active', 'lab_tests', 'consultations', 'services', 'rooms'
        ]

    def create(self, validated_data):
        lab_tests_data = validated_data.pop('lab_tests', [])
        consultations_data = validated_data.pop('consultations', [])
        services_data = validated_data.pop('services', [])
        rooms_data = validated_data.pop('rooms', [])

        # Create the package
        package = GlobalPackages.objects.create(**validated_data)

        # Handle lab tests
        for test_data in lab_tests_data:
            test = LabGlobalTests.objects.get(id=test_data['lab_test_id'])
            GlobalPackageLabTest.objects.create(
                package=package,
                lab_test=test,
                quantity=test_data['quantity']
            )

        # Handle consultations
        for consultation_data in consultations_data:
            consultation = DoctorConsultationDetails.objects.get(
                id=consultation_data['consultation_id']
            )
            GlobalPackageConsultation.objects.create(
                package=package,
                consultation=consultation,
                quantity=consultation_data['quantity']
            )

        # Handle services
        for service_data in services_data:
            service = GlobalServices.objects.get(id=service_data['service_id'])
            GlobalPackageService.objects.create(
                package=package,
                service=service,
                quantity=service_data['quantity']
            )

        # Handle rooms
        for room_data in rooms_data:
            room = GlobalRoom.objects.get(id=room_data['room_id'])
            GlobalPackageRoom.objects.create(
                package=package,
                room=room,
                quantity=room_data['quantity']
            )

        return package

    def update(self, instance, validated_data):
        lab_tests_data = validated_data.pop('lab_tests', [])
        consultations_data = validated_data.pop('consultations', [])
        services_data = validated_data.pop('services', [])
        rooms_data = validated_data.pop('rooms', [])

        # Update the package fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update related fields (clear and recreate)
        # instance.labglobalpackagelabtest_set.all().delete()
        # instance.labglobalpackageconsultation_set.all().delete()
        # instance.labglobalpackageservice_set.all().delete()
        # instance.labglobalpackageroom_set.all().delete()

        # Handle lab tests
        if lab_tests_data:
            GlobalPackageLabTest.objects.filter(package=instance).delete()
            for test_data in lab_tests_data:
                test = LabGlobalTests.objects.get(id=test_data['lab_test_id'])
                GlobalPackageLabTest.objects.create(
                    package=instance,
                    lab_test=test,
                    quantity=test_data['quantity']
                )

        # Handle consultations
        if consultations_data:
            GlobalPackageConsultation.objects.filter(package=instance).delete()
            for consultation_data in consultations_data:
                consultation = DoctorConsultationDetails.objects.get(
                    id=consultation_data['consultation_id']
                )
                GlobalPackageConsultation.objects.create(
                    package=instance,
                    consultation=consultation,
                    quantity=consultation_data['quantity']
                )

        # Handle services
        if services_data:
            GlobalPackageService.objects.filter(package=instance).delete()
            for service_data in services_data:
                service = GlobalServices.objects.get(id=service_data['service_id'])
                GlobalPackageService.objects.create(
                    package=instance,
                    service=service,
                    quantity=service_data['quantity']
                )

        # Handle rooms
        if rooms_data:
            GlobalPackageRoom.objects.filter(package=instance).delete()
            for room_data in rooms_data:
                room = GlobalRoom.objects.get(id=room_data['room_id'])
                GlobalPackageRoom.objects.create(
                    package=instance,
                    room=room,
                    quantity=room_data['quantity']
                )

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        package_tests = GlobalPackageLabTest.objects.filter(package=instance)
        representation['lab_tests'] = [{
        **GlobalTestsSerializer(package_test.lab_test).data,  # Serialize the lab_test
        'quantity': package_test.quantity  # Add the quantity field
    } for package_test in package_tests ] if package_tests.exists() else None

        package_services = GlobalPackageService.objects.filter(package=instance)
        representation['services'] = [{
            **GlobalServicesSerializer(package_service.service).data,  # Serialize the lab_test
            'quantity': package_service.quantity  # Add the quantity field
        } for package_service in package_services] if package_services.exists() else None

        package_consultations = GlobalPackageConsultation.objects.filter(package=instance)

        representation['consultations'] = [{
            **DoctorConsultationDetailsForPatientsSerializer(package_consultation.consultation).data,  # Serialize the lab_test
            'quantity': package_consultation.quantity  # Add the quantity field
        } for package_consultation in package_consultations] if package_consultations.exists() else None

        package_rooms = GlobalPackageRoom.objects.filter(package=instance)
        representation['rooms'] = [{
            **GlobalRoomSerializer(package_room.room).data,  # Serialize the lab_test
            'quantity': package_room.quantity  # Add the quantity field
        } for package_room in package_rooms] if package_rooms.exists() else None

        return representation