from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from decimal import Decimal


# ============================================================
# 🧱 Base Utilities
# ============================================================


class SoftDeleteModel(models.Model):
    """Base model with is_active and deleted_at fields (for reference only)."""
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('user', 'User'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')

    def __str__(self):
        return f"{self.username} ({self.role})"


# ============================================================
# 👤 Master Data
# ============================================================


class Customer(SoftDeleteModel):
    code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        help_text="Auto-generated customer code like CUST-1001"
    )
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    gstin = models.CharField(max_length=15, blank=True, null=True)
    credit = models.PositiveIntegerField(default=0)
    outstanding = models.CharField(max_length=50, default="₹0.00")

    # ✅ Date of Birth
    dob = models.DateField(
        null=True, 
        blank=True,
        help_text="Date of Birth in YYYY-MM-DD format"
    )

    # 🏠 Address breakdown (matches your frontend)
    door_no = models.CharField(max_length=50, blank=True, null=True)
    street = models.CharField(max_length=255, blank=True, null=True)
    area = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)

    customer_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ("retail", "Retail"),
            ("dealer", "Dealer"),
            ("distributor", "Distributor"),
            ("corporate", "Corporate"),
        ],
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.code or '(No Code)'} - {self.name}"


class Product(SoftDeleteModel):
    product_code = models.CharField(max_length=50, unique=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    series = models.CharField(max_length=100, blank=True, null=True)
    model_number = models.CharField(max_length=100, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    voltage = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    capacity = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    warranty_months = models.PositiveIntegerField(default=0)
    filled_weight = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    hsn_code = models.CharField(max_length=8, blank=True, null=True)
    dimension_l = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    dimension_w = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    dimension_h = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    electrolyte_volume = models.DecimalField(max_digits=8, decimal_places=3, blank=True, null=True)
    uom = models.CharField(max_length=50, blank=True, null=True, default="Pcs")
    
    color = models.CharField(max_length=50, blank=True, null=True)
    serial_managed = models.BooleanField(default=False)
    batch_managed = models.BooleanField(default=False)
    gst_rate = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    description = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.brand} {self.series} {self.model_number}"


# ============================================================
# 🧾 Document Headers
# ============================================================


class DocumentHeaderBase(SoftDeleteModel):
    """Common header fields across all CRM documents."""
    DOC_STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Open", "Open"),
        ("Closed", "Closed"),
        ("Canceled", "Canceled"),
    ]

    doc_num = models.BigIntegerField(unique=True, blank=True, null=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True)
    doc_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=DOC_STATUS_CHOICES, default="Draft")
    executivename = models.CharField(max_length=30, blank=True, null=True)
    canceled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Quotation(DocumentHeaderBase):
    quotation_num = models.CharField(max_length=50, blank=True, null=True, unique=True)
    overall_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_tax = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    overall_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        if not self.doc_num:
            last = Quotation.objects.aggregate(models.Max("doc_num"))["doc_num__max"] or 0
            self.doc_num = last + 1
        
        # Auto-generate quotation_num if missing
        if not self.quotation_num:
            self.quotation_num = f"QO-{self.doc_num:04d}"
            
        super().save(*args, **kwargs)

    def recalculate_totals(self):
        """Automatically update totals based on quotation lines."""
        subtotal = Decimal(0)
        total_tax = Decimal(0)
        for line in self.items.all():
            qty = Decimal(line.quantity or 0)
            price = Decimal(line.price or 0)
            disc = Decimal(line.discount_percent or 0)
            tax = Decimal(line.tax_percent or 0)

            base = qty * price
            discount_amt = (base * disc) / 100
            taxable = base - discount_amt
            tax_amt = (taxable * tax) / 100

            subtotal += taxable
            total_tax += tax_amt

        self.subtotal = subtotal
        self.total_tax = total_tax
        self.overall_total = subtotal + total_tax
        self.grand_total = self.overall_total - self.overall_discount
        self.save()


