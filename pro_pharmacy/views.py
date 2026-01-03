import re
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from django.core import paginator
from django.db.models import Q, Sum, F
from django.http import HttpResponse
from rest_framework import viewsets, status, generics
from rest_framework.response import Response
from unicodedata import category

from healtho_pro_user.models.business_models import BusinessProfiles
from healtho_pro_user.models.users_models import Client
from pro_laboratory.models.client_based_settings_models import PharmacyPricingConfig
from pro_laboratory.models.global_models import LabStaff
from pro_laboratory.models.patient_models import Patient, LabPatientReceipts, LabPatientInvoice
from pro_laboratory.models.universal_models import PrintTemplate, PrintDataTemplate
from pro_universal_data.models import PharmaItemOperationType, Tag, PrintTemplateType, TaxType
from pro_pharmacy.models import Category, StorageConditions, Dosage, PharmaItems, PharmaStock, Orders, Manufacturer, \
    PatientMedicine
from pro_pharmacy.serializers import CategorySerializer, StorageConditionsSerializer, DosageSerializer, \
    PharmaItemsSerializer, PharmaStockSerializer, OrdersSerializer, ManufacturerSerializer, PharmaStockGetSerializer, \
    GeneratePatientPharmacyBillingSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class StorageConditionsViewSet(viewsets.ModelViewSet):
    queryset = StorageConditions.objects.all()
    serializer_class = StorageConditionsSerializer


class DosageViewSet(viewsets.ModelViewSet):
    queryset = Dosage.objects.all()
    serializer_class = DosageSerializer


