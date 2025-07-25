from django.urls import path
from . import views

urlpatterns = [
    # Ta'minotchilar
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/create/', views.supplier_create, name='supplier_create'),
    path('suppliers/edit/<int:pk>/', views.supplier_edit, name='supplier_edit'),
    path('suppliers/delete/<int:pk>/', views.supplier_delete, name='supplier_delete'),
    path('suppliers/import/', views.import_suppliers_csv, name='import_suppliers_csv'),  # Nom izchillashtirildi
    path('suppliers/export/', views.export_suppliers_csv, name='export_suppliers_csv'),  # Nom izchillashtirildi

    # Xaridorlar
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/create/', views.customer_create, name='customer_create'),
    path('customers/edit/<int:pk>/', views.customer_edit, name='customer_edit'),
    path('customers/delete/<int:pk>/', views.customer_delete, name='customer_delete'),
    path('customers/import/', views.import_customers_csv, name='import_customers_csv'),  # Nom izchillashtirildi
    path('customers/export/', views.export_customers_csv, name='export_customers_csv'),  # Nom izchillashtirildi

    # To'lovlar
    path('suppliers/payments/', views.supplier_payment_list, name='supplier_payment_list'),
    path('suppliers/payments/create/', views.supplier_payment_create, name='supplier_payment_create'),
    path('customers/payments/', views.customer_payment_list, name='customer_payment_list'),
    path('customers/payments/create/', views.customer_payment_create, name='customer_payment_create'),
]