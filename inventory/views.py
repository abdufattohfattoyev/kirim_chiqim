from datetime import date
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils.dateparse import parse_date
from django.db import transaction
import csv
import pandas as pd

from .models import Product, Category, Incoming, IncomingItem, Outgoing, OutgoingItem, Warehouse
from partners.models import Supplier, Customer
from .forms import (
    IncomingForm, OutgoingForm, ProductForm, CategoryForm, WarehouseForm,
    IncomingItemFormSetFactory, OutgoingItemFormSet
)


def handle_ajax_response(success, message, data=None, status=200):
    """AJAX javoblarni qaytarish uchun yordamchi funksiya"""
    response_data = {'status': 'success' if success else 'error', 'message': message}
    if data:
        response_data.update(data)
    return JsonResponse(response_data, status=status if not success else 200)


def get_paginated_data(request, queryset, per_page=10):
    """Paginatsiya uchun yordamchi funksiya"""
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def apply_search_filter(queryset, query, fields):
    """Qidiruv filtri qo'llash uchun yordamchi funksiya"""
    if query:
        q_objects = Q()
        for field in fields:
            q_objects |= Q(**{f"{field}__icontains": query})
        return queryset.filter(q_objects)
    return queryset


def apply_date_filter(queryset, start_date, end_date, date_field='date'):
    """Sana filtri qo'llash uchun yordamchi funksiya"""
    if start_date and end_date:
        start_date = parse_date(start_date)
        end_date = parse_date(end_date)
        if start_date and end_date:
            return queryset.filter(**{f"{date_field}__range": [start_date, end_date]})
    return queryset


# WAREHOUSE VIEWS
@login_required
def ombor_list(request):
    query = request.GET.get('q')
    warehouses = Warehouse.objects.all().order_by('name')

    warehouses = apply_search_filter(warehouses, query, ['name'])

    warehouse_list = [{
        'warehouse': warehouse,
        'product_count': Product.objects.filter(warehouse=warehouse).count(),
    } for warehouse in warehouses]

    page_obj = get_paginated_data(request, warehouse_list)

    return render(request, 'inventory/ombor_list.html', {
        'page_obj': page_obj,
        'query': query,
    })


@login_required
def warehouse_detail(request, warehouse_id):
    warehouse = get_object_or_404(Warehouse, id=warehouse_id)
    query = request.GET.get('q')
    products = Product.objects.filter(warehouse=warehouse).order_by('name')

    products = apply_search_filter(products, query, ['name', 'category__name'])
    page_obj = get_paginated_data(request, products)

    return render(request, 'inventory/warehouse_detail.html', {
        'warehouse': warehouse,
        'page_obj': page_obj,
        'query': query,
        'product_form': ProductForm(initial={'warehouse': warehouse}),
    })


@login_required
def warehouse_create(request):
    if request.method == 'POST':
        form = WarehouseForm(request.POST)
        if form.is_valid():
            warehouse = form.save(commit=False)
            warehouse.created_by = request.user
            warehouse.save()

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return handle_ajax_response(True, "Ombor muvaffaqiyatli qo'shildi.", {
                    'warehouse': {
                        'id': warehouse.id,
                        'name': warehouse.name,
                        'created_at': warehouse.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    }
                })

            messages.success(request, "Ombor muvaffaqiyatli qo'shildi.")
            return redirect('ombor_list')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return handle_ajax_response(False, "Ombor qo'shishda xatolik yuz berdi.",
                                            {'errors': form.errors.as_json()}, 400)
            messages.error(request, f"Forma to'ldirishda xatolik: {form.errors}")
    else:
        form = WarehouseForm()

    return render(request, 'inventory/warehouse_form.html', {'form': form})