class PharmaStockViewSet(viewsets.ModelViewSet):
    queryset = PharmaStock.objects.all()
    serializer_class = PharmaStockSerializer

    def list(self, request, *args, **kwargs):
        manufacturer_id = request.query_params.get("manufacturer")
        sort = request.query_params.get("sort",'')
        date = request.query_params.get("date")
        date_range = request.query_params.get("date_range")


        if manufacturer_id:
            queryset = self.queryset.filter(manufacturer_id=manufacturer_id)
        else:
            queryset = self.queryset

        if date:
            try:
                date_obj = datetime.strptime(date, "%Y-%m-%d").date()
                queryset = queryset.filter(added_on__date=date_obj)
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        if date_range:
            try:
                start_date, end_date = date_range.split(",")
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                queryset = queryset.filter(added_on__date__range=(start_date, end_date))
            except ValueError:
                return Response({"error": "Invalid date_range format. Use YYYY-MM-DD,YYYY-MM-DD."},
                                status=status.HTTP_400_BAD_REQUEST)

        if sort == '-added_on':
            queryset = queryset.order_by('-added_on')
        elif sort == 'added_on':
            queryset = queryset.order_by('added_on')

        grouped_data = defaultdict(list)

        for stock in queryset:
            serializer = self.get_serializer(stock)
            grouped_data[stock.invoice_number].append(serializer.data)

        response_data = [
            {"invoice_number": invoice, "stock": stocks}
            for invoice, stocks in grouped_data.items()
        ]
        paginated_data = self.paginate_queryset(response_data)
        return self.get_paginated_response(paginated_data)

    def create(self, request, *args, **kwargs):
        data = request.data

        manufacturer_id = data.get("manufacturer")
        invoice_number = data.get("invoice_number")
        over_all_discount = data.get('over_all_discount')
        over_all_tax = data.get('over_all_tax')
        stock_items = data.get("stock", [])

        if not manufacturer_id or not invoice_number:
            return Response(
                {"error": "Manufacturer and Invoice number are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        existing_stocks = PharmaStock.objects.filter(
            manufacturer_id=manufacturer_id,
            invoice_number=invoice_number
        )
        existing_stocks.delete()

        created_stock_objects = []
        for stock_item in stock_items:
            item_id = stock_item.get("item")
            quantity = stock_item.get("quantity", 0)
            price = stock_item.get("price", 0)
            expiry_date = stock_item.get("expiry_date")
            batch_number = stock_item.get("batch_number")
            tax_type = stock_item.get('tax_type')
            tax_percentage = stock_item.get('tax')
            discount = stock_item.get('discount')
            cost = stock_item.get('cost')
            packs = stock_item.get('packs')

            if tax_type is not None:
                tax_type = TaxType.objects.get(id=tax_type)
            else:
                tax_type = None

            try:
                pharma_item = PharmaItems.objects.get(id=item_id)
            except PharmaItems.DoesNotExist:
                return Response(
                    {"error": f"PharmaItem with id {item_id} does not exist."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            pharma_stock = PharmaStock.objects.create(
                item=pharma_item,
                manufacturer_id=manufacturer_id,
                invoice_number=invoice_number,
                available_quantity=quantity,
                price=price,
                tax_type=tax_type,
                tax=tax_percentage,
                discount=discount,
                expiry_date=expiry_date,
                batch_number=batch_number,
                cost=cost,
                packs=packs,
                over_all_discount=over_all_discount,
                over_all_tax=over_all_tax
            )
            pharma_stock.total_amount = pharma_stock.available_quantity * pharma_stock.price
            pharma_stock.save()
            created_stock_objects.append(pharma_stock)

            pharma_item.price = pharma_stock.price
            pharma_item.quantity = pharma_stock.available_quantity
            pharma_item.save()

        serializer = self.get_serializer(created_stock_objects, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OrdersViewSet(viewsets.ModelViewSet):
    queryset = Orders.objects.all()
    serializer_class = OrdersSerializer


class PharmaItemsViewSet(viewsets.ModelViewSet):
    queryset = PharmaItems.objects.all()
    serializer_class = PharmaItemsSerializer

    def get_queryset(self):
        queryset = PharmaItems.objects.all()
        query = self.request.query_params.get('q', None)
        category = self.request.query_params.get('category', None)
        operation_type = self.request.query_params.get('operation_type', None)
        sort = self.request.query_params.get('sort', None)
        is_active = self.request.query_params.get('is_active', None)

        if is_active == 'true':
            queryset = queryset.filter(is_active=True)
        if operation_type:
            queryset = queryset.filter(operation_type__id=operation_type)

        if category:
            queryset = queryset.filter(category__id=category)

        if query is not None:
            search_query = (Q(name__icontains=query) | Q(short_code__icontains=query) | Q(composition__icontains=query))
            queryset = queryset.filter(search_query)

        if sort == '-name':
            queryset = queryset.order_by('-category__name', '-name')
        if sort == 'name':
            queryset = queryset.order_by('category__name', 'name')

        return queryset

    def create(self, request, *args, **kwargs):
            if isinstance(request.data, list):
                data = request.data
            else:
                data = [request.data]

            processed_data = []
            for item in data:
                operation_type = item.get("operation_type")
                category_value = item.get("category")

                if operation_type:
                    if isinstance(operation_type, int):
                        operation_type = PharmaItemOperationType.objects.filter(id=operation_type).first()
                    elif isinstance(operation_type, str):
                        operation_type = PharmaItemOperationType.objects.filter(name=operation_type).first()

                    item["operation_type"] = operation_type.id
                else:
                    item["operation_type"] = None

                if category_value:
                    if isinstance(category_value, int):
                        category, _ = Category.objects.get_or_create(id=category_value)
                    else:
                        category, _ = Category.objects.get_or_create(name=category_value)
                    item["category"] = category.id
                else:
                    item["category"] = None

                processed_data.append(item)

            serializer = self.get_serializer(data=processed_data, many=True)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)




class ManufacturerViewSet(viewsets.ModelViewSet):
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer

class PharmaStockGetAPIView(generics.ListAPIView):
    serializer_class = PharmaStockGetSerializer

    def get_queryset(self):
        queryset = PharmaStock.objects.all()
        sort = self.request.query_params.get("sort", '')
        query = self.request.query_params.get('q')
        date = self.request.query_params.get("date")
        date_range = self.request.query_params.get("date_range")
        manufacturer_id = self.request.query_params.get('manufacturer')
        category_id = self.request.query_params.get('category')
        operation_type_id = self.request.query_params.get('operation_type')


        if manufacturer_id:
            queryset = queryset.filter(manufacturer__id=manufacturer_id)
        if category_id:
            queryset = queryset.filter(item__category__id=category_id)
        if operation_type_id:
            queryset = queryset.filter(item__operation_type__id=operation_type_id)

        if date:
            try:
                date_obj = datetime.strptime(date, "%Y-%m-%d").date()
                queryset = queryset.filter(added_on__date=date_obj)
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        if date_range:
            try:
                start_date, end_date = date_range.split(",")
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                queryset = queryset.filter(added_on__date__range=(start_date, end_date))
            except ValueError:
                return Response({"error": "Invalid date_range format. Use YYYY-MM-DD,YYYY-MM-DD."},
                                status=status.HTTP_400_BAD_REQUEST)
        queryset = queryset.order_by('item__name')

        if sort == '-added_on':
            queryset = queryset.order_by('-added_on')
        elif sort == 'added_on':
            queryset = queryset.order_by('added_on')

        if query:
            # Find the composition of the queried medicine
            composition = PharmaStock.objects.filter(item__name__icontains=query).values_list('item__composition',
                                                                                              flat=True).first()
            if composition:
                # Include all items with the same composition
                queryset = PharmaStock.objects.filter(item__composition=composition)
            else:
                # If no composition found, filter by the initial search query
                search_query = (Q(item__name__icontains=query) | Q(item__composition__icontains=query) | Q(
                    item__short_code__icontains=query))
                queryset = queryset.filter(search_query)
        return queryset



class GeneratePatientPharmacyBillingViewSet(viewsets.ModelViewSet):
    serializer_class = GeneratePatientPharmacyBillingSerializer

    def get_queryset(self):
        return []

    def create(self, request=None, patient_id=None, client_id=None,printed_by_id=None,receipt_id=None, *args, **kwargs):
        if request:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer_data = serializer.validated_data
            patient_id = serializer_data.get('patient_id')
            printed_by_id = serializer_data.get('printed_by_id')
            receipt_id= serializer_data.get('receipt_id')
            client_id = request.client.id
            print(patient_id, client_id)
        else:
            print(patient_id, client_id)

        try:
            patient = Patient.objects.get(pk=patient_id)
            client = Client.objects.get(pk=client_id)
            bProfile = BusinessProfiles.objects.filter(organization_name=client.name).first()
            medicines = PatientMedicine.objects.filter(patient=patient)
            template_type = PrintTemplateType.objects.get(name='Pharmacy Bill')
            print_template = PrintTemplate.objects.get(print_template_type=template_type, is_default=True)
            template = PrintDataTemplate.objects.get(print_template=print_template)
            printed_by = LabStaff.objects.get(pk=printed_by_id) if printed_by_id else ""
            labpatientinvoice = LabPatientInvoice.objects.filter(patient=patient).first()
            receipt = LabPatientReceipts.objects.filter(invoiceid=labpatientinvoice).first()
            concerned_receipts = LabPatientReceipts.objects.filter(id=receipt.id)

            report_printed_on = datetime.now().strftime('%d-%m-%y %I:%M %p')

            details = {
                'patient': patient,
                'bProfile': bProfile,
                'medicines': medicines,
                "printed_by": printed_by,
                "receipt": receipt,
                "report_printed_on": report_printed_on
            }

        except Exception as error:
            print(error)
            return Response(f"Error fetching details: {error}", status=400)

            # print(f"details : {details}")

        search_pattern = r"\{(.*?)\}"
        expression_pattern = r"\[\[(.*?)\]\]"

        # Dictionary to hold totals for tags dynamically
        tag_totals = {}

        def accumulate_tag_totals(tag_name, value):
            if tag_name in tag_totals:
                tag_totals[tag_name] += value
            else:
                tag_totals[tag_name] = value

        # Function to replace tags found by regex search
        def replace_tag(match):
            tag_name = match.group(1)  # Capture the content without braces

            try:
                # Fetch the tag by its name
                tag = Tag.objects.get(tag_name='{' + tag_name + '}')

                # Check if the tag requires fetching a collection of items
                if tag.is_collection:
                    if tag_name == 'MedicineSNo':
                        medicines_details = details['medicines']
                        serial_no_data = []
                        counter = 1

                        if medicines_details:
                            for medicine in medicines_details:
                                serial_no_data.append(f"{counter}")
                                counter += 1
                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' if isinstance(x,
                                                                                            str) else f'<p style="margin: 3px 5px;"></p>'
                                       for x in serial_no_data)

                    if tag_name == 'MedicineNames':
                        medicines_details = details['medicines']
                        medicine_names_data = []

                        if medicines_details:
                            for medicine in medicines_details:
                                medicine_names_data.append(f"<strong>{medicine.stock.item.name}</strong>")
                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in medicine_names_data)

                    if tag_name == 'MedicineBatchNos':
                        medicines_details = details['medicines']
                        medicine_names_data = []

                        if medicines_details:
                            for medicine in medicines_details:
                                medicine_names_data.append(f"<strong>{medicine.batch_number}</strong>")

                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in medicine_names_data)

                    if tag_name == 'MedicineExpiryDate':
                        medicines_details = details['medicines']
                        medicine_names_data = []

                        if medicines_details:
                            for medicine in medicines_details:
                                medicine_names_data.append(f"<strong>{medicine.expiry_date}</strong>")
                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in medicine_names_data)

                    if tag_name == 'MedicineTotalPrice':
                        medicines_details = details['medicines']
                        medicine_names_data = []
                        if medicines_details:
                            for medicine in medicines_details:
                                total_amount = medicine.price * medicine.quantity if medicine.is_strip == True else (
                                        medicine.quantity * (medicine.price / medicine.stock.packs))
                                pharma_item_obj = PharmaItems.objects.get(id=medicine.stock.item.id)
                                if pharma_item_obj:
                                    discount_percentage = pharma_item_obj.discount
                                    discount_amount = total_amount - (
                                            (discount_percentage / 100) * total_amount)
                                else:
                                    pharma_pricing = PharmacyPricingConfig.objects.first()
                                    discount_amount = total_amount - (
                                            (pharma_pricing.discount_percentage / 100) * total_amount)
                                medicine_names_data.append(f"<strong>{discount_amount}</strong>")

                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in medicine_names_data)

                    if tag_name == 'MedicineTotalTaxAmount':
                        medicines_details = details['medicines']
                        total_taxable_price = Decimal(0)

                        if medicines_details:
                            for medicine in medicines_details:
                                total_amount = (
                                    Decimal(medicine.price) * Decimal(medicine.quantity)
                                    if medicine.is_strip
                                    else Decimal(medicine.quantity) * (
                                                Decimal(medicine.price) / Decimal(medicine.stock.packs))
                                )
                                pharma_item_obj = PharmaItems.objects.get(id=medicine.stock.item.id)
                                if pharma_item_obj:
                                    tax_percentage = Decimal(pharma_item_obj.tax) if pharma_item_obj.tax else Decimal(0)
                                    rate = total_amount - (
                                                (Decimal(pharma_item_obj.discount) / Decimal(100)) * total_amount)
                                else:
                                    pharma_pricing = PharmacyPricingConfig.objects.first()
                                    tax_percentage = Decimal(pharma_pricing.tax_percentage)
                                    rate = total_amount - ((Decimal(pharma_pricing.discount_percentage) / Decimal(
                                        100)) * total_amount)
                                taxable_price = (tax_percentage / Decimal(100)) * rate
                                total_taxable_price += taxable_price
                        return f"<p style='margin: 3px 5px;'><strong>{total_taxable_price}</strong></p>"
                    if tag_name == 'MedicineQuantity':
                        medicines_details = details['medicines']
                        medicine_names_data = []

                        if medicines_details:
                            for medicine in medicines_details:
                                medicine_names_data.append(f"<strong>{medicine.quantity}</strong>")

                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in medicine_names_data)

                    if tag_name == 'MedicineMRPPrice':
                        medicines_details = details['medicines']
                        medicine_names_data = []

                        if medicines_details:
                            for medicine in medicines_details:
                                medicine_names_data.append(
                                    f"<strong>{medicine.price}</strong>")

                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in medicine_names_data)

                    if tag_name == 'MedicineDiscountAmount':
                        medicines_details = details['medicines']
                        medicine_names_data = []

                        if medicines_details:
                            for medicine in medicines_details:
                                medicine_names_data.append(
                                    f"<strong>{medicine.price * (medicine.stock.item.discount/100)}</strong>")

                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in medicine_names_data)

                    if tag_name == 'MedicineRate':
                        medicines_details = details['medicines']
                        medicine_names_data = []

                        if medicines_details:
                            for medicine in medicines_details:
                                medicine_names_data.append(
                                    f"<strong>{medicine.price - (medicine.price * (medicine.stock.item.discount/100))}</strong>")

                        return "".join(f'<p style="margin: 3px 5px;">{x}</p>' for x in medicine_names_data)

                    if tag_name == 'MedicinesTotalMRPAmount':
                        medicines_details = details['medicines']
                        total_mrp_price = 0

                        if medicines_details:
                            for medicine in medicines_details:
                                total_mrp_price += medicine.price

                        return f"<p style='margin: 3px 5px;'><strong>{total_mrp_price}</strong></p>"

                    if tag_name == 'MedicinesTotalDiscountAmount':
                        medicines_details = details['medicines']
                        total_discount_amount = 0

                        if medicines_details:
                            for medicine in medicines_details:
                                discount_amount = medicine.price * (medicine.stock.item.discount / 100)
                                total_discount_amount += discount_amount
                        return "".join(f'<p style="margin: 3px 5px;">{total_discount_amount}</p>')

                    if tag_name == 'MedicinesTotalNetAmount':
                        medicines_details = details['medicines']
                        total_net_amount = 0

                        if medicines_details:
                            for medicine in medicines_details:
                                rate = medicine.price - (medicine.price * (medicine.stock.item.discount/100))
                                total_net_amount += rate

                        return "".join(f'<p style="margin: 3px 5px;">{total_net_amount}</p>')

                    if tag_name == "RecReceiptNo":
                        receipt_ids = [
                            obj.Receipt_id
                            for obj in concerned_receipts
                            for _ in range(obj.payments.count())
                        ]
                        return "".join(f'<p style="margin: 3px 0px;">{receipt_id}</p>' for receipt_id in
                                       receipt_ids)

                    if tag_name == "RecPaymentMode":
                        related_objects = concerned_receipts

                        payment_modes = [payment.pay_mode.name for obj in related_objects for payment in
                                         obj.payments.all()]
                        return "".join(f'<p style="margin: 3px 0px;">{mode}</p>' for mode in payment_modes)

                    if tag_name == "RecPaymentDate":
                        related_objects = concerned_receipts

                        payment_dates = [
                            obj.added_on.strftime('%d-%m-%y, %I:%M %p')
                            for obj in related_objects
                            for _ in range(obj.payments.count())
                        ]
                        return "".join(f'<p style="margin: 3px 0px;">{date}</p>' for date in payment_dates)

                    if tag_name == "RecPaymentRemark":
                        related_objects = concerned_receipts

                        payment_remarks = [
                            obj.remarks
                            for obj in related_objects
                            for _ in range(obj.payments.count())
                        ]
                        print(payment_remarks)
                        return "".join(
                            f'<p style="margin: 3px 0px;">{payment_remark if payment_remark else "-"}</p>' for payment_remark in
                            payment_remarks)
                    if tag_name == "RecPaymentAmount":
                        related_objects = concerned_receipts

                        payment_amounts = [
                            sum(payment.paid_amount for payment in obj.payments.filter(pay_mode=mode))
                            for obj in related_objects
                            for mode in obj.payments.values_list('pay_mode', flat=True).distinct()
                        ]
                        return "".join(
                            f'<p style="margin: 3px 0px;">{amount}</p>' for amount in payment_amounts)


                else:
                    if tag.tag_formula:
                        try:
                            tag_value = str(eval(tag.tag_formula, {'details': details}))
                            return tag_value
                        except Exception as eval_error:
                            print(f"{tag_name} - Error in formula evaluation: {eval_error}")
                            return " "  # If null
                    else:
                        # If no formula, return a placeholder or a default value
                        return f"No formula for {tag_name}"

            except Tag.DoesNotExist:
                # If the tag doesn't exist, return a placeholder indicating so
                return f"{tag_name} not found!"

                # New function to evaluate and replace expressions

        def evaluate_expression(match):
            expression = match.group(1)  # Capture the content without double brackets
            try:
                # Ensure you sanitize or validate the expression if using eval() directly poses a security risk
                result = str(eval(expression, {'__builtins__': None}, {'details': details}))
                return result
            except Exception as eval_error:
                print(f"Error in expression evaluation: {eval_error}")
                return "[Error]"  # Placeholder for any evaluation error

        html_content = template.data
        template_content = html_content
        intermediate_content = re.sub(search_pattern, replace_tag, template_content)

        modified_content = re.sub(expression_pattern, evaluate_expression, intermediate_content)

        def replace_total(match):
            tag_name = match.group(1)  # Extract the tag name
            total_value = tag_totals.get(tag_name, 0)  # Get the total value from tag_totals
            return str(total_value)  # Return the total value as a string

        # Use the regular expression to find and replace total placeholders
        final_content = re.sub(expression_pattern, replace_total, modified_content)

        return Response({'html_content': final_content})
        # return HttpResponse(final_content)
        # return render(request, 'print_invoice.html', {'content': final_content})

