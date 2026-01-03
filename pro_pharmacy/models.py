from django.db import models
from django.utils import timezone
from healtho_pro_user.models.universal_models import DeliveryMode
from pro_laboratory.models.patient_models import Patient
from pro_universal_data.models import ULabPaymentModeType, PharmaItemOperationType, TaxType, SupplierType


class Manufacturer(models.Model):
    name = models.CharField(max_length=200)
    supplier_type = models.ForeignKey(SupplierType, on_delete=models.PROTECT, null=True, blank=True)
    mobile_number = models.CharField(max_length=15)
    email = models.EmailField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    area = models.CharField(max_length=200, null=True, blank=True)
    contact_person = models.CharField(max_length=200, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)



class Category(models.Model):
    name = models.CharField(max_length=100)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class StorageConditions(models.Model):
    condition = models.CharField(max_length=200)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.condition


class PharmaItems(models.Model):
    name = models.CharField(max_length=600)
    short_code = models.CharField(max_length=200, null=True, blank=True)
    operation_type = models.ForeignKey(PharmaItemOperationType, on_delete=models.PROTECT, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=0, null=True, blank=True)
    composition = models.CharField(max_length=100, null=True, blank=True)
    tax = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hsn_number = models.CharField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, null=True, blank=True)
    item_image = models.TextField(null=True, blank=True)
    prescription_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class PharmaStock(models.Model):
    item = models.ForeignKey(PharmaItems, on_delete=models.PROTECT)
    description = models.TextField(blank=True, null=True)
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.PROTECT, null=True, blank=True)
    invoice_number = models.CharField(max_length=50, null=True, blank=True)
    packs = models.PositiveIntegerField(default=1,null=True, blank=True)
    free_packs = models.PositiveIntegerField(default=0, null=True, blank=True)
    available_quantity = models.PositiveIntegerField(default=0, null=True, blank=True)
    total_quantity = models.PositiveIntegerField(default=0, null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    batch_number = models.CharField(max_length=50, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    over_all_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tax_type = models.ForeignKey(TaxType, on_delete=models.PROTECT, null=True, blank=True)
    tax = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    over_all_tax = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    storage_conditions = models.ForeignKey(StorageConditions, on_delete=models.PROTECT, blank=True, null=True)
    bar_code = models.CharField(max_length=50, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.item.name}"

    def save(self, *args, **kwargs):
        if self.available_quantity and self.cost:
            self.total_amount = self.available_quantity * self.cost
            self.total_quantity = (self.available_quantity * self.packs) if self.packs > 0 else (self.available_quantity * 1)
        super().save(*args, **kwargs)


class Dosage(models.Model):
    item = models.ForeignKey(PharmaItems, on_delete=models.PROTECT, related_name='dosage')
    dosage_value = models.DecimalField(max_digits=5, decimal_places=2)
    unit = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.dosage_value} {self.unit}"



class PatientMedicine(models.Model):
    stock = models.ForeignKey(PharmaStock, on_delete=models.PROTECT)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=0)
    is_strip= models.BooleanField(default=True)
    name = models.CharField(max_length=200, null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    batch_number = models.CharField(max_length=50, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_after_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.price and self.stock.item.discount:
            self.price_after_discount = self.price - (self.price * self.stock.item.discount/100)
        super().save(*args, **kwargs)


class Orders(models.Model):
    item = models.ForeignKey(PharmaItems, on_delete=models.PROTECT)
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    order_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.name} - {self.item.name} - {self.quantity}"


class Order(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT)
    medicines = models.ManyToManyField(PharmaStock, through='OrderItem')
    delivery_method = models.ForeignKey(DeliveryMode, on_delete=models.PROTECT)
    address = models.TextField(blank=True, null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, null=True, blank=True, default='pending') #need to confirm to make it ForeignkeyField
    added_on = models.DateTimeField(auto_now_add=True)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='items')
    medicine = models.ForeignKey(PharmaStock, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()


class Payment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.ForeignKey(ULabPaymentModeType, on_delete=models.PROTECT)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    added_on = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)



