from rest_framework import routers
from django.urls import path, include
from .views import *
from .views_auth import LoginView, CompanyViewSet,AdminSignupView
from rest_framework_simplejwt.views import TokenRefreshView
from .views_auth import AdminSigninView
from .views_auth import CreateUserView
from .views_import import CustomerBulkImportView

router = routers.DefaultRouter()
router.register(r'customers', CustomerViewSet)
router.register(r'products', ProductViewSet)
router.register(r'enquiries', InquiryViewSet)
router.register(r'leads', LeadViewSet)
router.register(r'quotations', QuotationViewSet)
router.register(r'sales-orders', SalesOrderViewSet)
router.register(r'invoices', InvoiceViewSet)
router.register(r'payments', PaymentViewSet)
router.register(r'servicecalls', ServiceCallViewSet)
router.register(r'technicians', TechnicianViewSet)
router.register(r'technician-schedules', TechnicianScheduleViewSet)
router.register(r'equipment', EquipmentViewSet)
router.register(r'amc-contracts', AMCContractViewSet)
router.register(r'company', CompanyViewSet)
router.register(r'notifications', NotificationViewSet, basename='notifications')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
urlpatterns = [
    path("customers/import/", CustomerBulkImportView.as_view(), name="customer_bulk_import"),
    path("", include(router.urls)),
    path("admin/signin/", AdminSigninView.as_view(), name="admin_signin"),
    path("admin/signup/", AdminSignupView.as_view(), name="admin_signup"),
    path("login/", LoginView.as_view(), name="login"),
     path("create-user/", CreateUserView.as_view(), name="create_user"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
