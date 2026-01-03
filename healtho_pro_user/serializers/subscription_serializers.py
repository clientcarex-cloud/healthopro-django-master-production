from rest_framework import serializers

from healtho_pro_user.models.subscription_models import BusinessBillCalculationType, BusinessSubscriptionPlans, \
    OverallBusinessSubscriptionStatus, OverallBusinessSubscriptionPlansPurchased, BusinessSubscriptionType


class BusinessSubscriptionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessSubscriptionType
        fields = '__all__'


class BusinessBillCalculationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessBillCalculationType
        fields = '__all__'


class BusinessSubscriptionPlansSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessSubscriptionPlans
        fields = '__all__'


class OverallBusinessSubscriptionStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = OverallBusinessSubscriptionStatus
        fields = '__all__'


class OverallBusinessSubscriptionPlansPurchasedSerializer(serializers.ModelSerializer):
    class Meta:
        model = OverallBusinessSubscriptionPlansPurchased
        fields = '__all__'