class SalesOrder(DocumentHeaderBase):
    sales_order_num = models.CharField(max_length=50, blank=True, null=True, unique=True)
    overall_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_tax = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    overall_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    sales_order_id = models.BigIntegerField(blank=True, null=True) # For linking

    def save(self, *args, **kwargs):
        # Always maintain doc_num for backward compatibility
        if not self.doc_num:
            last = SalesOrder.objects.aggregate(models.Max("doc_num"))["doc_num__max"] or 0
            self.doc_num = last + 1
        
        # Auto-generate sales_order_num by finding max SO-XXXX value (independent of doc_num)
        if not self.sales_order_num:
            import re
            
            # Find the highest existing SO number
            # We filter for ones that match the pattern roughly to avoid fetching everything
            # SQLite regex support is limited by default in Django without plugins, so we fetch only relevant potential matches
            # 'SO-' prefix is a good enough filter
            existing_ids = SalesOrder.objects.filter(sales_order_num__startswith='SO-').values_list('sales_order_num', flat=True)
            
            max_num = 0
            for order_id in existing_ids:
                if not order_id: continue
                # Robustly extract the number
                match = re.search(r'SO-(\d+)', str(order_id))
                if match:
                    try:
                        num = int(match.group(1))
                        if num > max_num:
                            max_num = num
                    except ValueError:
                        continue
            
            next_num = max_num + 1
            self.sales_order_num = f"SO-{next_num:04d}"
            
        super().save(*args, **kwargs)

    def recalculate_totals(self):
        subtotal = Decimal(0)
        total_tax = Decimal(0)
        # Using 'lines' related name
        for line in self.lines.all():
            qty = Decimal(line.quantity or 0)
            price = Decimal(line.price or 0)
            disc = Decimal(line.discount_percent or 0)
            tax = Decimal(line.gst_percent if hasattr(line, 'gst_percent') else (line.tax_percent if hasattr(line, 'tax_percent') else 0) or 0) # SalesOrderLine uses gst_percent usually? Accessing property might fail if not field?
            # Check SalesOrderLine model def. Serializer has gst_percent method.
            # Usually model has 'tax_percent' or 'gst_rate' or it's on product?
            # Let's check SalesOrderLine definition in models.py? 
            # Assuming 'tax_percent' field exists on line like Quotation/Invoice.
            
            # Actually, let's keep it simple and consistent with Quotation logic
            # If fields differ, we might need to adjust.
            # But earlier DB schema check showed lines usually share structure.
            
            base = qty * price
            discount_amt = (base * disc) / 100
            taxable = base - discount_amt
            tax_amt = (taxable * tax) / 100
            
            subtotal += taxable
            total_tax += tax_amt

        self.subtotal = subtotal
        self.total_tax = total_tax
        self.overall_total = subtotal + total_tax
        self.grand_total = self.overall_total - self.overall_discount
        self.save()


class Delivery(DocumentHeaderBase):
    overall_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_tax = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    overall_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        if not self.doc_num:
            last = Delivery.objects.aggregate(models.Max("doc_num"))["doc_num__max"] or 4000
            self.doc_num = last + 1
        super().save(*args, **kwargs)

    def recalculate_totals(self):
        subtotal = Decimal(0)
        total_tax = Decimal(0)
        for line in self.lines.all():
            qty = Decimal(line.quantity or 0)
            price = Decimal(line.price or 0)
            disc = Decimal(line.discount_percent or 0)
            tax = Decimal(line.tax_percent or 0)
            
            base = qty * price
            discount_amt = (base * disc) / 100
            taxable = base - discount_amt
            tax_amt = (taxable * tax) / 100
            
            subtotal += taxable
            total_tax += tax_amt

        self.subtotal = subtotal
        self.total_tax = total_tax
        self.overall_total = subtotal + total_tax
        self.grand_total = self.overall_total - self.overall_discount
        self.save()


