# from django.db.models import Q
# from rest_framework import viewsets
# from rest_framework.response import Response
#
# from pro_laboratory.models.testPackages_models import LabPatientPackages
# from pro_laboratory.serializers.testPackages_serializers import LabPatientPackagesSerializer, \
#     LabPatientPackagesGetSerializer
# from rest_framework import generics
#
#
# class LabPatientPackagesViewSet(viewsets.ModelViewSet):
#     serializer_class = LabPatientPackagesSerializer
#
#     def get_queryset(self):
#         queryset = LabPatientPackages.objects.all()
#         query = self.request.query_params.get('q', None)
#         sort = self.request.query_params.get('sort', None)
#
#         if query is not None:
#             search_query = (Q(name__icontains=query) | Q(total_amount__icontains=query) | Q(
#                 total_discount__icontains=query) | Q(offer_price__icontains=query))
#             queryset = queryset.filter(search_query)
#
#         if sort == '-added_on':
#             queryset = queryset.order_by('-added_on')
#         if sort == 'added_on':
#             queryset = queryset.order_by('added_on')
#
#         return queryset
#
#     def create(self, request, *args, **kwargs):
#         print(request.data)
#         serializer = self.get_serializer(data=request.data)
#         lab_tests = request.data.get('lab_tests')
#         print(lab_tests)
#         serializer.is_valid(raise_exception=True)
#         validated_data = serializer.validated_data
#         print(validated_data)
#         package = LabPatientPackages.objects.create(**validated_data)
#
#         if lab_tests:
#             for test in lab_tests:
#                 print('in')
#                 package.lab_tests.add(test)
#
#         serializer=LabPatientPackagesSerializer(package)
#
#         return Response(serializer.data)
#
#     def update(self, request, pk=None, *args, **kwargs):
#         instance = self.get_object()
#         instance.id = pk  # Update the ID in case it's passed in the URL
#         serializer = self.get_serializer(instance, data=request.data)
#
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#
#         # Update lab tests if provided
#         lab_tests = request.data.get('lab_tests')
#         if lab_tests:
#             instance.lab_tests.clear()
#             instance.save()
#             for test in lab_tests:
#                 instance.lab_tests.add(test)
#
#         serializer = LabPatientPackagesSerializer(instance)
#         return Response(serializer.data)
#
#
# class LabPatientPackagesListView(generics.ListAPIView):
#     serializer_class = LabPatientPackagesGetSerializer
#
#     def get_queryset(self):
#         queryset = LabPatientPackages.objects.all()
#         query = self.request.query_params.get('q', None)
#         sort = self.request.query_params.get('sort', None)
#
#         if query is not None:
#             search_query = (Q(name__icontains=query) | Q(total_amount__icontains=query) | Q(
#                 total_discount__icontains=query) | Q(offer_price__icontains=query))
#             queryset = queryset.filter(search_query)
#
#         if sort == '-added_on':
#             queryset = queryset.order_by('-added_on')
#         if sort == 'added_on':
#             queryset = queryset.order_by('added_on')
#
#         return queryset
