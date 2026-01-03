from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Q, Sum
from django.forms import model_to_dict
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response

from pro_laboratory.filters import PrivilegeCardsFilter, PrivilegeCardMembershipsFilter
from pro_laboratory.models.global_models import LabStaff, LabDepartments, LabGlobalTests, LabGlobalPackages, \
    LabDiscountType
from pro_laboratory.models.patient_models import LabPatientTests, Patient
from pro_laboratory.models.privilege_card_models import PrivilegeCards, PrivilegeCardFor, PrivilegeCardMemberships, \
    PrivilegeCardsApplicableBenefits, PrivilegeCardsLabTestBenefits, PrivilegeCardMembers, \
    PrivilegeCardsLabDepartmentsBenefits, PrivilegeCardsMembershipApplicableBenefits
from pro_laboratory.serializers.privilege_card_serializers import PrivilegeCardsSerializer, \
    PrivilegeCardMembershipSerializer, PrivilegeCardForSerializer, PrivilegeCardUsageOfPatientSerializer
from pro_universal_data.models import TimeDurationTypes, ULabPatientGender, DepartmentFlowType


class PrivilegeCardForViewSet(viewsets.ModelViewSet):
    queryset = PrivilegeCardFor.objects.all()
    serializer_class = PrivilegeCardForSerializer

    def get_queryset(self):
        queryset = PrivilegeCardFor.objects.all()
        if not queryset.exists():
            instances_data = [
                {"name": "Individual"},
                {"name": "Family"}
            ]
            # Create the instances
            for instance_data in instances_data:
                PrivilegeCardFor.objects.create(**instance_data)
            queryset = PrivilegeCardFor.objects.all()
        return queryset