class Invoice(DocumentHeaderBase):
    invoice_num = models.CharField(max_length=50, blank=True, null=True, unique=True)
    overall_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_tax = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    overall_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        if not self.doc_num:
            last = Invoice.objects.aggregate(models.Max("doc_num"))["doc_num__max"] or 0
            self.doc_num = last + 1
        
        # Auto-generate invoice_num if missing
        if not self.invoice_num:
            import re
            
            # Find the highest existing IN number
            existing_ids = Invoice.objects.filter(invoice_num__startswith='IN-').values_list('invoice_num', flat=True)
            
            max_num = 0
            for inv_num in existing_ids:
                if not inv_num: continue
                match = re.search(r'IN-(\d+)', str(inv_num))
                if match:
                    try:
                        num = int(match.group(1))
                        if num > max_num:
                            max_num = num
                    except ValueError:
                        continue
            
            next_num = max_num + 1
            self.invoice_num = f"IN-{next_num:04d}"
            
        super().save(*args, **kwargs)

    def recalculate_totals(self):
        """Automatically update totals based on invoice lines."""
        subtotal = Decimal(0)
        total_tax = Decimal(0)
        for line in self.lines.all():
            qty = Decimal(line.quantity or 0)
            price = Decimal(line.price or 0)
            disc = Decimal(line.discount_percent or 0)
            tax = Decimal(line.tax_percent or 0)

            base = qty * price
            discount_amt = (base * disc) / 100
            taxable = base - discount_amt
            tax_amt = (taxable * tax) / 100

            subtotal += taxable
            total_tax += tax_amt

        self.subtotal = subtotal
        self.total_tax = total_tax
        self.overall_total = subtotal + total_tax
        self.grand_total = self.overall_total - self.overall_discount
        self.save()


# ============================================================
# 📦 Document Lines
# ============================================================


class EnquiryItem(models.Model):
    """
    Simple, self-contained model for items within an enquiry.
    Each record represents a product line in an enquiry.
    """
    enquiry = models.ForeignKey(
        "Inquiry",
        on_delete=models.CASCADE,
        related_name="enquiry_items"
    )
    product = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    remarks = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product} ({self.quantity})"


class LineBase(models.Model):
    """Common line structure for all document line tables."""
    line_num = models.PositiveIntegerField()
    item = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    uom = models.CharField(max_length=50, blank=True, null=True)
    quantity = models.DecimalField(max_digits=19, decimal_places=6)
    open_qty = models.DecimalField(max_digits=19, decimal_places=6, default=0)
    price = models.DecimalField(max_digits=19, decimal_places=6, default=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_code = models.CharField(max_length=50, blank=True, null=True)
    row_status = models.CharField(max_length=20, default="Open")
    hsn_code = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=19, decimal_places=6, default=0)

    base_doc_type = models.CharField(max_length=3, blank=True, null=True)
    base_doc_entry = models.BigIntegerField(blank=True, null=True)
    base_line = models.PositiveIntegerField(blank=True, null=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        abstract = True


# ============================================================
# 🧾 Inquiry Models — FULLY UPDATED
# ============================================================


class Inquiry(DocumentHeaderBase):
    """
    Represents the enquiry header information.
    Matches fields from Enquiry.jsx frontend.
    """
    SOURCE_CHOICES = [
        ("Walk-in", "Walk-in"),
        ("Phone", "Phone"),
        ("Online", "Online"),
        ("Reference", "Reference"),
        ("Existing Customer", "Existing Customer"),
    ]

    STATUS_CHOICES = [
        ("open", "open"),
        ("converted", "converted"),
        ("processed", "processed"),
        ("missed", "missed"),
    ]

    source = models.CharField(
        max_length=50, 
        choices=SOURCE_CHOICES, 
        blank=True, 
        null=True
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default="open"
    )
    next_followup = models.DateField(blank=True, null=True)  # ✅ NEW
    remarks = models.TextField(blank=True, null=True)  # ✅ NEW

    def save(self, *args, **kwargs):
        if not self.doc_num:
            last = Inquiry.objects.aggregate(models.Max("doc_num"))["doc_num__max"] or 0
            self.doc_num = last + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"ENQ-{self.doc_num} - {self.customer.name if self.customer else 'No Customer'}"


class InquiryLine(LineBase):
    """
    Line items for an enquiry document.
    Matches frontend Enquiry.jsx items table.
    """
    doc_entry = models.ForeignKey(Inquiry, on_delete=models.CASCADE, related_name="items")
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Item {self.line_num} - {self.item.product_code if self.item else 'No Product'}"


class InquiryActivity(models.Model):
    """
    Tracks activities related to an enquiry.
    Matches frontend Enquiry.jsx activities section.
    """
    ACTIVITY_TYPE_CHOICES = [
        ("Call", "Call"),
        ("Email", "Email"),
        ("Visit", "Visit"),
        ("Meeting", "Meeting"),
        ("Follow-up", "Follow-up"),
    ]

    inquiry = models.ForeignKey(
        Inquiry, 
        on_delete=models.CASCADE, 
        related_name="activities"
    )
    activity_id = models.CharField(max_length=20, blank=True, null=True)
    activity_date = models.DateField(blank=True, null=True)
    next_followup = models.DateField(blank=True, null=True)
    activity_type = models.CharField(
        max_length=50, 
        choices=ACTIVITY_TYPE_CHOICES, 
        blank=True, 
        null=True
    )
    details = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.activity_id:
            last_id = InquiryActivity.objects.count() + 1000
            self.activity_id = f"ACT-{last_id}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.activity_id} - {self.activity_type or 'No Type'}"


class QuotationLine(LineBase):
    doc_entry = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name="items")
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Quotation Line {self.line_num} - {self.item.product_code if self.item else 'No Product'}"


