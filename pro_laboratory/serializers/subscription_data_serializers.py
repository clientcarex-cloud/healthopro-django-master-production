from rest_framework import serializers
from healtho_pro_user.models.business_models import BusinessProfiles
from healtho_pro_user.models.subscription_models import BusinessSubscriptionPlans, BusinessBillCalculationType, \
    OverallBusinessSubscriptionStatus
from healtho_pro_user.serializers.subscription_serializers import OverallBusinessSubscriptionStatusSerializer
from pro_laboratory.models.subscription_data_models import  BusinessSubscriptionPlansPurchased


class BusinessSubscriptionPlansPurchasedSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessSubscriptionPlansPurchased
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        obj=OverallBusinessSubscriptionStatus.objects.get(b_id=instance.b_id)
        subscription_status=OverallBusinessSubscriptionStatusSerializer(obj).data
        representation['subscription_status'] = subscription_status

        created_by = instance.created_by
        last_updated_by = instance.last_updated_by

        if created_by:
            representation['created_by'] = {
                "id": created_by.id,
                "last_updated_by": created_by.full_name
            }

        if last_updated_by:
            representation['last_updated_by'] = {
                "id": last_updated_by.id,
                "last_updated_by": last_updated_by.full_name
            }
        return representation


class BusinessSubscriptionPlansPurchaseFromAdminSerializer(serializers.Serializer):
    b_id = serializers.PrimaryKeyRelatedField(queryset=BusinessProfiles.objects.all())
    calc_type = serializers.PrimaryKeyRelatedField(queryset=BusinessBillCalculationType.objects.all(), required=False)
    plan = serializers.PrimaryKeyRelatedField(queryset=BusinessSubscriptionPlans.objects.all(), required=False)
    plan_start_date = serializers.DateTimeField(required=False, allow_null=True)