class PrivilegeCardsViewset(viewsets.ModelViewSet):
    queryset = PrivilegeCards.objects.all()
    serializer_class = PrivilegeCardsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = PrivilegeCardsFilter

    def get_queryset(self):
        queryset = self.queryset
        query = self.request.query_params.get('q', None)
        sort = self.request.query_params.get('sort', None)

        if query:
            search_query = (Q(name__icontains=query) | Q(card_for__name__icontains=query))

            queryset = queryset.filter(search_query)

        if sort:
            if sort in ['added_on', '-added_on', 'card_cost', '-card_cost']:
                queryset = queryset.order_by(sort)

        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        lab_tests_data = request.data.get('lab_tests_data')
        departments_data = request.data.get('departments_data')

        with transaction.atomic():
            benefits_data = validated_data.pop('benefits')
            card = PrivilegeCards.objects.create(**validated_data)

            for benefit_data in benefits_data:
                benefit_data['card'] = card

                PrivilegeCardsApplicableBenefits.objects.create(**benefit_data)

            if lab_tests_data:
                for lab_test_data in lab_tests_data:
                    PrivilegeCardsLabTestBenefits.objects.create(
                        card=card,
                        test=LabGlobalTests.objects.get(pk=lab_test_data['id']),
                        discount=lab_test_data['discount'],
                        is_discount_percentage=lab_test_data['is_discount_percentage'])

            if departments_data:
                for department_data in departments_data:
                    department_benefit, created = PrivilegeCardsLabDepartmentsBenefits.objects.get_or_create(
                        card=card,
                        department=LabDepartments.objects.get(pk=department_data['id'])
                    )

                    department_benefit.discount = department_data['discount']
                    department_benefit.is_discount_percentage = department_data['is_discount_percentage']
                    department_benefit.save()

            serializer = PrivilegeCardsSerializer(card)

            department, created = LabDepartments.objects.get_or_create(name='SERVICES',
                                                                       department_flow_type=DepartmentFlowType.objects.get(pk=3))

            test = LabGlobalTests.objects.create(
                name=card.name,
                price=card.card_cost,
                department=department
            )

            return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        lab_tests_data = request.data.get('lab_tests_data')
        departments_data = request.data.get('departments_data')

        with (transaction.atomic()):
            benefits_data = validated_data.pop('benefits', None)
            self.perform_update(serializer)

            if benefits_data:
                for benefit_data in benefits_data:
                    benefit, created = PrivilegeCardsApplicableBenefits.objects.get_or_create(card=instance,
                                                                                              benefit=benefit_data[
                                                                                                  'benefit'])
                    benefit.free_usages = benefit_data['free_usages']
                    benefit.discount_usages = benefit_data['discount_usages']
                    benefit.discount = benefit_data.get('discount')
                    benefit.is_discount_percentage = benefit_data.get('is_discount_percentage')
                    benefit.save()

            if lab_tests_data:
                for lab_test_data in lab_tests_data:
                    test_benefit, created = PrivilegeCardsLabTestBenefits.objects.get_or_create(
                        card=instance,
                        test=LabGlobalTests.objects.get(pk=lab_test_data['id'])
                    )

                    test_benefit.discount = lab_test_data['discount']
                    test_benefit.is_discount_percentage = lab_test_data['is_discount_percentage']
                    test_benefit.save()

            if departments_data:
                for department_data in departments_data:
                    department_benefit, created = PrivilegeCardsLabDepartmentsBenefits.objects.get_or_create(
                        card=instance,
                        department=LabDepartments.objects.get(pk=department_data['id'])
                    )

                    department_benefit.discount = department_data['discount']
                    department_benefit.is_discount_percentage = department_data['is_discount_percentage']
                    department_benefit.save()

        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PrivilegeCardMembershipViewset(viewsets.ModelViewSet):
    queryset = PrivilegeCardMemberships.objects.all()
    serializer_class = PrivilegeCardMembershipSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = PrivilegeCardMembershipsFilter

    def get_queryset(self):
        queryset = self.queryset
        query = self.request.query_params.get('q', None)
        sort = self.request.query_params.get('sort', None)

        if query:
            search_query = (Q(card_for__name__icontains=query) | Q(pc_no__icontains=query) |
                            Q(card_name__icontains=query) | Q(card_holder__name__icontains=query) | Q(
                        card_holder__mobile_number__icontains=query))

            queryset = queryset.filter(search_query)

        if sort:
            if sort in ['added_on', '-added_on']:
                queryset = queryset.order_by(sort)

        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        card_holder_data = validated_data.pop('card_holder')
        card_holder = PrivilegeCardMembers.objects.create(**card_holder_data)

        membership = PrivilegeCardMemberships.objects.create(**validated_data)
        card = membership.card

        validity_starts_on = datetime.today().date()
        validity_in_days = card.duration_type.no_of_days * card.duration if card.duration else (365 * 100)
        validity_ends_on = validity_starts_on + timedelta(days=validity_in_days)
        count = PrivilegeCardMemberships.objects.all().values('card_holder').distinct().count() + 1
        card_prefix = card.card_prefix or ""
        pc_no_length = card.pc_no_length or 4
        pc_no = f"{card_prefix}{count:0{pc_no_length}d}"

        membership.card_holder = card_holder
        membership.card_name = card.name
        membership.card_cost = card.card_cost
        membership.card_for = card.card_for
        membership.duration = card.duration
        membership.duration_type = card.duration_type
        membership.validity_starts_on = validity_starts_on
        membership.validity_ends_on = validity_ends_on
        membership.pc_no = pc_no
        membership.save()

        card_benefits = PrivilegeCardsApplicableBenefits.objects.filter(card=card)

        for card_benefit in card_benefits:
            PrivilegeCardsMembershipApplicableBenefits.objects.create(membership=membership,
                                                                      benefit=card_benefit.benefit,
                                                                      free_usages=card_benefit.free_usages,
                                                                      availed_free_usages=0,
                                                                      discount_usages=card_benefit.discount_usages,
                                                                      availed_discount_usages=0,
                                                                      discount=card_benefit.discount,
                                                                      is_discount_percentage=card_benefit.is_discount_percentage
                                                                      )
        serializer = PrivilegeCardMembershipSerializer(membership)

        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        card_holder_data = validated_data.pop('card_holder')
        self.perform_update(serializer)

        card_holder = instance.card_holder
        card_holder.profile_image = card_holder_data['profile_image']
        card_holder.name = card_holder_data['name']
        card_holder.dob = card_holder_data['dob']
        card_holder.gender = card_holder_data['gender']
        card_holder.mobile_number = card_holder_data['mobile_number']
        card_holder.email = card_holder_data['email']
        card_holder.save()

        serializer = PrivilegeCardMembershipSerializer(instance)

        return Response(serializer.data)