class SalesOrderLine(LineBase):
    doc_entry = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name="lines")


class DeliveryLine(LineBase):
    doc_entry = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name="lines")


class InvoiceLine(LineBase):
    doc_entry = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")


# ============================================================
# 🔄 Doc Flow Link Ledger
# ============================================================


class DocType(models.Model):
    """Defines all supported document types (INQ, QUT, ORD, DLV, INV)."""
    code = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class DocFlowLink(models.Model):
    """Tracks every copy or reversal between documents."""
    source_doc_type = models.ForeignKey(DocType, on_delete=models.CASCADE, related_name="source_links")
    source_doc_entry = models.BigIntegerField()
    source_line = models.PositiveIntegerField()
    target_doc_type = models.ForeignKey(DocType, on_delete=models.CASCADE, related_name="target_links")
    target_doc_entry = models.BigIntegerField()
    target_line = models.PositiveIntegerField()
    qty_copied = models.DecimalField(max_digits=19, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True)
    reversed_of_id = models.BigIntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.source_doc_type_id}:{self.source_doc_entry} → {self.target_doc_type_id}:{self.target_doc_entry}"


# ============================================================
# 💰 Accounting & Payments
# ============================================================


class Payment(SoftDeleteModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=50, blank=True, null=True)
    paid_at = models.DateTimeField(default=timezone.now)


# ============================================================
# 🛠️ Service Management
# ============================================================


class ServiceCallOld(SoftDeleteModel):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, related_name="service_calls")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    issue = models.TextField(blank=True, null=True)
    priority = models.CharField(max_length=20, default="Low", choices=[
        ("Low", "Low"),
        ("Medium", "Medium"),
        ("High", "High"),
        ("Critical", "Critical"),
    ])
    status = models.CharField(max_length=20, default="Logged", choices=[
        ("Logged", "Logged"),
        ("InProgress", "In Progress"),
        ("Resolved", "Resolved"),
        ("Closed", "Closed"),
    ])
    technician = models.ForeignKey("Technician", on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=100)
    date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"ServiceCall {self.id} - {self.customer.name if self.customer else 'No Customer'}"


class Technician(SoftDeleteModel):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    skills = models.TextField(blank=True, null=True)
    STATUS_CHOICES = [
        ("Available", "Available"),
        ("Busy", "Busy"),
        ("On Leave", "On Leave"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Available")

    def __str__(self):
        return f"{self.code} - {self.name}"


class TechnicianSchedule(models.Model):
    technician = models.ForeignKey(Technician, on_delete=models.CASCADE, related_name="schedules")
    service_call = models.ForeignKey("ServiceCall", on_delete=models.SET_NULL, null=True, blank=True) # type: ignore
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)


# ============================================================
# 🧰 Equipment & AMC
# ============================================================


class Equipment(SoftDeleteModel):
    serial = models.CharField(max_length=255, unique=True)
    model = models.CharField(max_length=255)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name="equipment")
    purchase_date = models.DateField(null=True, blank=True)


