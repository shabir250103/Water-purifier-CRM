# Complete Updated serializers.py
# All existing code + fixes for customer_name, customer_code

from datetime import datetime, date
from decimal import Decimal
from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from django.db.models import Sum
from .models import (
    Company, Customer, EnquiryItem, Product, Inquiry, InquiryLine, 
    InquiryActivity, Quotation, QuotationLine, SalesOrder, SalesOrderLine, 
    Delivery, DeliveryLine, Invoice, InvoiceLine, DocType, DocFlowLink, 
    Payment, ServiceCall, Technician, TechnicianSchedule, Equipment, 
    AMCContract, Lead,  ServiceCallTechnician,
    ServiceCallResolution,
    ServiceCallExpense,
    ServiceCallActivity,
    AMCContractEquipment,
)

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    """Used for both normal user and admin login."""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get("username")
        password = data.get("password")

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError("Invalid username or password.")
        else:
            raise serializers.ValidationError("Both username and password are required.")

        data["user"] = user
        return data


class CreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "role"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"


class CustomerSerializer(serializers.ModelSerializer):
    """
    Serializer for Customer model.
    Includes dob field in YYYY-MM-DD format
    Frontend sends date in YYYY-MM-DD format from type=date
    API returns date in YYYY-MM-DD format
    """
    outstanding = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            "id",
            "code",
            "name",
            "contact_person",
            "phone",
            "email",
            "gstin",
            "credit",
            "outstanding",
            "dob",
            "door_no",
            "street",
            "area",
            "city",
            "pincode",
            "customer_type",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]

    def get_outstanding(self, obj):
        # 1. Get stored outstanding (Imported Opening Balance)
        stored_outstanding = Decimal(0)
        if obj.outstanding:
            try:
                # Remove currency symbol and commas to convert to decimal
                cleaned_val = str(obj.outstanding).replace("₹", "").replace(",", "").strip()
                if cleaned_val:
                    stored_outstanding = Decimal(cleaned_val)
            except Exception:
                stored_outstanding = Decimal(0)

        # 2. Calculate total invoiced amount
        total_invoiced = Invoice.objects.filter(
            customer=obj,
            is_active=True,
            canceled=False
        ).exclude(status='Canceled').aggregate(
            total=Sum('grand_total')
        )['total'] or Decimal(0)

        # 3. Calculate total paid amount via invoices
        total_paid = Payment.objects.filter(
            invoice__customer=obj,
            is_active=True,
            invoice__is_active=True,
            invoice__canceled=False
        ).exclude(invoice__status='Canceled').aggregate(
            total=Sum('amount')
        )['total'] or Decimal(0)

        # Total outstanding = Stored (Opening) + Invoiced - Paid
        outstanding = stored_outstanding + total_invoiced - total_paid
        return f"₹{outstanding:,.2f}"


class ProductSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ["id", "created_at", "deleted_at", "is_active", "product_name"]

    def get_product_name(self, obj):
        parts = [obj.brand, obj.series, obj.model_number]
        return " ".join(filter(None, parts))


class SafeDateField(serializers.DateField):
    """Safely converts timezone-aware datetime to date."""

    def to_representation(self, value):
        if isinstance(value, datetime):
            value = value.date()
        return super().to_representation(value)

    def to_internal_value(self, value):
        if isinstance(value, str):
            try:
                if "T" in value or "Z" in value:
                    value = datetime.fromisoformat(value.replace("Z", "+00:00")).date()
            except Exception:
                pass
        elif isinstance(value, datetime):
            value = value.date()
        return super().to_internal_value(value)


