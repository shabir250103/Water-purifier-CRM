from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

# ============================================================
# 👤 CUSTOM USER ADMIN
# ============================================================

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "email")
    ordering = ("username",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        ("Permissions", {
            "fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")
        }),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "role", "password1", "password2", "is_staff", "is_active"),
        }),
    )

# ============================================================
# 🧾 COMMON INLINE CLASSES (Document Lines)
# ============================================================

class InquiryLineInline(admin.TabularInline):
    model = InquiryLine
    extra = 0


class QuotationLineInline(admin.TabularInline):
    model = QuotationLine
    extra = 0


class SalesOrderLineInline(admin.TabularInline):
    model = SalesOrderLine
    extra = 0


class DeliveryLineInline(admin.TabularInline):
    model = DeliveryLine
    extra = 0


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0


# ============================================================
# 📋 DOCUMENT HEADER ADMINS
# ============================================================

@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ("doc_num", "customer", "doc_date", "status", "canceled")
    list_filter = ("status", "canceled")
    search_fields = ("doc_num", "customer__name")
    inlines = [InquiryLineInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ("doc_num", "customer", "doc_date", "status", "canceled")
    list_filter = ("status", "canceled")
    search_fields = ("doc_num", "customer__name")
    inlines = [QuotationLineInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ("doc_num", "customer", "doc_date", "status", "canceled")
    list_filter = ("status", "canceled")
    search_fields = ("doc_num", "customer__name")
    inlines = [SalesOrderLineInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("doc_num", "customer", "doc_date", "status", "canceled")
    list_filter = ("status", "canceled")
    search_fields = ("doc_num", "customer__name")
    inlines = [DeliveryLineInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("doc_num", "customer", "doc_date", "status", "canceled")
    list_filter = ("status", "canceled")
    search_fields = ("doc_num", "customer__name")
    inlines = [InvoiceLineInline]
    readonly_fields = ("created_at", "updated_at")


# ============================================================
# 🔄 DOC FLOW & TYPE (Audit)
# ============================================================

@admin.register(DocType)
class DocTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name")


@admin.register(DocFlowLink)
class DocFlowLinkAdmin(admin.ModelAdmin):
    list_display = (
        "source_doc_type", "source_doc_entry", "source_line",
        "target_doc_type", "target_doc_entry", "target_line",
        "qty_copied", "created_at"
    )
    list_filter = ("source_doc_type", "target_doc_type")
    search_fields = ("source_doc_entry", "target_doc_entry")


# ============================================================
# 💰 PAYMENTS & CUSTOMERS
# ============================================================

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice", "amount", "method", "paid_at")
    search_fields = ("invoice__doc_num", "method")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "created_at", "is_active")
    search_fields = ("name", "email", "phone")
    list_filter = ("is_active",)


from django.contrib import admin
from .models import Product

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "product_code",
        "brand",
        "series",
        "model_number",
        "voltage",
        "capacity",
        "warranty_months",
        "gst_rate",
        "created_at",
    )
    search_fields = ("product_code", "brand", "series", "model_number")
    list_filter = ("brand", "series", "gst_rate", "serial_managed", "batch_managed")



# ============================================================
# 🛠️ SERVICE MANAGEMENT
# ============================================================



@admin.register(ServiceCall)
class ServiceCallAdmin(admin.ModelAdmin):
    """✅ FIXED: ServiceCall Admin - updated for new SHORT CODE model"""
    list_display = ('call_num', 'customer', 'equipment', 'priority', 'status', 'created_at', 'is_active')
    list_filter = ('status', 'priority', 'is_active', 'created_at')
    search_fields = ('call_num', 'customer__name', 'equipment')
    readonly_fields = ('call_num', 'created_at', 'updated_at', 'closed_at')
    fieldsets = (
        ('Call Info', {
            'fields': ('call_num', 'customer', 'equipment', 'call_date')
        }),
        ('Details', {
            'fields': ('priority', 'status', 'contract', 'problem_description', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'closed_at'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    ordering = ['-created_at']

@admin.register(ServiceCallTechnician)
class ServiceCallTechnicianAdmin(admin.ModelAdmin):
    """Technician Assignment Admin"""
    list_display = ('id', 'service_call', 'technician', 'scheduled_date', 'status', 'duration_hours')
    list_filter = ('status', 'scheduled_date', 'created_at')
    search_fields = ('service_call__call_num', 'technician')
    readonly_fields = ('duration_hours', 'created_at', 'updated_at')
    ordering = ['-scheduled_date']

@admin.register(ServiceCallResolution)
class ServiceCallResolutionAdmin(admin.ModelAdmin):
    """Resolution Admin"""
    list_display = ('id', 'service_call', 'resolution_date', 'status', 'technician')
    list_filter = ('status', 'resolution_date', 'created_at')
    search_fields = ('service_call__call_num', 'technician')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ['-resolution_date']

@admin.register(ServiceCallExpense)
class ServiceCallExpenseAdmin(admin.ModelAdmin):
    """Expense Tracking Admin"""
    list_display = ('id', 'service_call', 'expense_type', 'description', 'quantity', 'unit_price', 'total_amount')
    list_filter = ('expense_type', 'created_at')
    search_fields = ('service_call__call_num', 'description')
    readonly_fields = ('total_amount', 'created_at', 'updated_at')
    ordering = ['-created_at']

@admin.register(ServiceCallActivity)
class ServiceCallActivityAdmin(admin.ModelAdmin):
    """Activity Log Admin"""
    list_display = ('id', 'service_call', 'activity_type', 'activity_date', 'performed_by')
    list_filter = ('activity_type', 'activity_date', 'created_at')
    search_fields = ('service_call__call_num', 'performed_by', 'notes')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ['-activity_date']


@admin.register(Technician)
class TechnicianAdmin(admin.ModelAdmin):
    """✅ FIXED: Removed non-existent created_at, updated_at"""
    list_display = ('code', 'name', 'phone', 'email', 'status', 'is_active')
    list_filter = ('status', 'is_active')
    search_fields = ('code', 'name', 'phone', 'email')
    fieldsets = (
        ("Info", {"fields": ("code", "name", "phone", "email", "status")}),
        ("Skills", {"fields": ("skills",)}),
        ("Status", {"fields": ("is_active",)}),
    )

@admin.register(TechnicianSchedule)
class TechnicianScheduleAdmin(admin.ModelAdmin):
    list_display = ('id', 'technician', 'service_call', 'start_time', 'end_time')
    list_filter = ('start_time', 'end_time')
    search_fields = ('technician__name', 'service_call__call_num')

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    """✅ FIXED: Removed non-existent created_at, updated_at"""
    list_display = ('serial', 'model', 'customer', 'purchase_date', 'is_active')
    list_filter = ('purchase_date', 'is_active')
    search_fields = ('serial', 'model', 'customer__name')
    fieldsets = (
        ("Equipment Info", {"fields": ("serial", "model", "customer", "purchase_date")}),
        ("Status", {"fields": ("is_active",)}),
    )

class AMCContractEquipmentInline(admin.TabularInline):
    model = AMCContractEquipment
    extra = 1

@admin.register(AMCContract)
class AMCContractAdmin(admin.ModelAdmin):
    """✅ FIXED: Updated for refactored AMCContract model"""
    list_display = ('contract_id', 'customer', 'contract_type', 'start_date', 'end_date', 'payment_status', 'is_active')
    list_filter = ('contract_type', 'payment_status', 'start_date', 'end_date', 'is_active')
    search_fields = ('contract_id', 'customer__name', 'customer__code')
    inlines = [AMCContractEquipmentInline]
    fieldsets = (
        ("Header", {"fields": ("contract_id", "customer", "contract_type")}),
        ("Dates", {"fields": ("start_date", "end_date")}),
        ("Values", {"fields": ("contract_value", "payment_terms", "response_time")}),
        ("Details", {"fields": ("coverage_details", "terms_conditions", "is_active")}),
        ("Renewal", {"fields": ("renewal_date", "revised_value", "payment_status")}),
    )

# ============================================================
# 🏢 COMPANY & LEADS
# ============================================================

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email", "created_at")
    search_fields = ("name", "phone", "email")
    readonly_fields = ("created_at",)
    fieldsets = (
        ("Company Info", {"fields": ("name", "phone", "email")}),
        ("Address", {"fields": ("address",)}),
        ("Tax", {"fields": ("gst_number",)}),
        ("Timestamps", {"fields": ("created_at",), "classes": ("collapse",)}),
    )

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    """✅ FIXED: Removed non-existent updated_at"""
    list_display = ('id', 'customer', 'source', 'status', 'created_at', 'is_active')
    list_filter = ('status', 'source', 'is_active')
    search_fields = ('customer__name', 'source')
    ordering = ['-created_at']

# ============================================================
# OLD MODELS (DEPRECATED)
# ============================================================

@admin.register(ServiceCallOld)
class ServiceCallOldAdmin(admin.ModelAdmin):
    """OLD Service Call Model - DEPRECATED"""
    list_display = ('id', 'customer', 'status', 'priority', 'date', 'is_active')
    list_filter = ('status', 'priority', 'is_active')
    search_fields = ('customer__name', 'description')
    readonly_fields = ('created_at', 'closed_at')