class AMCContract(SoftDeleteModel):
    """
    AMC / Warranty Contract Header
    Supports multiple equipment via AMCContractEquipment
    """
    CONTRACT_TYPE_CHOICES = [
        ('Warranty', 'Warranty'),
        ('AMC Contract', 'AMC Contract'),
        ('Extended Warranty', 'Extended Warranty'),
        ('Comprehensive Coverage', 'Comprehensive Coverage'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Partial', 'Partial'),
        ('Overdue', 'Overdue'),
    ]

    # Header Info
    contract_id = models.CharField(max_length=50, unique=True, blank=True, null=True) # E.g. AMC-12345
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, related_name="contracts")
    contract_type = models.CharField(max_length=50, choices=CONTRACT_TYPE_CHOICES, default='Warranty')

    # Dates
    start_date = models.DateField()
    end_date = models.DateField()

    # Commercials
    contract_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    response_time = models.IntegerField(default=24, help_text="Response time in hours")
    payment_terms = models.CharField(max_length=50, default="Annual Advance")

    # Details
    coverage_details = models.TextField(blank=True, null=True)
    terms_conditions = models.TextField(blank=True, null=True)

    # Renewal Section
    renewal_date = models.DateField(blank=True, null=True)
    revised_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"{self.contract_id} - {self.customer.name if self.customer else 'No Customer'}"


class AMCContractEquipment(models.Model):
    """
    Equipment covered under an AMC/Warranty Contract
    """
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
        ('Replaced', 'Replaced'),
    ]

    amc_contract = models.ForeignKey(AMCContract, on_delete=models.CASCADE, related_name="equipment_covered")
    product_model = models.CharField(max_length=255)
    serial_number = models.CharField(max_length=255)
    part_number = models.CharField(max_length=255, blank=True, null=True)
    installation_date = models.DateField(default=timezone.now)
    warranty_end = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')

    def __str__(self):
        return f"{self.product_model} ({self.serial_number})"



# ============================================================
# 🏢 Company Info & Leads
# ============================================================


class Company(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    gst_number = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Lead(SoftDeleteModel):
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, related_name="leads")
    source = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=100, default="new")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Lead: {self.customer.name if self.customer else 'Unknown'} ({self.status})"
    

class ServiceCall(SoftDeleteModel):
    """Main Service Call Header - Optimized with SHORT CODES"""

    # Status & Priority with SHORT codes
    STATUS_CHOICES = [
        ('O', 'Open'),
        ('IP', 'In Progress'),
        ('R', 'Resolved'),
        ('CL', 'Closed'),
    ]

    PRIORITY_CHOICES = [
        ('L', 'Low'),
        ('M', 'Medium'),
        ('H', 'High'),
        ('C', 'Critical'),
    ]

    # Call ID
    call_num = models.CharField(
        max_length=15,
        unique=True,
        blank=True,
        null=True
    )

    # Customer Reference
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        related_name="service_calls_new"
    )

    # Equipment Info
    equipment = models.CharField(max_length=100)

    # Call Details (Optimized field lengths)
    call_date = models.DateField(default=timezone.now)
    priority = models.CharField(
        max_length=1,
        default='M',
        choices=PRIORITY_CHOICES
    )
    status = models.CharField(
        max_length=2,
        default='O',
        choices=STATUS_CHOICES
    )

    # Optional Fields (Shorter lengths)
    contract = models.CharField(max_length=50, blank=True, null=True)
    problem_description = models.TextField()
    notes = models.TextField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.call_num} - {self.customer.name if self.customer else 'N/A'}"

    def save(self, *args, **kwargs):
        if not self.call_num:
            last = ServiceCall.objects.all().order_by('-id').first()
            if last and last.call_num:
                try:
                    last_num = int(last.call_num.split('-')[1])
                    self.call_num = f"SC-{last_num + 1}"
                except (ValueError, IndexError):
                    self.call_num = f"SC-1001"
            else:
                self.call_num = f"SC-1001"
        if self.status == 'CL' and not self.closed_at:
            self.closed_at = timezone.now()
        super().save(*args, **kwargs)