class PrivilegeCardMembershipRenewalView(generics.CreateAPIView):
    queryset = PrivilegeCardMemberships.objects.all()
    serializer_class = PrivilegeCardMembershipSerializer

    def post(self, request, *args, **kwargs):
        renewal_data = request.data
        card = PrivilegeCards.objects.get(pk=renewal_data['card'])
        card_holder = PrivilegeCardMembers.objects.get(pk=renewal_data['card_holder'])
        lab_staff = LabStaff.objects.get(pk=renewal_data['lab_staff'])

        latest_membership_of_holder = PrivilegeCardMemberships.objects.filter(card_holder=card_holder).last()

        validity_starts_on = latest_membership_of_holder.validity_ends_on + timedelta(days=1)
        validity_in_days = card.duration_type.no_of_days * card.duration
        validity_ends_on = validity_starts_on + timedelta(days=validity_in_days)

        count = PrivilegeCardMemberships.objects.all().values('card_holder').distinct().count() + 1
        card_prefix = card.card_prefix or ""
        pc_no_length = card.pc_no_length or 4
        pc_no = f"{card_prefix}{count:0{pc_no_length}d}"

        membership = PrivilegeCardMemberships.objects.create(
            card=card,
            card_name=card.name,
            pc_no=pc_no,
            card_holder=card_holder,
            card_cost=card.card_cost,
            card_for=card.card_for,
            plan_period_type=card.plan_period_type,
            duration=card.duration,
            duration_type=card.duration_type,
            validity_starts_on=validity_starts_on,
            validity_ends_on=validity_ends_on,
            created_by=lab_staff,
            last_updated_by=lab_staff
        )

        card_benefits = PrivilegeCardsApplicableBenefits.objects.filter(card=card)

        for card_benefit in card_benefits:
            PrivilegeCardsMembershipApplicableBenefits.objects.create(membership=membership,
                                                                      benefit=card_benefit.benefit,
                                                                      free_usages=card_benefit.free_usages,
                                                                      availed_free_usages=0,
                                                                      discount_usages=card_benefit.discount_usages,
                                                                      availed_discount_usages=0,
                                                                      discount=card_benefit.discount,
                                                                      is_discount_percentage=card_benefit.is_discount_percentage
                                                                      )

        serializer = PrivilegeCardMembershipSerializer(membership)

        return Response(serializer.data)


class PrivilegeCardUsageHistoryView(generics.ListAPIView):
    def list(self, request, *args, **kwargs):
        card_holder_id = self.request.query_params.get('card_holder')
        membership_id = self.request.query_params.get('membership')

        if card_holder_id:
            card_holder = PrivilegeCardMembers.objects.get(pk=card_holder_id)
            membership = PrivilegeCardMemberships.objects.filter(card_holder=card_holder).last()
        else:
            card_holder = None
            membership = PrivilegeCardMemberships.objects.get(pk=membership_id)

        patients = Patient.objects.filter(privilege_membership=membership)

        usage_data = PrivilegeCardUsageOfPatientSerializer(patients, many=True).data if patients else []

        return Response({"membership": PrivilegeCardMembershipSerializer(membership).data,
                         "usages": usage_data})


