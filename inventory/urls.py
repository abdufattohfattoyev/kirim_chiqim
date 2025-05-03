from django.urls import path
from . import views

urlpatterns = [
    path('ombor/', views.ombor_list, name='ombor_list'),
    path('warehouse/', views.warehouse_list, name='warehouse_list'),
    path('warehouse/create/', views.warehouse_create, name='warehouse_create'),
    path('warehouse/edit/<int:warehouse_id>/', views.warehouse_edit, name='warehouse_edit'),
    path('warehouse/delete/<int:warehouse_id>/', views.warehouse_delete, name='warehouse_delete'),
    path('warehouse/<int:warehouse_id>/', views.warehouse_detail, name='warehouse_detail'),
    path('warehouse/<int:warehouse_id>/export/', views.export_products_csv, name='export_products_csv'),
    path('warehouse/<int:warehouse_id>/import/', views.import_products_csv, name='import_products_csv'),
    path('kirim/', views.kirim_list, name='kirim_list'),
    path('get_products_by_warehouse/', views.get_products_by_warehouse, name='get_products_by_warehouse'),
    path('kirim/export/', views.export_incomings_csv, name='export_incomings_csv'),
    path('kirim/create/', views.kirim_create, name='kirim_create'),
    path('chiqim/', views.chiqim_list, name='chiqim_list'),
    path('chiqim/create/', views.chiqim_create, name='chiqim_create'),
    path('chiqim/export/', views.export_outgoings_csv, name='export_outgoings_csv'),
    path('product/create/', views.product_create, name='product_create'),
    path('product/edit/<int:product_id>/', views.product_edit, name='product_edit'),
    path('product/delete/<int:product_id>/', views.product_delete, name='product_delete'),

    #Loyihada CAtegory URLS-lar
    path('category/<int:category_id>/products/', views.category_products, name='category_products'),
    path('category/', views.category_list, name='category_list'),
    path('category/create/', views.category_create, name='category_create'),
    path('category/edit/<int:category_id>/', views.category_update, name='category_edit'),
    path('category/delete/<int:category_id>/', views.category_delete, name='category_delete'),
    # Agar loyihada /inventory/products/ URL’i bo‘lsa, uni qo‘shish
    path('products/', views.ombor_list, name='ombor_list'),
]