@login_required
def warehouse_edit(request, warehouse_id):
    warehouse = get_object_or_404(Warehouse, id=warehouse_id)

    if request.method == 'POST':
        form = WarehouseForm(request.POST, instance=warehouse)
        if form.is_valid():
            warehouse = form.save()

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return handle_ajax_response(True, "Ombor muvaffaqiyatli tahrirlandi.", {
                    'warehouse': {
                        'id': warehouse.id,
                        'name': warehouse.name,
                        'created_at': warehouse.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    }
                })

            messages.success(request, "Ombor muvaffaqiyatli tahrirlandi.")
            return redirect('ombor_list')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return handle_ajax_response(False, "Ombor tahrirlashda xatolik yuz berdi.",
                                            {'errors': form.errors.as_json()}, 400)
            messages.error(request, f"Forma to'ldirishda xatolik: {form.errors}")
    else:
        form = WarehouseForm(instance=warehouse)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return handle_ajax_response(True, "", {
                'form': {
                    'name': warehouse.name,
                    'address': warehouse.address or '',
                }
            })

    return render(request, 'inventory/warehouse_form.html', {'form': form})


@login_required
def warehouse_delete(request, warehouse_id):
    warehouse = get_object_or_404(Warehouse, id=warehouse_id)

    if request.method == 'POST':
        if Product.objects.filter(warehouse=warehouse).exists():
            message = "Bu omborda mahsulotlar mavjud, o'chirib bo'lmaydi."
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return handle_ajax_response(False, message, status=400)
            messages.error(request, message)
            return redirect('ombor_list')

        warehouse.delete()
        message = "Ombor muvaffaqiyatli o'chirildi."

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return handle_ajax_response(True, message, {'warehouse_id': warehouse_id})

        messages.success(request, message)
        return redirect('ombor_list')

    return render(request, 'inventory/warehouse_confirm_delete.html', {'warehouse': warehouse})


# PRODUCT VIEWS
def get_product_data(product):
    """Mahsulot ma'lumotlarini qaytarish uchun yordamchi funksiya"""
    return {
        'id': product.id,
        'name': product.name,
        'warehouse': product.warehouse.name,
        'category': product.category.name if product.category else 'Kategoriyasiz',
        'image': product.image.url if product.image else '',
        'quantity': product.quantity,
        'minimum_quantity': product.minimum_quantity,
    }


@login_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            product.save()

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return handle_ajax_response(True, "Mahsulot muvaffaqiyatli qo'shildi.",
                                            {'product': get_product_data(product)})

            messages.success(request, "Mahsulot muvaffaqiyatli qo'shildi.")
            return redirect('warehouse_detail', warehouse_id=product.warehouse.id)
        else:
            error_message = next(iter(form.errors.values()))[0] if form.errors else "Noma'lum xatolik"
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return handle_ajax_response(False, error_message, {'errors': form.errors.as_json()}, 400)
            messages.error(request, "Forma to'ldirishda xatolik yuz berdi.")
    else:
        form = ProductForm()

    return render(request, 'inventory/warehouse_detail.html', {'form': form})