class InquiryLineSerializer(serializers.ModelSerializer):
    """Serializer for Inquiry Line Items"""
    
    product_detail = serializers.SerializerMethodField(read_only=True)
    product_name = serializers.SerializerMethodField(read_only=True)
    price_with_gst = serializers.SerializerMethodField(read_only=True)
    
    doc_entry = serializers.PrimaryKeyRelatedField(
        queryset=Inquiry.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = InquiryLine
        fields = [
            "id",
            "line_num",
            "doc_entry",
            "item",
            "uom",
            "quantity",
            "open_qty",
            "price",
            "discount_percent",
            "tax_percent",
            "line_total",
            "remarks",
            "product_detail",
            "product_name",
            "price_with_gst",
        ]
        read_only_fields = ["id", "product_name", "price_with_gst"]

    def get_product_detail(self, obj):
        """Return readable product info."""
        if not obj.item:
            return None
        p = obj.item
        return {
            "id": p.id,
            "product_code": p.product_code,
            "brand": p.brand or "",
            "series": p.series or "",
            "model_number": p.model_number or "",
            "price": float(p.price or 0),
            "gst_rate": float(p.gst_rate or 0),
        }
    
    def get_product_name(self, obj):
        """Return formatted product name (brand + series + model)."""
        if not obj.item:
            return ""
        p = obj.item
        parts = [p.brand, p.series, p.model_number]
        return " ".join(filter(None, parts))
    
    def get_price_with_gst(self, obj):
        """Calculate and return price including GST."""
        if not obj.item or not obj.price:
            return float(obj.price or 0)
        
        gst_rate = float(obj.item.gst_rate or 0)
        base_price = float(obj.price or 0)
        return round(base_price * (1 + gst_rate / 100), 2)


class InquiryActivitySerializer(serializers.ModelSerializer):
    """Serializer for Inquiry Activities"""
    
    inquiry = serializers.PrimaryKeyRelatedField(
        queryset=Inquiry.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = InquiryActivity
        fields = [
            "id",
            "inquiry",
            "activity_id",
            "activity_date",
            "next_followup",
            "activity_type",
            "details",
            "created_at",
        ]
        read_only_fields = ["id", "activity_id", "created_at"]

    def validate(self, data):
        """Validate activity data"""
        if data.get("activity_date"):
            today = timezone.now().date()
            if data["activity_date"] > today:
                raise serializers.ValidationError(
                    {"activity_date": "Activity date cannot be in the future."}
                )
        return data

    def create(self, validated_data):
        """Auto-generate activity_id if not provided"""
        if not validated_data.get("activity_id"):
            last = InquiryActivity.objects.order_by("-id").first()
            new_id = f"ACT-{1000 + (last.id if last else 0) + 1}"
            validated_data["activity_id"] = new_id
        return super().create(validated_data)


class InquirySerializer(serializers.ModelSerializer):
    """
    Complete Inquiry Serializer
    Handles header info with nested items and activities
    ✅ FIXED: Includes customer_name and customer_code read-only fields
    """
    
    items = InquiryLineSerializer(many=True, required=False)
    activities = InquiryActivitySerializer(many=True, required=False)
    
    # ✅ FIX: ADD THESE READ-ONLY FIELDS FOR CUSTOMER DATA PERSISTENCE
    customer_name = serializers.CharField(
        source="customer.name",
        read_only=True,
        allow_blank=True
    )
    customer_code = serializers.CharField(
        source="customer.code",
        read_only=True,
        allow_blank=True
    )
    
    # ✅ UPDATE: Make customer_id write-only for API updates
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.filter(is_active=True),
        source="customer",
        write_only=True,
        required=False,
        allow_null=True
    )
    
    next_followup = SafeDateField(allow_null=True, required=False)
    doc_date = SafeDateField(allow_null=True, required=False)

    class Meta:
        model = Inquiry
        fields = [
            "id",
            "doc_num",
            "customer",                # READ-ONLY nested customer object
            "customer_id",             # WRITE-ONLY for updates
            "customer_name",           # ✅ NEW: READ-ONLY extracted from customer.name
            "customer_code",           # ✅ NEW: READ-ONLY extracted from customer.code
            "source",
            "status",
            "executivename",
            "doc_date",
            "next_followup",
            "remarks",
            "items",
            "activities",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "doc_num",
            "customer",
            "customer_name",           # ✅ NEW: READ-ONLY
            "customer_code",           # ✅ NEW: READ-ONLY
            "created_at",
            "updated_at",
        ]

    def validate_source(self, value):
        """Validate source field"""
        valid_sources = [choice[0] for choice in Inquiry.SOURCE_CHOICES]
        if value and value not in valid_sources:
            raise serializers.ValidationError(
                f"Invalid source. Must be one of {', '.join(valid_sources)}"
            )
        return value

    def validate_status(self, value):
        """Validate status field"""
        valid_statuses = [choice[0] for choice in Inquiry.STATUS_CHOICES]
        if value and value not in valid_statuses:
            raise serializers.ValidationError(
                f"Invalid status. Must be one of {', '.join(valid_statuses)}"
            )
        return value

    def create(self, validated_data):
        """Create inquiry with items and activities"""
        items_data = validated_data.pop("items", [])
        activities_data = validated_data.pop("activities", [])
        
        inquiry = Inquiry.objects.create(**validated_data)
        
        for idx, item_data in enumerate(items_data):
            item_data["line_num"] = idx + 1
            InquiryLine.objects.create(doc_entry=inquiry, **item_data)
        
        for activity_data in activities_data:
            InquiryActivity.objects.create(inquiry=inquiry, **activity_data)
        
        return inquiry

    def update(self, instance, validated_data):
        """Update inquiry with items and activities"""
        items_data = validated_data.pop("items", None)
        activities_data = validated_data.pop("activities", None)
        
        # Update inquiry header fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update items if provided
        if items_data is not None:
            instance.items.all().delete()
            for idx, item_data in enumerate(items_data):
                item_data["line_num"] = idx + 1
                InquiryLine.objects.create(doc_entry=instance, **item_data)
        
        # Update activities if provided
        if activities_data is not None:
            instance.activities.all().delete()
            for activity_data in activities_data:
                InquiryActivity.objects.create(inquiry=instance, **activity_data)
        
        return instance


class ProductDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "product_code", "brand", "series", "model_number", "price", "hsn_code", "gst_rate", "uom", "warranty_months"]


