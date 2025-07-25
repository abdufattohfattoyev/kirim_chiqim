from django.urls import path
from . import views

urlpatterns = [
    # Omborlar
    path('warehouses/', views.ombor_list, name='warehouse_list'),
    path('warehouse/create/', views.warehouse_create, name='warehouse_create'),
    path('warehouse/edit/<int:warehouse_id>/', views.warehouse_edit, name='warehouse_edit'),
    path('warehouse/delete/<int:warehouse_id>/', views.warehouse_delete, name='warehouse_delete'),
    path('warehouse/<int:warehouse_id>/', views.warehouse_detail, name='warehouse_detail'),
    path('warehouse/<int:warehouse_id>/export/', views.export_products_csv, name='export_products_csv'),
    path('warehouse/<int:warehouse_id>/import/', views.import_products_csv, name='import_products_csv'),

    # Mahsulotlar
    path('products/', views.ombor_list, name='product_list'),
    path('product/create/', views.product_create, name='product_create'),
    path('product/edit/<int:product_id>/', views.product_edit, name='product_edit'),
    path('product/delete/<int:product_id>/', views.product_delete, name='product_delete'),

    # Kirimlar
    path('incomings/', views.kirim_list, name='incoming_list'),
    path('incomings/create/', views.kirim_create, name='incoming_create'),
    path('incomings/<int:kirim_id>/', views.kirim_detail, name='incoming_detail'),
    path('incomings/edit/<int:kirim_id>/', views.kirim_update, name='incoming_edit'),
    path('incomings/delete/<int:kirim_id>/', views.kirim_delete, name='incoming_delete'),
    path('incomings/export/', views.export_incomings_csv, name='export_incomings_csv'),

    # Chiqimlar
    path('outgoings/', views.chiqim_list, name='outgoing_list'),
    path('outgoings/create/', views.chiqim_create, name='outgoing_create'),
    path('outgoings/<int:outgoing_id>/', views.chiqim_detail, name='outgoing_detail'),
    path('outgoings/edit/<int:outgoing_id>/', views.chiqim_edit, name='outgoing_edit'),
    path('outgoings/delete/<int:outgoing_id>/', views.chiqim_delete, name='outgoing_delete'),
    path('outgoings/export/', views.export_outgoings_csv, name='export_outgoings_csv'),

    # AJAX so'rovlar
    path('get_products_by_warehouse/', views.get_products_by_warehouse, name='get_products_by_warehouse'),

    # Kategoriyalar
    path('categories/', views.category_list, name='category_list'),
    path('category/create/', views.category_create, name='category_create'),
    path('category/edit/<int:category_id>/', views.category_update, name='category_edit'),
    path('category/delete/<int:category_id>/', views.category_delete, name='category_delete'),
    path('category/<int:category_id>/products/', views.category_products, name='category_products'),
]