@login_required
def product_edit(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return handle_ajax_response(True, "Mahsulot muvaffaqiyatli tahrirlandi.",
                                            {'product': get_product_data(product)})

            messages.success(request, "Mahsulot muvaffaqiyatli tahrirlandi.")
            return redirect('warehouse_detail', warehouse_id=product.warehouse.id)
        else:
            error_message = next(iter(form.errors.values()))[0] if form.errors else "Noma'lum xatolik"
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return handle_ajax_response(False, error_message, {'errors': form.errors.as_json()}, 400)
            messages.error(request, "Forma to'ldirishda xatolik yuz berdi.")
    else:
        form = ProductForm(instance=product)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return handle_ajax_response(True, "", {
                'form': {
                    'name': product.name,
                    'warehouse': product.warehouse.id,
                    'category': product.category.id if product.category else '',
                    'image': product.image.url if product.image else '',
                    'quantity': product.quantity,
                    'minimum_quantity': product.minimum_quantity,
                    'unit': product.unit,
                    'barcode': product.barcode or '',
                }
            })

    return render(request, 'inventory/warehouse_detail.html', {'form': form, 'product': product})


@login_required
def product_delete(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    warehouse_id = product.warehouse.id

    if request.method == 'POST':
        if (IncomingItem.objects.filter(product=product).exists() or
                OutgoingItem.objects.filter(product=product).exists()):
            message = "Bu mahsulot kirim yoki chiqimlarda ishlatilgan, o'chirib bo'lmaydi."
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return handle_ajax_response(False, message, status=400)
            messages.error(request, message)
        else:
            product.delete()
            message = "Mahsulot muvaffaqiyatli o'chirildi."
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return handle_ajax_response(True, message, {'product_id': product_id})
            messages.success(request, message)

        return redirect('warehouse_detail', warehouse_id=warehouse_id)

    return render(request, 'inventory/product_confirm_delete.html', {'product': product})


# CSV EXPORT/IMPORT
@login_required
def export_products_csv(request, warehouse_id):
    warehouse = get_object_or_404(Warehouse, id=warehouse_id)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="products_{warehouse.name}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Mahsulot nomi', 'Ombor', 'Kategoriya', 'Miqdor', 'O\'lchov birligi', 'Shtrix kod'])

    for product in Product.objects.filter(warehouse=warehouse):
        writer.writerow([
            product.name,
            product.warehouse.name,
            product.category.name if product.category else '-',
            product.quantity,
            product.unit,
            product.barcode or '-',
        ])

    return response


@login_required
def import_products_csv(request, warehouse_id):
    warehouse = get_object_or_404(Warehouse, id=warehouse_id)

    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        if not csv_file.name.endswith('.csv'):
            messages.error(request, "Faqat CSV fayllarni yuklash mumkin.")
            return redirect('warehouse_detail', warehouse_id=warehouse_id)

        try:
            data = pd.read_csv(csv_file)
            with transaction.atomic():
                for _, row in data.iterrows():
                    category = None
                    category_name = row.get('Kategoriya')
                    if category_name and category_name != '-':
                        category, _ = Category.objects.get_or_create(name=category_name)

                    Product.objects.update_or_create(
                        name=row['Mahsulot nomi'],
                        warehouse=warehouse,
                        defaults={
                            'category': category,
                            'quantity': row['Miqdor'],
                            'unit': row.get('O\'lchov birligi', 'dona'),
                            'barcode': row.get('Shtrix kod', None),
                            'created_by': request.user,
                        }
                    )
            messages.success(request, "Mahsulotlar muvaffaqiyatli import qilindi.")
        except Exception as e:
            messages.error(request, f"Import xatosi: {str(e)}")

    return redirect('warehouse_detail', warehouse_id=warehouse_id)


# INCOMING VIEWS
@login_required
def kirim_list(request):
    query = request.GET.get('q')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    warehouse_id = request.GET.get('warehouse')

    incomings = Incoming.objects.all().order_by('-date')

    if warehouse_id:
        incomings = incomings.filter(warehouse_id=warehouse_id)
    incomings = apply_search_filter(incomings, query, ['supplier__name', 'note'])
    incomings = apply_date_filter(incomings, start_date, end_date)

    page_obj = get_paginated_data(request, incomings)

    return render(request, 'inventory/kirim_list.html', {
        'page_obj': page_obj,
        'query': query,
        'start_date': start_date,
        'end_date': end_date,
        'warehouse_id': warehouse_id,
        'warehouses': Warehouse.objects.all(),
    })


@login_required
def kirim_create(request):
    if request.method == 'POST':
        form = IncomingForm(request.POST)
        warehouse_id = request.POST.get('warehouse')
        warehouse = get_object_or_404(Warehouse, id=warehouse_id) if warehouse_id else None
        formset = IncomingItemFormSetFactory(request.POST, instance=Incoming(), warehouse=warehouse)

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    incoming = form.save(commit=False)
                    incoming.created_by = request.user
                    incoming.save()

                    formset.instance = incoming
                    instances = formset.save(commit=False)

                    for instance in instances:
                        instance.incoming = incoming
                        instance.save()  # Bu yerda IncomingItem save metodi mahsulot miqdorini yangilaydi

                    for obj in formset.deleted_objects:
                        obj.delete()

                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return handle_ajax_response(True, "Kirim muvaffaqiyatli qo'shildi.", {
                            'incoming': {
                                'id': incoming.id,
                                'warehouse': incoming.warehouse.name,
                                'supplier': incoming.supplier.name if incoming.supplier else 'Noma\'lum',
                                'date': incoming.date.strftime('%Y-%m-%d'),
                                'total_amount': float(incoming.total_amount),
                                'paid_amount': float(incoming.paid_amount),
                                'debt': float(incoming.debt),
                            }
                        })

                    messages.success(request, "Kirim muvaffaqiyatli qo'shildi.")
                    return redirect('incoming_list')

            except Exception as e:
                error_msg = f"Xatolik yuz berdi: {str(e)}"
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return handle_ajax_response(False, error_msg, status=400)
                messages.error(request, error_msg)
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return handle_ajax_response(False, "Forma to'ldirishda xatolik yuz berdi.",
                                            {'errors': form.errors.as_json() if form.errors else formset.errors}, 400)
            messages.error(request, "Forma to'ldirishda xatolik yuz berdi.")
    else:
        form = IncomingForm()
        formset = IncomingItemFormSetFactory(instance=Incoming(), warehouse=None)

    return render(request, 'inventory/kirim_form.html', {'form': form, 'formset': formset})


@login_required
def kirim_update(request, kirim_id):
    kirim = get_object_or_404(Incoming, id=kirim_id)
    warehouse = kirim.warehouse

    if request.method == 'POST':
        form = IncomingForm(request.POST, instance=kirim)
        formset = IncomingItemFormSetFactory(request.POST, instance=kirim, warehouse=warehouse)

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # Eski elementlarning miqdorini qaytarish
                    for item in kirim.items.all():
                        if item.product:
                            item.product.quantity -= item.quantity
                            item.product.save()

                    # Kirimni saqlash
                    kirim = form.save(commit=False)
                    kirim.created_by = request.user
                    kirim.save()

                    # Yangi elementlarni saqlash
                    formset.instance = kirim
                    instances = formset.save(commit=False)

                    for instance in instances:
                        instance.incoming = kirim
                        instance.save()
                        # save metodida mahsulot miqdori avtomatik yangilanadi

                    for obj in formset.deleted_objects:
                        obj.delete()

                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return handle_ajax_response(True, "Kirim muvaffaqiyatli yangilandi.", {
                            'kirim': {
                                'id': kirim.id,
                                'warehouse': kirim.warehouse.name,
                                'supplier': kirim.supplier.name if kirim.supplier else 'Noma\'lum',
                                'date': kirim.date.strftime('%Y-%m-%d'),
                                'total_amount': float(kirim.total_amount),
                                'paid_amount': float(kirim.paid_amount),
                                'debt': float(kirim.debt),
                            }
                        })

                    messages.success(request, "Kirim muvaffaqiyatli yangilandi.")
                    return redirect('incoming_list')

            except Exception as e:
                error_msg = f"Xatolik yuz berdi: {str(e)}"
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return handle_ajax_response(False, error_msg, status=400)
                messages.error(request, error_msg)
        else:
            error_messages = []
            if form.errors:
                for field, errors in form.errors.items():
                    error_messages.extend([f"{field}: {error}" for error in errors])
            if formset.errors:
                for i, form_errors in enumerate(formset.errors):
                    if form_errors:
                        for field, errors in form_errors.items():
                            error_messages.extend([f"Qator {i + 1} - {field}: {error}" for error in errors])
            if formset.non_form_errors():
                error_messages.extend([str(error) for error in formset.non_form_errors()])
            error_message = "; ".join(error_messages) if error_messages else "Forma to'ldirishda xatolik yuz berdi."

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return handle_ajax_response(False, error_message, {
                    'form_errors': form.errors,
                    'formset_errors': formset.errors
                }, 400)
            messages.error(request, error_message)
    else:
        form = IncomingForm(instance=kirim)
        formset = IncomingItemFormSetFactory(instance=kirim, warehouse=warehouse)

    return render(request, 'inventory/kirim_update.html', {
        'form': form,
        'formset': formset,
        'kirim': kirim,
        'title': f'Kirim #{kirim.id} ni tahrirlash'
    })


@login_required
def kirim_detail(request, kirim_id):
    try:
        kirim = Incoming.objects.get(id=kirim_id)
        items = kirim.items.all().select_related('product')

        return render(request, 'inventory/kirim_detail.html', {
            'kirim': kirim,
            'items': items,
            'title': f'Kirim #{kirim.id} tafsilotlari'
        })
    except Incoming.DoesNotExist:
        messages.error(request, "Kirim topilmadi.")
        return redirect('incoming_list')


@login_required
def kirim_delete(request, kirim_id):
    try:
        kirim = get_object_or_404(Incoming, id=kirim_id)

        if request.method == 'POST':
            try:
                with transaction.atomic():
                    # Kirimni o'chirish (model delete metodida mahsulot miqdorlari qaytariladi)
                    kirim.delete()

                message = "Kirim muvaffaqiyatli o'chirildi."
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return handle_ajax_response(True, message, {'kirim_id': kirim_id})
                messages.success(request, message)
                return redirect('incoming_list')

            except Exception as e:
                error_msg = f"Kirimni o'chirishda xatolik: {str(e)}"
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return handle_ajax_response(False, error_msg, status=400)
                messages.error(request, error_msg)
                return redirect('incoming_list')

        return render(request, 'inventory/kirim_confirm_delete.html', {
            'kirim': kirim,
            'title': f'Kirim #{kirim.id} ni o\'chirish'
        })
    except Incoming.DoesNotExist:
        message = "Kirim topilmadi."
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return handle_ajax_response(False, message, status=404)
        messages.error(request, message)
        return redirect('incoming_list')


@login_required
def get_products_by_warehouse(request):
    warehouse_id = request.GET.get('warehouse_id')
    if not warehouse_id:
        return JsonResponse({'products': []})

    try:
        products = Product.objects.filter(warehouse_id=warehouse_id).values(
            'id', 'name', 'quantity', 'unit'
        )

        products_list = [{
            'id': product['id'],
            'name': product['name'],
            'stock': product['quantity'],
            'unit': product['unit']
        } for product in products]

        return JsonResponse({'products': products_list, 'count': len(products_list)})
    except Exception as e:
        return JsonResponse({'error': str(e), 'products': []}, status=400)


# OUTGOING VIEWS
@login_required
def chiqim_list(request):
    query = request.GET.get('q')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    warehouse_id = request.GET.get('warehouse')

    outgoings = Outgoing.objects.all().order_by('-date')

    if warehouse_id:
        outgoings = outgoings.filter(warehouse_id=warehouse_id)
    outgoings = apply_search_filter(outgoings, query, ['customer__name', 'note'])
    outgoings = apply_date_filter(outgoings, start_date, end_date)

    page_obj = get_paginated_data(request, outgoings)

    return render(request, 'inventory/chiqim_list.html', {
        'page_obj': page_obj,
        'query': query,
        'start_date': start_date,
        'end_date': end_date,
        'warehouse_id': warehouse_id,
        'warehouses': Warehouse.objects.all(),
    })


@login_required
def chiqim_create(request):
    if request.method == 'POST':
        form = OutgoingForm(request.POST)
        warehouse = None

        if 'warehouse' in request.POST:
            try:
                warehouse_id = request.POST.get('warehouse')
                if warehouse_id:
                    warehouse = Warehouse.objects.get(id=warehouse_id)
            except Warehouse.DoesNotExist:
                pass

        formset = OutgoingItemFormSet(request.POST, warehouse=warehouse)

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    outgoing = form.save(commit=False)
                    outgoing.created_by = request.user
                    outgoing.date = outgoing.date or date.today()
                    outgoing.save()

                    total_amount = 0
                    total_profit = 0
                    formset.instance = outgoing

                    for form_item in formset:
                        if form_item.cleaned_data and not form_item.cleaned_data.get('DELETE', False):
                            product = form_item.cleaned_data.get('product')
                            quantity = form_item.cleaned_data.get('quantity', 0)
                            price = form_item.cleaned_data.get('price', 0)

                            if not product:
                                raise ValidationError(
                                    "Har bir chiqim elementi uchun mahsulot tanlangan bo'lishi kerak!")

                            if product.quantity < quantity:
                                raise ValidationError(
                                    f"{product.name} uchun yetarli miqdor mavjud emas. "
                                    f"Kerak: {quantity}, Mavjud: {product.quantity}"
                                )

                            item = form_item.save(commit=False)
                            item.outgoing = outgoing
                            item.product = product
                            item.cost_price = 0
                            item.total = quantity * price
                            item.profit = (price * quantity) - (item.cost_price * quantity)
                            item.save()

                            # Mahsulot miqdorini kamaytirish
                            product.quantity -= quantity
                            product.save()

                            total_amount += item.total
                            total_profit += item.profit

                    outgoing.total_amount = total_amount
                    outgoing.profit = total_profit
                    outgoing.debt = outgoing.total_amount - (outgoing.paid_amount or 0)
                    outgoing.save()

                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return handle_ajax_response(True, "Chiqim muvaffaqiyatli qo'shildi.", {
                            'outgoing': {
                                'id': outgoing.id,
                                'warehouse': outgoing.warehouse.name,
                                'customer': outgoing.customer.name if outgoing.customer else 'Noma\'lum',
                                'date': outgoing.date.strftime('%Y-%m-%d'),
                                'total_amount': float(outgoing.total_amount),
                                'paid_amount': float(outgoing.paid_amount),
                                'debt': float(outgoing.debt),
                                'profit': float(outgoing.profit),
                            }
                        })

                    messages.success(request, "Chiqim muvaffaqiyatli qo'shildi.")
                    return redirect('outgoing_list')

            except ValidationError as e:
                error_msg = str(e)
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return handle_ajax_response(False, error_msg, status=400)
                messages.error(request, error_msg)

            except Exception as e:
                error_msg = f"Xatolik yuz berdi: {str(e)}"
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return handle_ajax_response(False, error_msg, status=400)
                messages.error(request, error_msg)
        else:
            error_messages = []

            if form.errors:
                for field, errors in form.errors.items():
                    error_messages.extend([f"{field}: {error}" for error in errors])

            if formset.errors:
                for i, form_errors in enumerate(formset.errors):
                    if form_errors:
                        for field, errors in form_errors.items():
                            error_messages.extend([f"Qator {i + 1} - {field}: {error}" for error in errors])

            if formset.non_form_errors():
                error_messages.extend([str(error) for error in formset.non_form_errors()])

            error_message = "; ".join(error_messages) if error_messages else "Forma to'ldirishda xatolik yuz berdi."

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return handle_ajax_response(False, error_message, {
                    'form_errors': form.errors,
                    'formset_errors': formset.errors
                }, 400)
            messages.error(request, error_message)
    else:
        form = OutgoingForm(initial={'date': date.today()})
        formset = OutgoingItemFormSet()

    return render(request, 'inventory/chiqim_form.html', {
        'form': form,
        'formset': formset,
        'title': 'Yangi chiqim qo\'shish'
    })


@login_required
def chiqim_detail(request, outgoing_id):
    try:
        outgoing = Outgoing.objects.get(id=outgoing_id)
        items = outgoing.items.all().select_related('product')

        return render(request, 'inventory/chiqim_detail.html', {
            'outgoing': outgoing,
            'items': items,
            'title': f'Chiqim #{outgoing.id} tafsilotlari'
        })
    except Outgoing.DoesNotExist:
        messages.error(request, "Chiqim topilmadi.")
        return redirect('outgoing_list')


@login_required
def chiqim_edit(request, outgoing_id):
    try:
        outgoing = Outgoing.objects.get(id=outgoing_id)
        messages.info(request, "Tahrirlash funksiyasi hali ishlab chiqilmagan.")
        return redirect('outgoing_detail', outgoing_id=outgoing_id)
    except Outgoing.DoesNotExist:
        messages.error(request, "Chiqim topilmadi.")
        return redirect('outgoing_list')


@login_required
def chiqim_delete(request, outgoing_id):
    try:
        outgoing = get_object_or_404(Outgoing, id=outgoing_id)

        if request.method == 'POST':
            try:
                with transaction.atomic():
                    # Chiqimni o'chirish (model delete metodida mahsulot miqdorlari qaytariladi)
                    outgoing.delete()

                message = "Chiqim muvaffaqiyatli o'chirildi."
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return handle_ajax_response(True, message, {'outgoing_id': outgoing_id})
                messages.success(request, message)
                return redirect('outgoing_list')

            except Exception as e:
                error_msg = f"Chiqimni o'chirishda xatolik: {str(e)}"
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return handle_ajax_response(False, error_msg, status=400)
                messages.error(request, error_msg)
                return redirect('outgoing_list')

        return render(request, 'inventory/chiqim_delete.html', {
            'outgoing': outgoing,
            'title': f'Chiqim #{outgoing.id} ni o\'chirish'
        })

    except Outgoing.DoesNotExist:
        message = "Chiqim topilmadi."
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return handle_ajax_response(False, message, status=404)
        messages.error(request, message)
        return redirect('outgoing_list')


# CSV EXPORT FUNCTIONS
def export_csv(request, queryset, filename, headers, get_row_data):
    """CSV eksport uchun umumiy funksiya"""
    warehouse_id = request.GET.get('warehouse')
    if warehouse_id:
        queryset = queryset.filter(warehouse_id=warehouse_id)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'

    writer = csv.writer(response)
    writer.writerow(headers)

    for item in queryset:
        writer.writerow(get_row_data(item))

    return response


@login_required
def export_incomings_csv(request):
    return export_csv(
        request,
        Incoming.objects.all(),
        'incomings',
        ['Sana', 'Ombor', 'Ta\'minotchi', 'Jami summa', 'To\'langan', 'Qarz', 'Izoh'],
        lambda item: [
            item.date,
            item.warehouse.name,
            item.supplier.name if item.supplier else '-',
            item.total_amount,
            item.paid_amount,
            item.debt,
            item.note or '-'
        ]
    )


@login_required
def export_outgoings_csv(request):
    return export_csv(
        request,
        Outgoing.objects.all(),
        'outgoings',
        ['Sana', 'Ombor', 'Xaridor', 'Jami summa', 'To\'langan', 'Qarz', 'Foyda', 'Izoh'],
        lambda item: [
            item.date,
            item.warehouse.name,
            item.customer.name if item.customer else '-',
            item.total_amount,
            item.paid_amount,
            item.debt,
            item.profit,
            item.note or '-'
        ]
    )


# CATEGORY VIEWS
@login_required
def category_list(request):
    categories = Category.objects.all().order_by('-created_at')
    return render(request, 'inventory/category_list.html', {'categories': categories})


def get_category_data(category):
    """Kategoriya ma'lumotlarini qaytarish uchun yordamchi funksiya"""
    return {
        'id': category.id,
        'name': category.name,
        'image': category.image.url if category.image else '',
    }


@login_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            category = form.save(commit=False)
            category.created_by = request.user
            category.save()

            return handle_ajax_response(True, "Kategoriya muvaffaqiyatli qo'shildi.",
                                        {'category': get_category_data(category)})
        else:
            return handle_ajax_response(False, "Kategoriya qo'shishda xatolik yuz berdi.",
                                        {'errors': form.errors.as_json()}, 400)
    else:
        form = CategoryForm()
        return render(request, 'inventory/category_form.html', {'form': form})


@login_required
def category_update(request, category_id):
    category = get_object_or_404(Category, pk=category_id)

    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            category = form.save()
            return handle_ajax_response(True, "Kategoriya muvaffaqiyatli yangilandi.",
                                        {'category': get_category_data(category)})
        else:
            return handle_ajax_response(False, "Kategoriyani yangilashda xatolik yuz berdi.",
                                        {'errors': form.errors.as_json()}, 400)
    else:
        return handle_ajax_response(True, "", {'category': get_category_data(category)})


@login_required
def category_delete(request, category_id):
    if request.method == 'POST':
        category = get_object_or_404(Category, pk=category_id)

        if Product.objects.filter(category=category).exists():
            return handle_ajax_response(False, "Bu kategoriyada mahsulotlar mavjud, o'chirib bo'lmaydi.", status=400)

        category.delete()
        return handle_ajax_response(True, "Kategoriya muvaffaqiyatli o'chirildi.")
    else:
        return handle_ajax_response(False, "Faqat POST so'rovi orqali o'chirish mumkin.", status=400)


@login_required
def category_products(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = Product.objects.filter(category=category)

    product_list = [{
        'id': product.id,
        'name': product.name,
        'quantity': product.quantity,
        'minimum_quantity': product.minimum_quantity,
        'unit': product.unit,
        'barcode': product.barcode or '',
    } for product in products]

    return handle_ajax_response(True, "", {'products': product_list})