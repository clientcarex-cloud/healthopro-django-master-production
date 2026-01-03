from rest_framework import serializers
from pro_pharmacy.models import Category, StorageConditions, Dosage, PharmaItems, PharmaStock, Orders, \
    OrderItem, Payment, Order, Manufacturer
from pro_universal_data.serializers import PharmaItemOperationTypeSerializer


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class StorageConditionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageConditions
        fields = '__all__'


class DosageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dosage
        fields = '__all__'


class PharmaItemsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmaItems
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        representation['operation_type'] = PharmaItemOperationTypeSerializer(instance.operation_type).data if instance.operation_type else None

        representation['category'] = CategorySerializer(instance.category).data if instance.category else None

        return representation


class PharmaStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmaStock
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['item'] = {"id": instance.item.id, "name": instance.item.name, "composition": instance.item.composition} if instance.item else None
        representation['tax_type'] = {"id": instance.tax_type.id, "name": instance.tax_type.name} if instance.tax_type else None
        representation['manufacturer'] = {"id":instance.manufacturer.id,"name": instance.manufacturer.name, "supplier_type": instance.manufacturer.supplier_type.name} if instance.manufacturer else None
        return representation

class OrdersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Orders
        fields = ['id', 'item', 'patient', 'quantity', 'order_date']



class ManufacturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manufacturer
        fields = '__all__'


class PharmaStockGetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmaStock
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        item = instance.item
        representation['item'] = {
            "id": getattr(item, 'id', None),
            "name": getattr(item, 'name', None),
            "composition": getattr(item, 'composition', None),
            "short_code": getattr(item, 'short_code', None),
            "quantity": getattr(item, 'quantity', None),
            "operation_type": getattr(item.operation_type, 'name', None) if item and item.operation_type else None,
            "category": getattr(item.category, 'name', None) if item and item.category else None,
            "discount": getattr(item, 'discount', None),
            "tax": getattr(item, 'tax', None)
        }

        manufacturer = instance.manufacturer
        representation['manufacturer'] = {
            "id": getattr(manufacturer, 'id', None),
            "name": getattr(manufacturer, 'name', None),
        }
        return representation

class GeneratePatientPharmacyBillingSerializer(serializers.Serializer):
    patient_id = serializers.CharField()

    class Meta:
        fields = '__all__'