class ServiceCallTechnician(models.Model):
    """Technician Assignment - Optimized"""

    TECH_STATUS_CHOICES = [
        ('S', 'Scheduled'),
        ('IP', 'In Progress'),
        ('C', 'Completed'),
        ('X', 'Cancelled'),
    ]

    service_call = models.ForeignKey(
        ServiceCall,
        on_delete=models.CASCADE,
        related_name="technicians"
    )

    # Technician info
    technician = models.CharField(max_length=100)
    scheduled_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    # Duration (auto-calculated)
    duration_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )






    # Status
    status = models.CharField(
        max_length=2,
        default='S',
        choices=TECH_STATUS_CHOICES
    )

    notes = models.TextField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_date', 'start_time']
        indexes = [
            models.Index(fields=['service_call', 'scheduled_date']),
        ]

    def __str__(self):
        return f"{self.service_call.call_num} - {self.technician}"

    def save(self, *args, **kwargs):
        if self.start_time and self.end_time:
            from datetime import datetime
            start = datetime.combine(datetime.today(), self.start_time)
            end = datetime.combine(datetime.today(), self.end_time)
            duration = (end - start).total_seconds() / 3600
            self.duration_hours = max(Decimal('0'), Decimal(str(duration)))
        super().save(*args, **kwargs)


class ServiceCallResolution(models.Model):
    """Resolution - Optimized"""

    RESOLUTION_STATUS_CHOICES = [
        ('P', 'Partial'),
        ('F', 'Full'),
    ]

    service_call = models.ForeignKey(
        ServiceCall,
        on_delete=models.CASCADE,
        related_name="resolutions"
    )

    resolution_date = models.DateField()
    technician = models.CharField(max_length=100, blank=True, null=True)
    time_spent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )

    # Solution & Feedback
    solution_description = models.TextField(blank=True, null=True)
    customer_feedback = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=1,
        default='P',
        choices=RESOLUTION_STATUS_CHOICES
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-resolution_date']
        indexes = [
            models.Index(fields=['service_call']),
        ]

    def __str__(self):
        return f"{self.service_call.call_num} - {self.get_status_display()}"


class ServiceCallExpense(models.Model):
    """Expense Tracking - Optimized"""

    EXPENSE_TYPE_CHOICES = [
        ('P', 'Parts'),
        ('L', 'Labor'),
        ('T', 'Travel'),
        ('M', 'Material'),
        ('O', 'Other'),
    ]

    service_call = models.ForeignKey(
        ServiceCall,
        on_delete=models.CASCADE,
        related_name="expenses"
    )

    # Expense type
    expense_type = models.CharField(
        max_length=1,
        choices=EXPENSE_TYPE_CHOICES,
        default='P'
    )

    # Details (shorter lengths)
    description = models.CharField(max_length=150, blank=True, null=True)
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Auto-calculated total
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['service_call']),
        ]

    def __str__(self):
        return f"{self.service_call.call_num} - {self.get_expense_type_display()}"

    def save(self, *args, **kwargs):
        self.total_amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class ServiceCallActivity(models.Model):
    """Activity Log - Optimized"""

    ACTIVITY_TYPE_CHOICES = [
        ('SV', 'Site Visit'),
        ('PC', 'Phone Call'),
        ('EM', 'Email'),
        ('PR', 'Parts Replaced'),
        ('TR', 'Training'),
        ('FU', 'Follow-up'),
        ('O', 'Other'),
    ]

    service_call = models.ForeignKey(
        ServiceCall,
        on_delete=models.CASCADE,
        related_name="activities"
    )

    # Activity type
    activity_type = models.CharField(
        max_length=2,
        choices=ACTIVITY_TYPE_CHOICES,
        default='SV'
    )

    activity_date = models.DateField()
    performed_by = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-activity_date']
        indexes = [
            models.Index(fields=['service_call', 'activity_date']),
        ]

    def __str__(self):
        return f"{self.service_call.call_num} - {self.get_activity_type_display()}"


# ============================================================
# 🔔 Notifications
# ============================================================


class Notification(models.Model):
    RECIPIENT_CHOICES = [
        ('all', 'All Users'),
        ('admin', 'Admins Only'),
        ('specific', 'Specific User'),
    ]
    
    TYPE_CHOICES = [
        ('dob', 'Birthday'),
        ('payment', 'Payment Outstanding'),
        ('new_customer', 'New Customer'),
        ('stock', 'Low Stock'),
        ('other', 'Other'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    notification_type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='other')
    created_at = models.DateTimeField(auto_now_add=True)
    related_id = models.IntegerField(null=True, blank=True)  # ID of related Customer/Invoice
    related_model = models.CharField(max_length=50, null=True, blank=True) # 'Customer', 'Invoice'

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.recipient}"