class QuotationLineSerializer(serializers.ModelSerializer):
    item_detail = serializers.SerializerMethodField(read_only=True)
    id = serializers.IntegerField(required=False)
    price_with_gst = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = QuotationLine
        fields = [
            "id",
            "line_num",
            "item",
            "uom",
            "quantity",
            "open_qty",
            "price",
            "discount_percent",
            "tax_percent",
            "line_total",
            "hsn_code",
            "item_detail",
            "price_with_gst",
        ]
        extra_kwargs = {"doc_entry": {"read_only": True}, "line_num": {"read_only": True}}

    def get_item_detail(self, obj):
        if not obj.item:
            return None
        return ProductDetailSerializer(obj.item).data

    def get_price_with_gst(self, obj):
        """Calculate and return price including GST."""
        price = float(obj.price or 0)
        gst_rate = float(obj.tax_percent or 0)
        return round(price * (1 + gst_rate / 100), 2)


# serializers.py (replace the existing QuotationSerializer with this)
from decimal import Decimal
from django.db import transaction
from rest_framework import serializers

# import your models & nested serializer names to match your project
# from .models import Quotation, QuotationLine, Customer
# from .serializers_other import QuotationLineSerializer

class QuotationSerializer(serializers.ModelSerializer):
    items = QuotationLineSerializer(many=True)
    customer_code = serializers.CharField(source="customer.code", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    enquiry_id = serializers.SerializerMethodField(read_only=True)

    # Accept customer_id as a write-only field (compatibility)
    customer_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Quotation
        fields = "__all__"
        read_only_fields = ["doc_num", "enquiry_id"]

    def get_enquiry_id(self, obj):
        """
        Derive the associated Enquiry ID (doc_num) from the first line item
        that has base_doctype='INQ'.
        """
        first_linked_line = obj.items.filter(base_doc_type="INQ").first()
        if first_linked_line and first_linked_line.base_doc_entry:
            # Assuming base_doc_entry stores the ID of the enquiry, 
            # we might want to return the DOC_NUM or the ID. 
            # Frontend usually expects the ID to look up, or the Code/DocNum to display.
            # Let's fetch the Enquiry to get its doc_num if possible, or just return the ID.
            # If base_doc_entry is the ID (pk) of Inquiry:
            try:
                # We can't import Inquiry inside method easily due to circular imports if strictly separate files,
                # but here they are in same file or we can import at top.
                # Assuming 'Inquiry' is available.
                inquiry = Inquiry.objects.filter(id=first_linked_line.base_doc_entry).first()
                if inquiry:
                   return f"ENQ-{inquiry.doc_num}"
            except Exception:
                pass
            return str(first_linked_line.base_doc_entry)
        return None

    def _normalize_incoming(self, validated_data):
        """
        Normalize common alternate keys and ensure validated_data is in the exact shape
        we will pass to model creation.
        - Accept 'customer' (preferred): either instance (rare) or numeric pk (if DRF resolved it)
        - Accept 'customer_id' (write-only): convert to 'customer_id' key for model kwargs
        - Accept 'lines' (frontend alias): convert to 'items'
        """
        # If frontend sent `lines` instead of `items`, move it
        if "lines" in validated_data and "items" not in validated_data:
            validated_data["items"] = validated_data.pop("lines")

        # If frontend sent customer_id, ensure model receives customer_id
        cid = validated_data.pop("customer_id", None)
        if cid is not None:
            # model can accept 'customer_id' as kwarg to set FK
            validated_data["customer_id"] = cid

        # If someone provided nested 'customer' pk mapped by other serializer config,
        # it's fine — leave it as 'customer' or 'customer_id' depending on what's present.
        return validated_data

    def create(self, validated_data):
        # debug/log: view should also print serializer.validated_data for debugging if needed
        validated_data = self._normalize_incoming(validated_data)

        # Print validated data for debug (remove after verification)
        print("VALIDATED_DATA (create):", {k: v for k, v in validated_data.items() if k != "items"})

        items_data = validated_data.pop("items", []) or []
        with transaction.atomic():
            # Pass validated_data directly to model create -> will accept customer/customer_id if present
            quotation = Quotation.objects.create(**validated_data)

            for i, item_data in enumerate(items_data):
                # Auto-populate tax_percent from product if missing/zero
                if not item_data.get("tax_percent") and item_data.get("item"):
                    try:
                        # item_data['item'] is a Product instance because of ModelSerializer validation
                        product = item_data["item"]
                        if product.gst_rate:
                            item_data["tax_percent"] = product.gst_rate
                    except Exception as e:
                        print(f"Error fetching tax from product: {e}")

                # create QuotationLine - ensure correct keys: doc_entry or doc_entry_id depends on your model
                QuotationLine.objects.create(
                    doc_entry=quotation,
                    line_num=item_data.get("line_num", i + 1),
                    open_qty=item_data.get("open_qty", item_data.get("quantity", 0)),
                    **{k: v for k, v in item_data.items() if k not in ("line_total", "total")},
                )

            # compute totals and save via model method which handles subtotal/tax/grand_total correctly
            quotation.recalculate_totals()
            # Note: recalculate_totals() calls save() internally.

        return quotation

    def update(self, instance, validated_data):
        validated_data = self._normalize_incoming(validated_data)

        # Print validated data for debug (remove after verification)
        print("VALIDATED_DATA (update):", {k: v for k, v in validated_data.items() if k != "items"})

        items_data = validated_data.pop("items", None)

        with transaction.atomic():
            # apply scalar updates
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            # If items provided, replace them
            if items_data is not None:
                instance.items.all().delete()

                for i, item_data in enumerate(items_data):
                    # Auto-populate tax_percent from product if missing/zero
                    if not item_data.get("tax_percent") and item_data.get("item"):
                        try:
                            product = item_data["item"]
                            if product.gst_rate:
                                item_data["tax_percent"] = product.gst_rate
                        except Exception as e:
                            print(f"Error fetching tax from product: {e}")

                    QuotationLine.objects.create(
                        doc_entry=instance,
                        line_num=item_data.get("line_num", i + 1),
                        open_qty=item_data.get("open_qty", item_data.get("quantity", 0)),
                        **{k: v for k, v in item_data.items() if k not in ("line_total", "total")},
                    )

                instance.recalculate_totals()
                # Note: recalculate_totals() calls save() internally.

        return instance




class SalesOrderLineSerializer(serializers.ModelSerializer):
    """Serializer for Sales Order Line Items"""

    product_code = serializers.CharField(
        source="item.product_code", 
        read_only=True, 
        allow_blank=True
    )
    product_name = serializers.CharField(
        source="item.brand", 
        read_only=True, 
        allow_blank=True
    )
    hsn_code = serializers.CharField(
        source="item.hsn_code", 
        read_only=True, 
        allow_blank=True
    )

    price_per_unit = serializers.SerializerMethodField()
    gst_percent = serializers.SerializerMethodField()
    discount_percent = serializers.SerializerMethodField()
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = SalesOrderLine
        fields = [
            "id", "line_num", "item", "product_code", "product_name", "hsn_code",
            "quantity", "uom", "price", "price_per_unit", "gst_percent", 
            "discount_percent", "line_total", "open_qty"
        ]
        read_only_fields = ["id", "product_code", "product_name", "hsn_code"]

    def get_price_per_unit(self, obj):
        return obj.price or 0

    def get_gst_percent(self, obj):
        return getattr(obj, 'tax_percent', 0) or 0

    def get_discount_percent(self, obj):
        return getattr(obj, 'discount_percent', 0) or 0

    def get_line_total(self, obj):
        qty = obj.quantity or 0
        price = obj.price or 0
        gst = getattr(obj, 'tax_percent', 0) or 0
        discount = getattr(obj, 'discount_percent', 0) or 0

        subtotal = qty * price
        discount_amount = (subtotal * discount) / 100
        after_discount = subtotal - discount_amount
        gst_amount = (after_discount * gst) / 100

        return round(after_discount + gst_amount, 2)


class SalesOrderSerializer(serializers.ModelSerializer):
    """Serializer for Sales Order - ONLY REAL FIELDS FROM MODEL"""

    # Customer info from FK
    customer_code = serializers.CharField(
        source="customer.code",
        read_only=True,
        allow_blank=True
    )
    customer_name = serializers.CharField(
        source="customer.name",
        read_only=True,
        allow_blank=True
    )

    # Accept customer_id on create/update
    customer_id = serializers.IntegerField(
        write_only=True,
        required=False,
        allow_null=True
    )

    # Read items
    lines = SalesOrderLineSerializer(
        many=True,
        read_only=True
    )

    # Write items
    items = SalesOrderLineSerializer(
        many=True,
        write_only=True,
        required=False
    )

    customer = CustomerSerializer(read_only=True)
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(), source="customer", write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = SalesOrder
        # ONLY include fields that actually exist in the model!
        fields = [
            "id", "doc_num", "customer", "customer_id", "customer_code", "customer_name",
            "doc_date", "status", "executivename", "canceled", "lines", "items", 
            "created_at", "updated_at"
        ]
        read_only_fields = [
            "id", "doc_num", "customer", "customer_code", "customer_name",
            "lines", "created_at", "updated_at", "canceled"
        ]

    def create(self, validated_data):
        """Create Sales Order with items"""
        items_data = validated_data.pop("items", [])
        customer_id = validated_data.pop("customer_id", None)

        if customer_id:
            validated_data["customer_id"] = customer_id

        order = SalesOrder.objects.create(**validated_data)

        for idx, item_data in enumerate(items_data, 1):
            if "line_num" not in item_data:
                item_data["line_num"] = idx
            
            # Set open_qty to quantity if not provided
            if "open_qty" not in item_data or item_data.get("open_qty") is None:
                item_data["open_qty"] = item_data.get("quantity", 0)
            
            # Auto-populate tax_percent from product if missing/zero
            if not item_data.get("tax_percent") and item_data.get("item"):
                try:
                    product = item_data["item"]
                    if product.gst_rate:
                        item_data["tax_percent"] = product.gst_rate
                except Exception as e:
                    print(f"Error fetching tax from product: {e}")

            SalesOrderLine.objects.create(
                doc_entry=order,
                **item_data
            )
        
        # Recalculate totals after creation
        order.recalculate_totals()

        return order

    def update(self, instance, validated_data):
        """Update Sales Order with items"""
        items_data = validated_data.pop("items", None)
        customer_id = validated_data.pop("customer_id", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if customer_id:
            instance.customer_id = customer_id

        instance.save()

        if items_data is not None:
            instance.lines.all().delete()

            for idx, item_data in enumerate(items_data, 1):
                if "line_num" not in item_data:
                    item_data["line_num"] = idx
                
                # Set open_qty to quantity if not provided
                if "open_qty" not in item_data or item_data.get("open_qty") is None:
                    item_data["open_qty"] = item_data.get("quantity", 0)
                
                # Auto-populate tax_percent from product if missing/zero
                if not item_data.get("tax_percent") and item_data.get("item"):
                    try:
                        product = item_data["item"]
                        if product.gst_rate:
                            item_data["tax_percent"] = product.gst_rate
                    except Exception as e:
                        print(f"Error fetching tax from product: {e}")

                SalesOrderLine.objects.create(
                    doc_entry=instance,
                    **item_data
                )
        
        # Recalculate totals after lines update
        instance.recalculate_totals()

        return instance


class DeliveryLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryLine
        fields = "__all__"


class DeliverySerializer(serializers.ModelSerializer):
    lines = DeliveryLineSerializer(many=True, read_only=True)

    class Meta:
        model = Delivery
        fields = "__all__"


class InvoiceLineSerializer(serializers.ModelSerializer):
    item_detail = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = InvoiceLine
        fields = [
            "id", "line_num", "item", "uom", "quantity", "open_qty",
            "price", "discount_percent", "tax_percent", "line_total",
            "hsn_code", "item_detail", "product_name", "serial_number"
        ]

    product_name = serializers.CharField(source="item.product_name", read_only=True, allow_null=True)

    def get_item_detail(self, obj):
            if not obj.item:
                return None
            return {
                "id": obj.item.id,
                "product_code": obj.item.product_code,
                "product_name": obj.item.brand + " " + (obj.item.series or "") + " " + (obj.item.model_number or ""),
                "brand": obj.item.brand,
                "gst_rate": obj.item.gst_rate,
                "hsn_code": obj.item.hsn_code,
                "price": float(obj.item.price or 0),
            }

    
    


class InvoiceSerializer(serializers.ModelSerializer):
    lines = InvoiceLineSerializer(many=True, required=False)
    customer = CustomerSerializer(read_only=True)
    customer_id = serializers.PrimaryKeyRelatedField(
        queryset=Customer.objects.all(), source="customer", write_only=True, required=False, allow_null=True
    )

    paid_amount = serializers.SerializerMethodField()
    outstanding_amount = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = "__all__"
        read_only_fields = ["paid_amount", "outstanding_amount"]

    def get_paid_amount(self, obj):
        return sum(p.amount for p in obj.payments.all())

    def get_outstanding_amount(self, obj):
        paid = sum(p.amount for p in obj.payments.all())
        return float(obj.grand_total or 0) - float(paid)

    def create(self, validated_data):
        lines_data = validated_data.pop("lines", [])
        customer_id = validated_data.pop("customer_id", None)
        
        if customer_id:
            validated_data["customer"] = customer_id
            
        invoice = Invoice.objects.create(**validated_data)
        for line_data in lines_data:
            InvoiceLine.objects.create(doc_entry=invoice, **line_data)

        # Update Customer Outstanding
        if invoice.customer:
            try:
                current_outstanding_str = str(invoice.customer.outstanding or "0").replace("₹", "").replace(",", "")
                current_outstanding = float(current_outstanding_str)
            except ValueError:
                current_outstanding = 0.0
            
            new_outstanding = current_outstanding + float(invoice.grand_total or 0)
            invoice.customer.outstanding = f"₹{new_outstanding:,.2f}"
            invoice.customer.save()
            
        invoice.recalculate_totals()
        return invoice

    def update(self, instance, validated_data):
        lines_data = validated_data.pop("lines", None)
        customer_id = validated_data.pop("customer_id", None)

        # Update scalar fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        if customer_id:
            instance.customer = customer_id
            
        instance.save()
        
        existing_ids = [line.id for line in instance.lines.all()]
        if lines_data is not None:
             # Logic to update lines... (simplified for clarity, keeping original behavior usually best but ensure safety)
            payload_ids = [item.get("id") for item in lines_data if item.get("id")]

            for line_id in existing_ids:
                if line_id not in payload_ids:
                    InvoiceLine.objects.filter(id=line_id).delete()

            for line_data in lines_data:
                line_id = line_data.get("id", None)
                if line_id:
                    line = InvoiceLine.objects.get(id=line_id, doc_entry=instance)
                    for attr, value in line_data.items():
                        setattr(line, attr, value)
                    line.save()
                else:
                    InvoiceLine.objects.create(doc_entry=instance, **line_data)

        instance.recalculate_totals()
        return instance


class DocTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocType
        fields = "__all__"


class DocFlowLinkSerializer(serializers.ModelSerializer):
    source_doctype = DocTypeSerializer(read_only=True)
    target_doctype = DocTypeSerializer(read_only=True)

    class Meta:
        model = DocFlowLink
        fields = "__all__"


class PaymentSerializer(serializers.ModelSerializer):
    # Add read-only fields for better display
    invoice_doc_num = serializers.IntegerField(source="invoice.doc_num", read_only=True)
    invoice_pk = serializers.IntegerField(source="invoice.id", read_only=True)
    invoice_num = serializers.CharField(source="invoice.invoice_num", read_only=True)
    invoice_customer_name = serializers.CharField(source="invoice.customer.name", read_only=True)
    invoice_grand_total = serializers.DecimalField(
        source="invoice.grand_total", 
        read_only=True,
        max_digits=15,
        decimal_places=2
    )
    
    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ["id", "paid_at", "deleted_at", "is_active", 
                           "invoice_doc_num", "invoice_pk", "invoice_num", "invoice_customer_name", "invoice_grand_total"]


class ServiceCallTechnicianSerializer(serializers.ModelSerializer):
    """Technician assignment serializer"""
    
    # Display labels for codes
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    class Meta:
        model = ServiceCallTechnician
        fields = [
            'id', 'technician', 'scheduled_date', 'start_time', 'end_time',
            'duration_hours', 'status', 'status_display', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate(self, data):
        if data.get('start_time') and data.get('end_time'):
            if data['start_time'] >= data['end_time']:
                raise serializers.ValidationError(
                    "Start time must be before end time"
                )
        return data


class ServiceCallResolutionSerializer(serializers.ModelSerializer):
    """Resolution serializer"""
    
    # Display label for status code
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    class Meta:
        model = ServiceCallResolution
        fields = [
            'id', 'resolution_date', 'technician', 'time_spent',
            'solution_description', 'customer_feedback', 'status', 'status_display',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ServiceCallExpenseSerializer(serializers.ModelSerializer):
    """Expense serializer"""
    
    # Display label for expense type code
    expense_type_display = serializers.CharField(
        source='get_expense_type_display',
        read_only=True
    )
    
    class Meta:
        model = ServiceCallExpense
        fields = [
            'id', 'expense_type', 'expense_type_display', 'description',
            'quantity', 'unit_price', 'total_amount', 'created_at'
        ]
        read_only_fields = ['id', 'total_amount', 'created_at']
    
    def validate(self, data):
        quantity = data.get('quantity', 0)
        unit_price = data.get('unit_price', 0)
        
        if quantity < 0:
            raise serializers.ValidationError(
                {"quantity": "Quantity cannot be negative"}
            )
        if unit_price < 0:
            raise serializers.ValidationError(
                {"unit_price": "Unit price cannot be negative"}
            )
        
        return data


class ServiceCallActivitySerializer(serializers.ModelSerializer):
    """Activity serializer"""
    
    # Display label for activity type code
    activity_type_display = serializers.CharField(
        source='get_activity_type_display',
        read_only=True
    )
    
    class Meta:
        model = ServiceCallActivity
        fields = [
            'id', 'activity_type', 'activity_type_display', 'activity_date',
            'performed_by', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# ============================================================
# MAIN SERIALIZERS
# ============================================================

class ServiceCallDetailSerializer(serializers.ModelSerializer):
    """Complete Service Call with nested data"""
    
    # Nested serializers
    technicians = ServiceCallTechnicianSerializer(many=True, required=False)
    resolutions = ServiceCallResolutionSerializer(many=True, required=False)
    expenses = ServiceCallExpenseSerializer(many=True, required=False)
    activities = ServiceCallActivitySerializer(many=True, required=False)
    
    # Customer info (from FK)
    customer_name = serializers.CharField(
        source='customer.name',
        read_only=True
    )
    customer_code = serializers.CharField(
        source='customer.code',
        read_only=True
    )
    
    # Status & Priority display labels
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    priority_display = serializers.CharField(
        source='get_priority_display',
        read_only=True
    )
    
    class Meta:
        model = ServiceCall
        fields = [
            # Header
            'id', 'call_num', 'customer', 'customer_name', 'customer_code',
            'equipment', 'call_date', 'priority', 'priority_display',
            'status', 'status_display', 'contract', 'problem_description', 'notes',
            
            # Nested
            'technicians', 'resolutions', 'expenses', 'activities',
            
            # Timestamps
            'closed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'call_num', 'customer_name', 'customer_code',
            'status_display', 'priority_display', 'closed_at',
            'created_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        """Create with nested data"""
        tech_data = validated_data.pop('technicians', [])
        res_data = validated_data.pop('resolutions', [])
        exp_data = validated_data.pop('expenses', [])
        act_data = validated_data.pop('activities', [])
        
        # Create main
        call = ServiceCall.objects.create(**validated_data)
        
        # Create nested
        for t in tech_data:
            ServiceCallTechnician.objects.create(service_call=call, **t)
        
        for r in res_data:
            ServiceCallResolution.objects.create(service_call=call, **r)
        
        for e in exp_data:
            ServiceCallExpense.objects.create(service_call=call, **e)
        
        for a in act_data:
            ServiceCallActivity.objects.create(service_call=call, **a)
        
        return call
    
    def update(self, instance, validated_data):
        """Update main fields only"""
        for field, value in validated_data.items():
            if field not in ['technicians', 'resolutions', 'expenses', 'activities']:
                setattr(instance, field, value)
        
        instance.save()
        return instance


class ServiceCallListSerializer(serializers.ModelSerializer):
    """Lightweight for list views (grid display)"""
    
    customer_name = serializers.CharField(
        source='customer.name',
        read_only=True
    )
    
    priority_display = serializers.CharField(
        source='get_priority_display',
        read_only=True
    )
    
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    class Meta:
        model = ServiceCall
        fields = [
            'id', 'call_num', 'customer_name', 'equipment', 'call_date', 'priority',
            'priority_display', 'status', 'status_display', 'created_at'
        ]


# ============================================================
# CUSTOMER AUTOCOMPLETE SERIALIZER
# ============================================================

class CustomerAutocompleteSerializer(serializers.ModelSerializer):
    """For AJAX autocomplete"""
    
    display = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = ['id', 'name', 'code', 'display']
    
    def get_display(self, obj):
        return f"{obj.code or 'N/A'} - {obj.name}"


# ============================================================
# HELPER: Status & Priority Display Mapping
# ============================================================

"""
FRONTEND MAPPING - Use these codes in your React component:

Service Call Status:
  'O'  = Open
  'IP' = In Progress
  'R'  = Resolved
  'CL' = Closed

Service Call Priority:
  'L' = Low
  'M' = Medium
  'H' = High
  'C' = Critical

Technician Status:
  'S'  = Scheduled
  'IP' = In Progress
  'C'  = Completed
  'X'  = Cancelled

Resolution Status:
  'P' = Partial
  'F' = Full

Expense Type:
  'P' = Parts
  'L' = Labor
  'T' = Travel
  'M' = Material
  'O' = Other

Activity Type:
  'SV' = Site Visit
  'PC' = Phone Call
  'EM' = Email
  'PR' = Parts Replaced
  'TR' = Training
  'FU' = Follow-up
  'O'  = Other
"""


class TechnicianSerializer(serializers.ModelSerializer):
    class Meta:
        model = Technician
        fields = "__all__"
        read_only_fields = ["id", "deleted_at", "is_active"]


class TechnicianScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnicianSchedule
        fields = "__all__"


class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = "__all__"
        read_only_fields = ["id", "deleted_at", "is_active"]


class AMCContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = AMCContract
        fields = "__all__"
        read_only_fields = ["id", "deleted_at", "is_active"]


class LeadSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)

    class Meta:
        model = Lead
        fields = "__all__"
        read_only_fields = ["id", "created_at", "deleted_at", "is_active"]


class AMCContractEquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AMCContractEquipment
        fields = ['id', 'product_model', 'serial_number', 'part_number', 'installation_date', 'warranty_end', 'status']


class AMCContractSerializer(serializers.ModelSerializer):
    equipment = AMCContractEquipmentSerializer(source='equipment_covered', many=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_code = serializers.CharField(source='customer.code', read_only=True)
    
    # Read-only lists for UI tabs
    service_history = serializers.SerializerMethodField()
    invoices = serializers.SerializerMethodField()

    class Meta:
        model = AMCContract
        fields = [
            'id', 'contract_id', 'customer', 'customer_name', 'customer_code', 'contract_type',
            'start_date', 'end_date', 'contract_value', 'response_time',
            'payment_terms', 'coverage_details', 'terms_conditions',
            'renewal_date', 'revised_value', 'payment_status', 'is_active',
            'equipment', 'service_history', 'invoices'
        ]
        read_only_fields = ['id', 'customer_name', 'customer_code', 'service_history', 'invoices']

    def get_service_history(self, obj):
        if not obj.customer: return []
        # Return last 10 calls for this customer
        calls = ServiceCall.objects.filter(customer=obj.customer).order_by('-id')[:10]
        # Minimal data for the list
        return [{
            'callId': c.call_num,
            'date': c.call_date,
            'equipment': c.equipment,
            'issue': c.problem_description,
            'priority': c.get_priority_display(),
            'status': c.get_status_display(),
            'technician': c.technicians.first().technician if c.technicians.exists() else 'Unassigned',
            'resolution': c.resolutions.last().solution_description if c.resolutions.exists() else ''
        } for c in calls]

    def get_invoices(self, obj):
        # Return empty list - invoices tab is read-only and not critical for warranty contracts
        return []

    def create(self, validated_data):
        eq_data = validated_data.pop('equipment_covered', [])
        
        # Auto-generate contract ID if missing
        if not validated_data.get('contract_id'):
            validated_data['contract_id'] = f"AMC-{int(timezone.now().timestamp())}"

        contract = AMCContract.objects.create(**validated_data)
        
        for eq in eq_data:
            AMCContractEquipment.objects.create(amc_contract=contract, **eq)
        return contract

    def update(self, instance, validated_data):
        eq_data = validated_data.pop('equipment_covered', [])
        
        # Update main fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update equipment: Replace strategy (Simplest for nested lists)
        # In a real app we might try to match IDs to prevent churn, but this is safe for now
        instance.equipment_covered.all().delete()
        for eq in eq_data:
            AMCContractEquipment.objects.create(amc_contract=instance, **eq)
        
        return instance


from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"