class CalculatePrivilegeCardDiscountView(generics.ListAPIView):
    def list(self, request=None, membership=None, tests=None, privilege_discount=None, add_usage=None, *args, **kwargs):
        try:
            if request:
                membership_id = self.request.query_params.get('membership_id')
                tests = self.request.query_params.get('tests')
                privilege_discount = self.request.query_params.get('privilege_discount')
                test_ids = [test.strip() for test in tests.split(',') if test.strip()]
                tests = LabGlobalTests.objects.filter(id__in=test_ids)
                membership = PrivilegeCardMemberships.objects.get(pk=membership_id)

            else:
                pass

            privilege_card_discount = 0

            if membership:
                test_wise_discounts = []
                if membership.validity_ends_on >= timezone.now().date():
                    department_wise_benefits = PrivilegeCardsLabDepartmentsBenefits.objects.filter(
                        card=membership.card)

                    test_wise_benefits = PrivilegeCardsLabTestBenefits.objects.filter(card=membership.card)

                    tests_discount_benefit = PrivilegeCardsMembershipApplicableBenefits.objects.filter(
                        membership=membership, benefit__name='Lab Tests Discount').first()

                    if privilege_discount == 'free':
                        if tests_discount_benefit.free_usages is None:
                            pass
                        else:
                            free_usages_left = tests_discount_benefit.free_usages - tests_discount_benefit.availed_free_usages

                            if free_usages_left < 1:
                                error_message = f"Privilege Membership has no free usages left!"
                                return Response({"Error": error_message})

                        if not (test_wise_benefits or department_wise_benefits):
                            for test in tests:
                                privilege_card_discount += test.price
                                test_wise_discounts.append({"id": test.id, "discount": test.price})

                        elif test_wise_benefits:
                            for test in tests:
                                obj = test_wise_benefits.filter(test=test).first()
                                if obj:
                                    privilege_card_discount += test.price
                                    test_wise_discounts.append(
                                        {"id": test.id, "discount": test.price})
                                else:
                                    pass

                        elif department_wise_benefits:
                            for test in tests:
                                obj = department_wise_benefits.filter(department=test.department).first()
                                if obj:
                                    privilege_card_discount += test.price
                                    test_wise_discounts.append(
                                        {"id": test.id, "discount": test.price})
                                else:
                                    pass

                        if add_usage:
                            tests_discount_benefit.availed_free_usages += 1
                            tests_discount_benefit.save()

                    elif privilege_discount == 'discount':
                        if tests_discount_benefit.discount_usages is None:
                            pass
                        else:
                            discount_usages_left = tests_discount_benefit.discount_usages - tests_discount_benefit.availed_discount_usages

                            if discount_usages_left < 1:
                                error_message = f"Privilege Membership has no discount usages left!"
                                return Response({"Error": error_message})

                        if not (test_wise_benefits or department_wise_benefits):
                            for test in tests:
                                privilege_card_discount += (test.price / 100 * tests_discount_benefit.discount)
                                test_wise_discounts.append(
                                    {"id": test.id, "discount": (test.price / 100 * tests_discount_benefit.discount)})

                        elif test_wise_benefits:
                            for test in tests:
                                obj = test_wise_benefits.filter(test=test).first()
                                if obj:
                                    privilege_card_discount += (test.price / 100 * obj.discount)
                                    test_wise_discounts.append(
                                        {"id": test.id, "discount": (test.price / 100 * obj.discount)})
                                else:
                                    pass

                        elif department_wise_benefits:
                            for test in tests:
                                obj = department_wise_benefits.filter(department=test.department).first()
                                if obj:
                                    privilege_card_discount += (test.price / 100 * obj.discount)
                                    test_wise_discounts.append(
                                        {"id": test.id, "discount": (test.price / 100 * obj.discount)})
                                else:
                                    pass

                        if add_usage:
                            tests_discount_benefit.availed_discount_usages += 1
                            tests_discount_benefit.save()

                    return Response({"discount": privilege_card_discount,
                                     "test_wise_discounts": test_wise_discounts})


                else:
                    error_message = f"Privilege Membership is Expired! Please check!"
                    return Response({"Error": error_message})


        except Exception as error:
            return Response({"Error": f"{error}"}, status=status.HTTP_400_BAD_REQUEST)
