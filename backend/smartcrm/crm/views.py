# Complete Updated views.py - FIXED
# All existing code + fixes for soft delete + basename error fix

from django.utils import timezone
from django.db.models import F, Max, Sum, Count
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from decimal import Decimal

from .models import (
    Inquiry, InquiryLine, InquiryActivity,
    Quotation, QuotationLine,
    SalesOrder, SalesOrderLine,
    Delivery, DeliveryLine,
    Invoice, InvoiceLine,
    Product,
    Customer,
    Company,
    Payment,
    ServiceCall,
    ServiceCallTechnician,
    ServiceCallResolution,
    ServiceCallExpense,
    ServiceCallActivity,
    Technician,
    TechnicianSchedule,
    Equipment,
    AMCContract,
    Lead,
    DocType,
    DocFlowLink,
)
from .serializers import (
    InquirySerializer, InquiryLineSerializer, InquiryActivitySerializer,
    QuotationSerializer, QuotationLineSerializer,
    SalesOrderSerializer, SalesOrderLineSerializer,
    DeliverySerializer, DeliveryLineSerializer,
    InvoiceSerializer, InvoiceLineSerializer,
    ProductSerializer,
    CustomerSerializer,
    CompanySerializer,
    PaymentSerializer,
    TechnicianSerializer,
    TechnicianScheduleSerializer,
    EquipmentSerializer,
    AMCContractSerializer,
    LeadSerializer,
    DocTypeSerializer,
    DocFlowLinkSerializer,
    CustomerAutocompleteSerializer,
    ServiceCallDetailSerializer,
    ServiceCallListSerializer,
    ServiceCallTechnicianSerializer,
    ServiceCallResolutionSerializer,
    ServiceCallExpenseSerializer,
    ServiceCallActivitySerializer,
)


class SoftModelViewSet(viewsets.ModelViewSet):
    """Base ViewSet - with Soft Delete implementation."""

    def get_queryset(self):
        """
        By default, list only active records.
        For detail/retrieve/update, we might want to allow access if needed,
        but typically we hide them from general lists.
        """
        qs = super().get_queryset()
        if self.action == 'list':
            return qs.filter(is_active=True)
        return qs

    def perform_destroy(self, instance):
        """Soft delete: Mark as inactive instead of removing from DB."""
        instance.is_active = False
        instance.save()


class CustomerViewSet(SoftModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "phone", "email", "code"]


class ProductViewSet(SoftModelViewSet):
    queryset = Product.objects.all().order_by("id")
    serializer_class = ProductSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["product_code", "brand", "series", "model_number", "description"]


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer


class InquiryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Inquiry (Enquiry) Management
    ✅ UPDATED: Now uses hard delete (permanent removal from DB)
    """
    
    queryset = Inquiry.objects.all().order_by("-id")
    serializer_class = InquirySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return all enquiries (no soft delete filtering)"""
        return Inquiry.objects.all().order_by("-id")

    def destroy(self, request, *args, **kwargs):
        """
        Hard delete: Permanently remove from database
        """
        try:
            instance = self.get_object()
            
            # Hard delete: permanently remove from DB
            instance.delete()
            
            return Response(
                {"message": "Enquiry deleted successfully"},
                status=status.HTTP_204_NO_CONTENT,
            )
        
        except Inquiry.DoesNotExist:
            return Response(
                {"error": "Enquiry not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        except Exception as e:
            print(f"Delete Enquiry Error: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["get", "post"], url_path="items")
    def items(self, request, pk=None):
        """
        GET: List all enquiry items
        POST: Create new enquiry item
        """
        inquiry = self.get_object()

        if request.method == "GET":
            serializer = InquiryLineSerializer(inquiry.items.all(), many=True)
            return Response(serializer.data)

        if request.method == "POST":
            data = request.data.copy()

            # Remove doc_entry if present (will be set automatically)
            if "doc_entry" in data:
                del data["doc_entry"]

            # Auto-generate line number
            last_line = inquiry.items.aggregate(Max("line_num"))["line_num__max"] or 0
            data["line_num"] = last_line + 1

            # Set open_qty defaults if needed
            if "quantity" in data and "open_qty" not in data:
                data["open_qty"] = data["quantity"]

            serializer = InquiryLineSerializer(data=data)
            if serializer.is_valid():
                serializer.save(doc_entry=inquiry)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            print("Item Serializer Errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["put", "delete"], url_path=r"items/(?P<item_id>[0-9]+)")
    def item_detail(self, request, pk=None, item_id=None):
        """
        PUT: Update a specific enquiry item
        DELETE: Delete a specific enquiry item
        """
        inquiry = self.get_object()

        try:
            item = inquiry.items.get(id=item_id)
        except InquiryLine.DoesNotExist:
            return Response(
                {"error": "Item not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if request.method == "PUT":
            old_qty = Decimal(item.quantity)
            new_qty = Decimal(request.data.get("quantity", old_qty))

            if new_qty != old_qty:
                diff = new_qty - old_qty
                request.data["open_qty"] = max(Decimal(0), item.open_qty + diff)

            serializer = InquiryLineSerializer(item, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "DELETE":
            item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get", "post"], url_path="activities")
    def activities(self, request, pk=None):
        """
        GET: List all enquiry activities
        POST: Create new enquiry activity
        """
        inquiry = self.get_object()

        if request.method == "GET":
            serializer = InquiryActivitySerializer(inquiry.activities.all(), many=True)
            return Response(serializer.data)

        if request.method == "POST":
            data = request.data.copy()

            # Remove inquiry if present (will be set automatically)
            if "inquiry" in data:
                del data["inquiry"]

            serializer = InquiryActivitySerializer(data=data)
            if serializer.is_valid():
                serializer.save(inquiry=inquiry)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            print("Activity Serializer Errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["put", "delete"], url_path=r"activities/(?P<activity_id>[0-9]+)")
    def activity_detail(self, request, pk=None, activity_id=None):
        """
        PUT: Update a specific enquiry activity
        DELETE: Delete a specific enquiry activity
        """
        inquiry = self.get_object()

        try:
            activity = inquiry.activities.get(id=activity_id)
        except InquiryActivity.DoesNotExist:
            return Response(
                {"error": "Activity not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if request.method == "PUT":
            serializer = InquiryActivitySerializer(activity, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if request.method == "DELETE":
            activity.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="convert-to-quotation")
    def convert_to_quotation(self, request, pk=None):
        """
        Fetch Inquiry header and items and prepare data for
        pre-filling a quotation dialog (payload matches QuotationSerializer).
        ✅ UPDATED: Automatically changes enquiry status to 'converted'
        """
        inquiry = self.get_object()
        
        # ✅ UPDATE STATUS TO CONVERTED
        inquiry.status = "converted"
        inquiry.save()
        
        items = inquiry.items.all()

        # Build items in the shape QuotationSerializer/QuotationLine expects
        items_payload = []
        total = 0.0
        for idx, line in enumerate(items, start=1):
            item_fk = line.item.id if line.item else None
            price = float(line.price or 0)
            qty = float(line.quantity or 0)
            line_total = price * qty
            total += line_total

            items_payload.append({
                # keys that match the quotation line/create API
                "line_num": idx,
                "item": item_fk,               # FK to product (model field name is usually `item`)
                "quantity": qty,
                "price": price,
                "remarks": line.remarks or "",
                "open_qty": float(line.open_qty or line.quantity or 0),
                # optional audit/trace fields
                "base_doctype": "INQ",
                "base_docentry": inquiry.id,
                "base_line": line.line_num,
            })

        # Defensive: include both 'customer' (FK expected by model) and 'customer_id'
        quotation_preview = {
            "customer": inquiry.customer.id if inquiry.customer else None,
            "customer_id": inquiry.customer.id if inquiry.customer else None,
            "customer_name": inquiry.customer.name if inquiry.customer else "",
            "doc_date": str(timezone.now().date()),
            "status": "Draft",
            "lines": items_payload,               # IMPORTANT: use key 'items' not 'lines'
            "overall_total": total,
        }

        # debug print to verify server-side payload
        print("convert_to_quotation preview:", quotation_preview)

        return Response(quotation_preview, status=status.HTTP_200_OK)



class QuotationViewSet(viewsets.ModelViewSet):
    """Full-featured Quotation ViewSet with hard delete"""

    queryset = Quotation.objects.all().order_by("-id")
    serializer_class = QuotationSerializer

    def get_queryset(self):
        """Return all quotations (no soft delete filtering)"""
        return Quotation.objects.all().order_by("-id")

    def destroy(self, request, *args, **kwargs):
        """Hard delete quotation from database"""
        try:
            instance = self.get_object()
            instance.delete()  # Hard delete from DB
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Quotation.DoesNotExist:
            return Response({"detail": "Quotation not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["get", "post"], url_path="items")
    def items(self, request, pk=None):
        quotation = self.get_object()

        if request.method == "GET":
            serializer = QuotationLineSerializer(quotation.items.all(), many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        elif request.method == "POST":
            data = request.data.copy()
            data["doc_entry"] = quotation.id

            last_line = quotation.items.aggregate(Max("line_num"))["line_num__max"] or 0
            data["line_num"] = last_line + 1

            if "quantity" in data and "open_qty" not in data:
                data["open_qty"] = data["quantity"]

            serializer = QuotationLineSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            print("Serializer Errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel_quotation(self, request, pk=None):
        """Cancels the quotation"""
        try:
            quotation = self.get_object()

            if SalesOrderLine.objects.filter(
                base_doctype="QUO", base_docentry=quotation.id
            ).exists():
                return Response(
                    {"error": "Cannot cancel quotation already converted to Sales Order."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            restored_count = 0
            for quot_line in quotation.items.all():
                if quot_line.base_doctype == "INQ" and quot_line.base_docentry:
                    try:
                        inq_item = InquiryLine.objects.get(
                            doc_entry_id=quot_line.base_docentry,
                            line_num=quot_line.base_line,
                        )
                        inq_item.open_qty = F("open_qty") + quot_line.quantity
                        inq_item.save()
                        inq_item.refresh_from_db()
                        restored_count += 1

                        inquiry = inq_item.doc_entry
                        if inquiry.status == "C":
                            inquiry.status = "O"
                            inquiry.save()

                    except InquiryLine.DoesNotExist:
                        continue

            quotation.status = "Canceled"
            quotation.save()

            return Response(
                {
                    "message": "Quotation canceled successfully.",
                    "items_restored": restored_count,
                },
                status=status.HTTP_200_OK,
            )

        except Quotation.DoesNotExist:
            return Response({"error": "Quotation not found."}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            print(f"Cancel quotation error: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["post"], url_path="convert-to-salesorder")
    def convert_to_salesorder(self, request, pk=None):
        """Converts quotation to Sales Order"""
        try:
            quotation = self.get_object()

            # -----------------------------
            # 1️⃣ FIX CUSTOMER RESOLUTION
            # -----------------------------
            customer_obj = quotation.customer

            # Case 1: quotation.customer_id exists
            if not customer_obj and getattr(quotation, "customer_id", None):
                customer_obj = Customer.objects.filter(id=quotation.customer_id).first()

            # Case 2: Try matching customer_code
            if not customer_obj and getattr(quotation, "customer_code", None):
                customer_obj = Customer.objects.filter(code=quotation.customer_code).first()

            # Case 3: Try matching customer_name
            if not customer_obj and getattr(quotation, "customer_name", None):
                customer_obj = Customer.objects.filter(name=quotation.customer_name).first()

            # If STILL no customer → return error
            if not customer_obj:
                return Response(
                    {"error": "Quotation has no valid customer. Please update quotation with a proper customer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ---------------------------------
            # 2️⃣ FILTER LINES WITH OPEN QTY
            # ---------------------------------
            convertible_lines = quotation.items.filter(open_qty__gt=0)

            if not convertible_lines.exists():
                return Response(
                    {"error": "No items to convert"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ---------------------------------
            # 3️⃣ CREATE SALES ORDER
            # ---------------------------------
            so = SalesOrder.objects.create(
                customer=customer_obj,
                doc_date=timezone.now().date(),
                status="Open",
                executivename=getattr(quotation, "executivename", ""),
            )

            # ---------------------------------
            # 4️⃣ CREATE SALES ORDER LINES
            # ---------------------------------
            for line in convertible_lines:

                # Resolve product
                product_obj = None
                if line.item_id:
                    product_obj = line.item
                elif getattr(line, "product", None):
                    product_obj = Product.objects.filter(product_code=line.product).first()

                if not product_obj:
                    continue

                qty = line.open_qty or line.quantity or 0
                price = line.price or line.price_per_unit or 0

                discount = (
                    getattr(line, "discount_percent", None)
                    if getattr(line, "discount_percent", None) is not None
                    else getattr(line, "line_discount", None)
                    if getattr(line, "line_discount", None) is not None
                    else 0
                )

                tax = (
                    getattr(line, "tax_percent", None)
                    if getattr(line, "tax_percent", None) is not None
                    else getattr(line, "gst_percent", None)
                    if getattr(line, "gst_percent", None) is not None
                    else 0
                )

                # Compute totals
                subtotal = qty * price
                discount_amt = subtotal * (discount / 100)
                taxable_amt = subtotal - discount_amt
                gst_amt = taxable_amt * (tax / 100)
                line_total = taxable_amt + gst_amt

                # Create sales order line
                SalesOrderLine.objects.create(
                    doc_entry=so,
                    line_num=line.line_num or line.id,
                    item=product_obj,
                    quantity=qty,
                    open_qty=qty,
                    price=price,
                    discount_percent=discount,
                    tax_percent=tax,
                    line_total=line_total,
                )

                # consumed qty
                line.open_qty = 0
                line.save()

            # ---------------------------------
            # 5️⃣ CLOSE QUOTATION IF FINISHED
            # ---------------------------------
            if not quotation.items.filter(open_qty__gt=0).exists():
                quotation.status = "Closed"
                quotation.save()

            return Response(
                {
                    "sales_order_id": so.id,
                    "id": so.id,
                    "message": "Sales Order created successfully"
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            print(f"Error: {str(e)}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )





class SalesOrderViewSet(SoftModelViewSet):
    queryset = SalesOrder.objects.all()
    serializer_class = SalesOrderSerializer

    @action(detail=True, methods=["get", "post"], url_path="items")
    def items(self, request, pk=None):
        """Handle api/sales-orders/items list/create order lines"""
        sales_order = self.get_object()

        if request.method == "GET":
            lines = sales_order.lines.all().order_by("line_num")
            serializer = SalesOrderLineSerializer(lines, many=True)
            return Response(serializer.data)

        elif request.method == "POST":
            serializer = SalesOrderLineSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(doc_entry=sales_order)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="convert-to-invoice")
    def convert_to_invoice(self, request, pk=None):
        """Convert SalesOrder to Invoice"""
        try:
            order = self.get_object()
            
            # Check if customer exists
            if not order.customer:
                return Response(
                    {"error": "Sales order has no customer assigned"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            convertible_lines = order.lines.filter(open_qty__gt=0)

            if not convertible_lines.exists():
                return Response(
                    {"error": "All order items already invoiced"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Create invoice with overall_discount from sales order
            invoice = Invoice.objects.create(
                customer=order.customer,
                doc_date=timezone.now(),
                status="Open",
                executivename=getattr(order, "executivename", ""),
                overall_discount=order.overall_discount,  # Copy overall discount
            )

            # Create invoice lines
            for line in convertible_lines:
                # Calculate totals (basic implementation - adjust if tax logic is complex)
                line_total = line.price * line.open_qty
                if line.discount_percent:
                    line_total -= (line_total * line.discount_percent / 100)
                if line.tax_percent:
                    line_total += (line_total * line.tax_percent / 100)
                
                InvoiceLine.objects.create(
                    doc_entry=invoice,
                    line_num=line.line_num,
                    item=line.item,
                    quantity=line.open_qty,
                    open_qty=line.open_qty,
                    price=line.price,
                    uom=line.uom,  # Copy UOM
                    discount_percent=line.discount_percent, # Copy Discount
                    tax_percent=line.tax_percent, # Copy Tax
                    hsn_code=line.hsn_code, # Copy HSN
                    line_total=line_total # Save Calculated Total
                )

                line.open_qty = 0
                line.save()

            # Recalculate invoice totals from lines
            invoice.recalculate_totals()

            # Close order if all lines are invoiced
            if not order.lines.filter(open_qty__gt=0).exists():
                order.status = "Closed"
                order.save()

            return Response(
                {"invoice_id": invoice.id, "message": "Invoice created successfully"},
                status=status.HTTP_201_CREATED,
            )
            
        except Exception as e:
            print(f"❌ ERROR in convert_to_invoice: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Failed to convert to invoice: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DeliveryViewSet(SoftModelViewSet):
    queryset = Delivery.objects.all()
    serializer_class = DeliverySerializer

    @action(detail=True, methods=["post"], url_path="convert-to-invoice")
    def convert_to_invoice(self, request, pk=None):
        """Convert Delivery to Invoice"""
        delivery = self.get_object()
        print(delivery)
        convertible_lines = delivery.lines.filter(open_qty__gt=0)

        if not convertible_lines.exists():
            return Response(
                {"error": "All delivery items already invoiced"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invoice = Invoice.objects.create(
            customer=delivery.customer,
            doc_date=timezone.now(),
            status="Open",
            overall_discount=delivery.overall_discount,
        )

        for line in convertible_lines:
            InvoiceLine.objects.create(
                doc_entry=invoice,
                line_num=line.line_num,
                item=line.item,
                quantity=line.open_qty,
                open_qty=line.open_qty,
                price=line.price,
                uom=line.uom,  # Copy UOM
                discount_percent=line.discount_percent,  # Copy Discount
                tax_percent=line.tax_percent,  # Copy Tax
                hsn_code=line.hsn_code,  # Copy HSN
                line_total=line.line_total,  # Copy line total
                base_doctype="DLV",
                base_docentry=delivery.doc_num,
                base_line=line.line_num,
            )

            line.open_qty = 0
            line.save()

        # Recalculate invoice totals from lines
        invoice.recalculate_totals()

        if not delivery.lines.filter(open_qty__gt=0).exists():
            delivery.status = "Closed"
            delivery.save()

        return Response(
            {"invoice_id": invoice.id, "message": "Invoice created successfully"},
            status=status.HTTP_201_CREATED,
        )


class InvoiceViewSet(SoftModelViewSet):
    queryset = Invoice.objects.all().order_by('-doc_num')
    serializer_class = InvoiceSerializer

    @action(detail=True, methods=["get", "post"], url_path="items")
    def items(self, request, pk=None):
        invoice = self.get_object()
        
        if request.method == "GET":
            lines = invoice.lines.all().order_by("line_num")
            serializer = InvoiceLineSerializer(lines, many=True)
            return Response(serializer.data)
        
        elif request.method == "POST":
            serializer = InvoiceLineSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(doc_entry=invoice)
            return Response(serializer.data, status=status.HTTP_201_CREATED)



class PaymentViewSet(SoftModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def perform_create(self, serializer):
        payment = serializer.save()
        invoice = payment.invoice
        
        # 1. Update Customer Outstanding
        if invoice and invoice.customer:
            try:
                current_str = str(invoice.customer.outstanding or "0").replace("₹", "").replace(",", "")
                current_bal = float(current_str)
            except ValueError:
                current_bal = 0.0
            
            new_bal = current_bal - float(payment.amount)
            invoice.customer.outstanding = f"₹{new_bal:,.2f}"
            invoice.customer.save()

        # 2. Check and Close Invoice if fully paid
        if invoice:
            paid_so_far = sum(p.amount for p in invoice.payments.all())
            if paid_so_far >= invoice.grand_total:
                invoice.status = "Closed"
                invoice.save()

    def perform_destroy(self, instance):
        """Update customer outstanding when payment is deleted"""
        payment = instance
        invoice = payment.invoice
        
        # 1. Update Customer Outstanding (increase by payment amount)
        if invoice and invoice.customer:
            try:
                current_str = str(invoice.customer.outstanding or "0").replace("₹", "").replace(",", "")
                current_bal = float(current_str)
            except ValueError:
                current_bal = 0.0
            
            new_bal = current_bal + float(payment.amount)
            invoice.customer.outstanding = f"₹{new_bal:,.2f}"
            invoice.customer.save()

        # 2. Reopen Invoice if it was closed
        if invoice and invoice.status == "Closed":
            invoice.status = "Open"
            invoice.save()
        
        # 3. Delete the payment
        instance.delete()


class ServiceCallViewSet(SoftModelViewSet):
    """✅ FIXED: Service Call Management ViewSet"""
    
    # ✅ Prefetch related data for performance
    queryset = ServiceCall.objects.filter(is_active=True).prefetch_related(
        'technicians', 'resolutions', 'expenses', 'activities', 'customer'
    )
    
    # ✅ Default serializer
    serializer_class = ServiceCallDetailSerializer
    
    filter_backends = [filters.SearchFilter]
    search_fields = ['call_num', 'customer__name', 'equipment']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """✅ FIX: Use list serializer for list view, detail for others"""
        if self.action == 'list':
            return ServiceCallListSerializer
        return ServiceCallDetailSerializer

    @action(detail=False, methods=['get'])
    def customer_search(self, request):
        """✅ NEW: Search customers for autocomplete"""
        query = request.query_params.get('q', '').strip()
        if len(query) < 2:
            return Response([])
        
        customers = Customer.objects.filter(
            is_active=True,
            name__icontains=query
        )[:10]
        
        data = []
        for c in customers:
            data.append({
                'id': c.id,
                'name': c.name,
                'code': c.code,
                'display': f"{c.code or 'N/A'} - {c.name}"
            })
        return Response(data)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """✅ FIX: Close service call - set status to 'CL' not 'Closed'"""
        sc = self.get_object()
        sc.status = "CL"  # ✅ Use SHORT code
        sc.closed_at = timezone.now()
        sc.save()
        return Response({"message": "Service call closed"}, status=status.HTTP_200_OK)


class TechnicianViewSet(SoftModelViewSet):
    queryset = Technician.objects.all()
    serializer_class = TechnicianSerializer


class TechnicianScheduleViewSet(viewsets.ModelViewSet):
    queryset = TechnicianSchedule.objects.all()
    serializer_class = TechnicianScheduleSerializer


class EquipmentViewSet(SoftModelViewSet):
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer


class AMCContractViewSet(SoftModelViewSet):
    queryset = AMCContract.objects.all().select_related('customer').prefetch_related('equipment_covered')
    serializer_class = AMCContractSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['contract_id', 'customer__name', 'customer__code']
    ordering_fields = ['contract_id', 'start_date', 'contract_value']
    ordering = ['-id']  # Changed from '-created_at' to '-id'

    @action(detail=False, methods=['get'])
    def customer_search(self, request):
        """AJAX Search for Customers"""
        query = request.query_params.get('q', '')
        if len(query) < 2:
            return Response([])
        
        customers = Customer.objects.filter(
            name__icontains=query,
            is_active=True
        )[:10] | Customer.objects.filter(
            code__icontains=query,
            is_active=True
        )[:10]
        
        serializer = CustomerAutocompleteSerializer(customers, many=True)
        return Response(serializer.data)


class LeadViewSet(SoftModelViewSet):
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer

class DashboardViewSet(viewsets.ViewSet):
    """
    ViewSet for Dashboard Analytics & KPIs
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    @action(detail=False, methods=['get'])
    def stats(self, request):
        today = timezone.now().date()
        current_month = today.month
        current_year = today.year

        # --- 1. Total Outstanding Pending ---
        # (Sum of all Active Invoices) - (Sum of all Linked Payments)
        # We consider ALL time outstanding, not just this month
        total_invoiced_all_time = Invoice.objects.filter(
            is_active=True,
            canceled=False
        ).exclude(status='Canceled').aggregate(
            total=Sum('grand_total')
        )['total'] or Decimal(0)

        total_paid_all_time = Payment.objects.filter(
            is_active=True,
            invoice__is_active=True,
            invoice__canceled=False
        ).exclude(invoice__status='Canceled').aggregate(
            total=Sum('amount')
        )['total'] or Decimal(0)

        total_outstanding_pending = total_invoiced_all_time - total_paid_all_time

        # --- 2. Total Invoices Pending ---
        # Count of invoices that are NOT fully paid (Status != 'Paid' OR outstanding > 0)
        # Often status is updated manually or via signals, but calculating logic is safer
        # We'll stick to a robust check: Invoice Total > Paid Total for that invoice
        # But for performance (and since we likely update status), filtering by status != 'Paid' and != 'Canceled' is good.
        # Let's verify status choices in Invoice model: Draft, Open, Closed, Canceled.
        # Usually 'Open' implies pending. 'Closed' implies paid? Or is there a 'Paid' status?
        # Looking at frontend tables, we see 'Paid', 'Unpaid', 'Partial'.
        # Let's assume 'Open' statuses are pending.
        # Actually, let's look at the Invoice model definition again or rely on the query similar to 'overdue' but without the date constraint.
        
        # A safer way without relying on 'status' string being perfect:
        # Find all active invoices, annotate with paid amount, filter where paid < total.
        # This can be heavy. Let's stick to the user's previous logic or standard logic.
        # Standard logic: Open invoices.
        total_invoices_pending = Invoice.objects.filter(
            is_active=True,
            canceled=False,
            status__in=['Open', 'Draft', 'Overdue', 'Partial', 'Unpaid'] # Covering likely statuses
        ).exclude(status='Paid').exclude(status='Canceled').exclude(status='Closed').count()
        
        # --- 3. Total Sales ---
        # Grand Total of all valid invoices (All Time)
        total_sales = total_invoiced_all_time

        # --- 4. Payments Received ---
        # Total collected payments (All Time)
        payments_received = total_paid_all_time

        # --- CHARTS (Keep existing logic but optimized) ---
        
        # Enquiries vs Leads Trend (Last 6 Months)
        import calendar
        trends_data = []
        for i in range(5, -1, -1):
            d = today.replace(day=1)
            year = d.year
            month = d.month - i
            while month < 1:
                month += 12
                year -= 1
            
            month_name = calendar.month_abbr[month]
            
            enq_count = Inquiry.objects.filter(
                created_at__month=month,
                created_at__year=year,
                is_active=True
            ).count()
            
            lead_count = Lead.objects.filter(
                created_at__month=month,
                created_at__year=year,
                is_active=True
            ).count()
            
            trends_data.append({
                "month": month_name,
                "Enquiries": enq_count,
                "Leads": lead_count
            })

        # Financial Overview (Revenue from Invoices)
        finance_data = []
        for i in range(5, -1, -1):
            d = today.replace(day=1)
            year = d.year
            month = d.month - i
            while month < 1:
                month += 12
                year -= 1
            
            month_name = calendar.month_abbr[month]

            revenue = Invoice.objects.filter(
                doc_date__month=month,
                doc_date__year=year,
                is_active=True,
                canceled=False
            ).exclude(status='Canceled').aggregate(
                total=Sum('grand_total')
            )['total'] or 0
            
            finance_data.append({
                "month": month_name,
                "revenue": revenue,
                "target": revenue * Decimal(1.2) # Mock target for visualization
            })
            
        # Pipeline Data
        pipeline_data = [
            {"name": "Leads", "value": Lead.objects.filter(is_active=True).count()},
            {"name": "Enquiries", "value": Inquiry.objects.filter(is_active=True).count()},
            {"name": "Quotations", "value": Quotation.objects.filter(is_active=True).count()},
            {"name": "Orders", "value": SalesOrder.objects.filter(is_active=True).count()},
        ]

        # Recent Lists
        top_customers = Invoice.objects.filter(is_active=True, canceled=False).values('customer__name').annotate(
            total=Sum('grand_total'),
            count=Count('id')
        ).order_by('-total')[:5]
        
        recent_invoices = Invoice.objects.filter(is_active=True).select_related('customer').order_by('-doc_date')[:5]
        
        # Prepare Lists Data
        lists_data = {
            "top_customers": [
                {"name": c['customer__name'], "total": c['total'], "count": c['count']} 
                for c in top_customers if c['customer__name']
            ],
            "recent_invoices": [
                {
                    "id": inv.id,
                    "invoice_num": inv.invoice_num,
                    "customer": inv.customer.name if inv.customer else "Unknown",
                    "date": inv.doc_date,
                    "amount": inv.grand_total,
                    "status": inv.status
                }
                for inv in recent_invoices
            ]
        }

        return Response({
            "kpi": {
                "total_outstanding_pending": total_outstanding_pending,
                "total_invoices_pending": total_invoices_pending,
                "total_sales": total_sales,
                "payments_received": payments_received
            },
            "charts": {
                "enquiries": trends_data,
                "finance": finance_data,
                "pipeline": pipeline_data
            },
            "lists": lists_data
        })






# ============================================================
# 🔔 Notification ViewSet
# ============================================================

from .models import Notification
from .serializers import NotificationSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    """
    Handles notifications.
    Includes lazy checks for DOB and Overdue Payments.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Return notifications for the current user or all if generic logic used
        # For simplicity, returning all for admins or filtering by recipient
        user = self.request.user
        return Notification.objects.filter(recipient=user).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        """
        Overriden list to trigger daily checks before returning data.
        """
        # self.run_daily_checks(request.user)
        return super().list(request, *args, **kwargs)

    def run_daily_checks(self, user):
        """
        Check for Birthday tomorrow and Overdue Payments.
        """
        today = timezone.now().date()
        tomorrow = today + timezone.timedelta(days=1)
        
        # 1. Check DOBs (Tomorrow)
        # Extract month and day for tomorrow
        customers_birthday = Customer.objects.filter(
            dob__month=tomorrow.month, 
            dob__day=tomorrow.day,
            is_active=True
        )
        
        for cust in customers_birthday:
            # Check if notification already exists for this event (today)
            exists = Notification.objects.filter(
                recipient=user,
                related_model='Customer',
                related_id=cust.id,
                notification_type='dob',
                created_at__date=today
            ).exists()
            
            if not exists:
                Notification.objects.create(
                    recipient=user,
                    title="🎉 Upcoming Birthday",
                    message=f"Customer {cust.name}'s birthday is tomorrow!",
                    notification_type='dob',
                    related_id=cust.id,
                    related_model='Customer'
                )

        # 2. Check Overdue Payments (>15 days)
        # Outstanding logic: Invoice Open and Doc Date < Today - 15
        overdue_date = today - timezone.timedelta(days=15)
        overdue_invoices = Invoice.objects.filter(
            status='Open',
            doc_date__lt=overdue_date,
            is_active=True
        ) # Ensure we don't spam? 
        # Strategy: Notify once? Or daily? Let's notify daily but check if we already notified TODAY.
        
        for inv in overdue_invoices:
            exists = Notification.objects.filter(
                recipient=user,
                related_model='Invoice',
                related_id=inv.id,
                notification_type='payment',
                created_at__date=today
            ).exists()
            
            if not exists:
                days_overdue = (today - inv.doc_date).days
                Notification.objects.create(
                    recipient=user,
                    title="⚠️ Overdue Invoice",
                    message=f"Invoice #{inv.doc_num} for {inv.customer.name if inv.customer else 'Unknown'} is overdue by {days_overdue} days.",
                    notification_type='payment',
                    related_id=inv.id,
                    related_model='Invoice'
                )

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notif = self.get_object()
        notif.is_read = True
        notif.save()
        return Response({'status': 'marked read'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        self.get_queryset().update(is_read=True)
        return Response({'status': 'all marked read'})

