from rest_framework import viewsets
from healtho_pro_user.models.subscription_models import BusinessBillCalculationType, BusinessSubscriptionPlans, \
    OverallBusinessSubscriptionStatus, OverallBusinessSubscriptionPlansPurchased
from healtho_pro_user.serializers.subscription_serializers import BusinessBillCalculationTypeSerializer, \
    BusinessSubscriptionPlansSerializer, OverallBusinessSubscriptionStatusSerializer, \
    OverallBusinessSubscriptionPlansPurchasedSerializer


class BusinessBillCalculationTypeViewSet(viewsets.ModelViewSet):
    queryset = BusinessBillCalculationType.objects.all()
    serializer_class = BusinessBillCalculationTypeSerializer


class BusinessSubscriptionPlansViewSet(viewsets.ModelViewSet):
    queryset = BusinessSubscriptionPlans.objects.all()
    serializer_class = BusinessSubscriptionPlansSerializer


class OverallBusinessSubscriptionStatusViewSet(viewsets.ModelViewSet):
    queryset = OverallBusinessSubscriptionStatus.objects.all()
    serializer_class = OverallBusinessSubscriptionStatusSerializer


class OverallBusinessSubscriptionPlansPurchasedViewSet(viewsets.ModelViewSet):
    queryset = OverallBusinessSubscriptionPlansPurchased.objects.all()
    serializer_class = OverallBusinessSubscriptionPlansPurchasedSerializer


