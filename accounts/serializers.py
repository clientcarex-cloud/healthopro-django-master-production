from rest_framework import serializers
from .models import LabExpenses, LabIncomes, LabExpenseType, LabPaidToType, LabIncomeType, \
    LabIncomeFromAccount


class LabExpenseTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabExpenseType
        fields = '__all__'

class LabPaidToTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabPaidToType
        fields = '__all__'


class LabIncomeFromAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabIncomeFromAccount
        fields = '__all__'


class LabExpensesSerializer(serializers.ModelSerializer):

    class Meta:
        model = LabExpenses
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['expense_type'] = {"id": instance.expense_type.id,
                                         "name": instance.expense_type.name} if instance.expense_type else None
        representation['paid_to'] = {"id": instance.paid_to.id,
                                     "name": instance.paid_to.name} if instance.paid_to else None
        representation['pay_mode'] = {"id": instance.pay_mode.id,
                                      "name": instance.pay_mode.name} if instance.pay_mode else None

        representation['account_to'] = {"id": instance.account_to.id,
                                        "name": instance.account_to.name} if instance.account_to else None
        representation['authorized_by'] = instance.authorized_by.name  if instance.authorized_by else None
        return representation


class LabIncomesSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabIncomes
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['income_type'] = {"id": instance.income_type.id, "name": instance.income_type.name} if instance.income_type else None
        representation['pay_mode'] = {"id": instance.pay_mode.id, "name": instance.pay_mode.name} if instance.pay_mode else None
        representation['account_to'] = {"id": instance.account_to.id, "name": instance.account_to.name} if instance.account_to else None
        representation['received_from'] = {"id": instance.received_from.id, "name": instance.received_from.name} if instance.received_from else None
        representation['authorized_by'] = instance.authorized_by.name if instance.authorized_by else None
        return representation


class LabIncomeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabIncomeType
        fields = '__all__'