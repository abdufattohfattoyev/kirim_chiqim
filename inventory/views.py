from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Product, Category, Incoming, IncomingItem, Outgoing, OutgoingItem, Warehouse
from .forms import IncomingForm, IncomingItemFormSet, OutgoingForm, OutgoingItemFormSet, ProductForm, CategoryForm, \
    WarehouseForm, IncomingItemFormSetFactory
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils.dateparse import parse_date
from django.http import HttpResponse
import csv
import pandas as pd
from django.db import transaction
from django import forms


@login_required
def ombor_list(request):
    query = request.GET.get('q')
    warehouses = Warehouse.objects.all().order_by('name')

    if query:
        warehouses = warehouses.filter(name__icontains=query)

    # Har bir ombor uchun mahsulotlar sonini qo'shamiz
    warehouse_list = []
    for warehouse in warehouses:
        product_count = Product.objects.filter(warehouse=warehouse).count()
        warehouse_list.append({
            'warehouse': warehouse,
            'product_count': product_count,
        })

    # Pagination
    paginator = Paginator(warehouse_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
    }
    return render(request, 'inventory/ombor_list.html', context)


@login_required
def warehouse_list(request):
    warehouses = Warehouse.objects.all().order_by('name')
    context = {
        'warehouses': warehouses,
    }
    return render(request, 'inventory/ombor_list.html', context)


@login_required
def warehouse_detail(request, warehouse_id):
    warehouse = get_object_or_404(Warehouse, id=warehouse_id)
    query = request.GET.get('q')
    products = Product.objects.filter(warehouse=warehouse).order_by('name')

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(category__name__icontains=query)
        )

    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    product_form = ProductForm(initial={'warehouse': warehouse})

    context = {
        'warehouse': warehouse,
        'page_obj': page_obj,
        'query': query,
        'product_form': product_form,
    }
    return render(request, 'inventory/warehouse_detail.html', context)


@login_required
def warehouse_create(request):
    if request.method == 'POST':
        form = WarehouseForm(request.POST)
        if form.is_valid():
            warehouse = form.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Ombor muvaffaqiyatli qo‘shildi.',
                    'warehouse': {
                        'id': warehouse.id,
                        'name': warehouse.name,
                        'created_at': warehouse.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    }
                })
            messages.success(request, 'Ombor muvaffaqiyatli qo‘shildi.')
            return redirect('ombor_list')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Ombor qo‘shishda xatolik yuz berdi.',
                    'errors': form.errors.as_json()
                }, status=400)
            messages.error(request, f'Forma to‘ldirishda xatolik: {form.errors}')
            return render(request, 'inventory/warehouse_form.html', {'form': form})
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
                return JsonResponse({
                    'status': 'success',
                    'message': 'Ombor muvaffaqiyatli tahrirlandi.',
                    'warehouse': {
                        'id': warehouse.id,
                        'name': warehouse.name,
                        'created_at': warehouse.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    }
                })
            messages.success(request, 'Ombor muvaffaqiyatli tahrirlandi.')
            return redirect('ombor_list')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Ombor tahrirlashda xatolik yuz berdi.',
                    'errors': form.errors.as_json()
                }, status=400)
            messages.error(request, f'Forma to‘ldirishda xatolik: {form.errors}')
            return render(request, 'inventory/warehouse_form.html', {'form': form})
    else:
        form = WarehouseForm(instance=warehouse)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'form': {
                    'name': warehouse.name,
                }
            })
        return render(request, 'inventory/warehouse_form.html', {'form': form})


@login_required
def warehouse_delete(request, warehouse_id):
    warehouse = get_object_or_404(Warehouse, id=warehouse_id)
    if request.method == 'POST':
        products = Product.objects.filter(warehouse=warehouse)
        if products.exists():
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Bu omborda mahsulotlar mavjud, o‘chirib bo‘lmaydi.'
                }, status=400)
            messages.error(request, 'Bu omborda mahsulotlar mavjud, o‘chirib bo‘lmaydi.')
            return redirect('ombor_list')
        warehouse.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': 'Ombor muvaffaqiyatli o‘chirildi.',
                'warehouse_id': warehouse_id
            })
        messages.success(request, 'Ombor muvaffaqiyatli o‘chirildi.')
        return redirect('ombor_list')
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'error',
            'message': 'Faqat POST so‘rovi orqali o‘chirish mumkin.'
        }, status=400)
    return render(request, 'inventory/warehouse_confirm_delete.html', {'warehouse': warehouse})


@login_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Mahsulot muvaffaqiyatli qo‘shildi.',
                    'product': {
                        'id': product.id,
                        'name': product.name,
                        'warehouse': product.warehouse.name,
                        'category': product.category.name if product.category else 'Kategoriyasiz',
                        'image': product.image.url if product.image else '',
                        'quantity': product.quantity,
                        'minimum_quantity': product.minimum_quantity,
                    }
                })
            messages.success(request, 'Mahsulot muvaffaqiyatli qo‘shildi.')
            return redirect('warehouse_detail', warehouse_id=product.warehouse.id)
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                errors = form.errors.as_json()
                error_message = ''
                if 'name' in form.errors:
                    error_message = form.errors['name'][0]
                elif 'warehouse' in form.errors:
                    error_message = form.errors['warehouse'][0]
                elif 'category' in form.errors:
                    error_message = form.errors['category'][0]
                elif 'new_category' in form.errors:
                    error_message = form.errors['new_category'][0]
                elif 'image' in form.errors:
                    error_message = form.errors['image'][0]
                elif 'quantity' in form.errors:
                    error_message = form.errors['quantity'][0]
                elif 'minimum_quantity' in form.errors:
                    error_message = form.errors['minimum_quantity'][0]
                else:
                    error_message = 'Forma to‘ldirishda noma’lum xatolik yuz berdi.'
                return JsonResponse({
                    'status': 'error',
                    'message': error_message,
                    'errors': errors
                }, status=400)
            messages.error(request, 'Forma to‘ldirishda xatolik yuz berdi.')
            return render(request, 'inventory/warehouse_detail.html', {'form': form})
    else:
        form = ProductForm()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'form': {
                    'name': '',
                    'warehouse': '',
                    'category': '',
                    'image': '',
                    'quantity': 0,
                    'minimum_quantity': 10,
                }
            })
        return render(request, 'inventory/warehouse_detail.html', {'form': form})


@login_required
def product_edit(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Mahsulot muvaffaqiyatli tahrirlandi.',
                    'product': {
                        'id': product.id,
                        'name': product.name,
                        'warehouse': product.warehouse.name,
                        'category': product.category.name if product.category else 'Kategoriyasiz',
                        'image': product.image.url if product.image else '',
                        'quantity': product.quantity,
                        'minimum_quantity': product.minimum_quantity,
                    }
                })
            messages.success(request, 'Mahsulot muvaffaqiyatli tahrirlandi.')
            return redirect('warehouse_detail', warehouse_id=product.warehouse.id)
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                errors = form.errors.as_json()
                error_message = ''
                if 'name' in form.errors:
                    error_message = form.errors['name'][0]
                elif 'warehouse' in form.errors:
                    error_message = form.errors['warehouse'][0]
                elif 'category' in form.errors:
                    error_message = form.errors['category'][0]
                elif 'new_category' in form.errors:
                    error_message = form.errors['new_category'][0]
                elif 'image' in form.errors:
                    error_message = form.errors['image'][0]
                elif 'quantity' in form.errors:
                    error_message = form.errors['quantity'][0]
                elif 'minimum_quantity' in form.errors:
                    error_message = form.errors['minimum_quantity'][0]
                else:
                    error_message = 'Forma to‘ldirishda noma’lum xatolik yuz berdi.'
                return JsonResponse({
                    'status': 'error',
                    'message': error_message,
                    'errors': errors
                }, status=400)
            messages.error(request, 'Forma to‘ldirishda xatolik yuz berdi.')
            return render(request, 'inventory/warehouse_detail.html', {'form': form, 'product': product})
    else:
        form = ProductForm(instance=product)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'form': {
                    'name': product.name,
                    'warehouse': product.warehouse.id,
                    'category': product.category.id if product.category else '',
                    'image': product.image.url if product.image else '',
                    'quantity': product.quantity,
                    'minimum_quantity': product.minimum_quantity,
                }
            })
        return render(request, 'inventory/warehouse_detail.html', {'form': form, 'product': product})


@login_required
def product_delete(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    warehouse_id = product.warehouse.id
    if request.method == 'POST':
        incoming_items = IncomingItem.objects.filter(product=product)
        outgoing_items = OutgoingItem.objects.filter(product=product)
        if incoming_items.exists() or outgoing_items.exists():
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Bu mahsulot kirim yoki chiqimlarda ishlatilgan, o‘chirib bo‘lmaydi.'
                }, status=400)
            messages.error(request, 'Bu mahsulot kirim yoki chiqimlarda ishlatilgan, o‘chirib bo‘lmaydi.')
            return redirect('warehouse_detail', warehouse_id=warehouse_id)
        else:
            product.delete()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Mahsulot muvaffaqiyatli o‘chirildi.',
                    'product_id': product_id
                })
            messages.success(request, 'Mahsulot muvaffaqiyatli o‘chirildi.')
            return redirect('warehouse_detail', warehouse_id=warehouse_id)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'error',
            'message': 'Faqat POST so‘rovi orqali o‘chirish mumkin.'
        }, status=400)
    return render(request, 'inventory/product_confirm_delete.html', {'product': product})


@login_required
def export_products_csv(request, warehouse_id):
    warehouse = get_object_or_404(Warehouse, id=warehouse_id)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="products_{warehouse.name}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Mahsulot nomi', 'Ombor', 'Kategoriya', 'Miqdor'])

    products = Product.objects.filter(warehouse=warehouse)

    for product in products:
        writer.writerow([
            product.name,
            product.warehouse.name,
            product.category.name if product.category else '-',
            product.quantity
        ])

    return response


@login_required
def import_products_csv(request, warehouse_id):
    warehouse = get_object_or_404(Warehouse, id=warehouse_id)
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Faqat CSV fayllarni yuklash mumkin.')
            return redirect('warehouse_detail', warehouse_id=warehouse_id)

        try:
            data = pd.read_csv(csv_file)
            with transaction.atomic():
                for _, row in data.iterrows():
                    category, _ = Category.objects.get_or_create(name=row['Kategoriya'])
                    Product.objects.update_or_create(
                        name=row['Mahsulot nomi'],
                        warehouse=warehouse,
                        category=category,
                        defaults={'quantity': row['Miqdor']}
                    )
            messages.success(request, 'Mahsulotlar muvaffaqiyatli import qilindi.')
        except Exception as e:
            messages.error(request, f'Import xatosi: {str(e)}')
        return redirect('warehouse_detail', warehouse_id=warehouse_id)

    return render(request, 'inventory/import_products.html', {'warehouse': warehouse})


@login_required
def kirim_list(request):
    query = request.GET.get('q')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    warehouse_id = request.GET.get('warehouse')

    incomings = Incoming.objects.all().order_by('-date')

    if warehouse_id:
        incomings = incomings.filter(warehouse_id=warehouse_id)
    if query:
        incomings = incomings.filter(
            Q(supplier__name__icontains=query) | Q(note__icontains=query)
        )
    if start_date and end_date:
        start_date = parse_date(start_date)
        end_date = parse_date(end_date)
        incomings = incomings.filter(date__range=[start_date, end_date])

    paginator = Paginator(incomings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    warehouses = Warehouse.objects.all()

    context = {
        'page_obj': page_obj,
        'query': query,
        'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
        'end_date': end_date.strftime('%Y-%m-%d') if end_date else '',
        'warehouse_id': warehouse_id,
        'warehouses': warehouses,
    }
    return render(request, 'inventory/kirim_list.html', context)

@login_required
def kirim_create(request):
    if request.method == 'POST':
        form = IncomingForm(request.POST)
        warehouse_id = request.POST.get('warehouse')
        warehouse = Warehouse.objects.get(id=warehouse_id) if warehouse_id else None
        formset = IncomingItemFormSetFactory(request.POST, instance=Incoming(), warehouse=warehouse)

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    incoming = form.save(commit=False)
                    incoming.created_by = request.user
                    incoming.debt = incoming.total_amount - incoming.paid_amount
                    incoming.save()

                    formset.instance = incoming
                    instances = formset.save(commit=False)
                    for instance in instances:
                        instance.incoming = incoming
                        instance.save()
                        product = instance.product
                        product.quantity += instance.quantity
                        product.save()

                    for obj in formset.deleted_objects:
                        obj.delete()

                    messages.success(request, 'Kirim muvaffaqiyatli qo‘shildi.')
                    return redirect('kirim_list')
            except Exception as e:
                messages.error(request, f'Xatolik yuz berdi: {str(e)}')
        else:
            messages.error(request, 'Forma to‘ldirishda xatolik yuz berdi.')
    else:
        form = IncomingForm()
        formset = IncomingItemFormSetFactory(instance=Incoming(), warehouse=None)

    return render(request, 'inventory/kirim_form.html', {
        'form': form,
        'formset': formset,
    })

@login_required
def get_products_by_warehouse(request):
    warehouse_id = request.GET.get('warehouse_id')
    products = Product.objects.filter(warehouse_id=warehouse_id).values('id', 'name')
    return JsonResponse({'products': list(products)})




@login_required
def chiqim_list(request):
    query = request.GET.get('q')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    warehouse_id = request.GET.get('warehouse')

    outgoings = Outgoing.objects.all().order_by('-date')

    if warehouse_id:
        outgoings = outgoings.filter(warehouse_id=warehouse_id)
    if query:
        outgoings = outgoings.filter(
            Q(customer__name__icontains=query) | Q(note__icontains=query)
        )
    if start_date and end_date:
        start_date = parse_date(start_date)
        end_date = parse_date(end_date)
        outgoings = outgoings.filter(date__range=[start_date, end_date])

    paginator = Paginator(outgoings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    warehouses = Warehouse.objects.all()

    context = {
        'page_obj': page_obj,
        'query': query,
        'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
        'end_date': end_date.strftime('%Y-%m-%d') if end_date else '',
        'warehouse_id': warehouse_id,
        'warehouses': warehouses,
    }
    return render(request, 'inventory/chiqim_list.html', context)


@login_required
def chiqim_create(request):
    if request.method == 'POST':
        form = OutgoingForm(request.POST)
        formset = OutgoingItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                outgoing = form.save(commit=False)
                outgoing.created_by = request.user
                total_profit = 0

                for item_form in formset:
                    if item_form.cleaned_data and not item_form.cleaned_data.get('DELETE', False):
                        item = item_form.save(commit=False)
                        product = item.product
                        quantity = item.quantity

                        incoming_items = IncomingItem.objects.filter(
                            product=product
                        ).order_by('created_at')

                        remaining_quantity = quantity
                        item_cost = 0
                        selected_batch = None

                        for incoming_item in incoming_items:
                            if remaining_quantity <= 0:
                                break
                            if incoming_item.quantity > 0:
                                available = min(remaining_quantity, incoming_item.quantity)
                                item_cost += available * incoming_item.price
                                remaining_quantity -= available
                                incoming_item.quantity -= available
                                incoming_item.save()
                                if not selected_batch:
                                    selected_batch = incoming_item.batch_number

                        if remaining_quantity > 0:
                            raise forms.ValidationError(f'{product.name} uchun yetarli miqdor mavjud emas.')

                        item.batch_number = selected_batch
                        item.profit = (item.price * item.quantity) - item_cost
                        total_profit += item.profit

                        item.outgoing = outgoing
                        item.save()
                        product.quantity -= item.quantity
                        product.save()

                outgoing.profit = total_profit
                outgoing.save()
                formset.save()
                messages.success(request, 'Chiqim muvaffaqiyatli qo‘shildi.')
                return redirect('chiqim_list')
        else:
            messages.error(request, 'Forma to‘ldirishda xatolik yuz berdi.')
    else:
        form = OutgoingForm()
        formset = OutgoingItemFormSet()

    return render(request, 'inventory/chiqim_form.html', {'form': form, 'formset': formset})

@login_required
def export_incomings_csv(request):
    warehouse_id = request.GET.get('warehouse')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="incomings.csv"'

    writer = csv.writer(response)
    writer.writerow(['Sana', 'Ombor', 'Ta\'minotchi', 'Jami summa', 'To‘langan', 'Qarz', 'Izoh'])

    incomings = Incoming.objects.all()
    if warehouse_id:
        incomings = incomings.filter(warehouse_id=warehouse_id)

    for incoming in incomings:
        writer.writerow([
            incoming.date,
            incoming.warehouse.name,
            incoming.supplier.name if incoming.supplier else '-',
            incoming.total_amount,
            incoming.paid_amount,
            incoming.debt,
            incoming.note or '-'
        ])

    return response

@login_required
def export_outgoings_csv(request):
    warehouse_id = request.GET.get('warehouse')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="outgoings.csv"'

    writer = csv.writer(response)
    writer.writerow(['Sana', 'Ombor', 'Xaridor', 'Jami summa', 'To‘langan', 'Qarz', 'Foyda', 'Izoh'])

    outgoings = Outgoing.objects.all()
    if warehouse_id:
        outgoings = outgoings.filter(warehouse_id=warehouse_id)

    for outgoing in outgoings:
        writer.writerow([
            outgoing.date,
            outgoing.warehouse.name,
            outgoing.customer.name if outgoing.customer else '-',
            outgoing.total_amount,
            outgoing.paid_amount,
            outgoing.debt,
            outgoing.profit,
            outgoing.note or '-'
        ])

    return response


@login_required
def category_list(request):
    categories = Category.objects.all().order_by('-created_at')
    context = {
        'categories': categories,
    }
    return render(request, 'inventory/category_list.html', context)

@login_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            category = form.save()
            return JsonResponse({
                'status': 'success',
                'message': 'Kategoriya muvaffaqiyatli qo‘shildi.',
                'category': {
                    'id': category.id,
                    'name': category.name,
                    'image': category.image.url if category.image else '',
                }
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Kategoriya qo‘shishda xatolik yuz berdi.',
                'errors': form.errors.as_json()
            }, status=400)
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
            return JsonResponse({
                'status': 'success',
                'message': 'Kategoriya muvaffaqiyatli yangilandi.',
                'category': {
                    'id': category.id,
                    'name': category.name,
                    'image': category.image.url if category.image else '',
                }
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Kategoriyani yangilashda xatolik yuz berdi.',
                'errors': form.errors.as_json()
            }, status=400)
    else:
        return JsonResponse({
            'status': 'success',
            'category': {
                'id': category.id,
                'name': category.name,
                'image': category.image.url if category.image else '',
            }
        })

@login_required
def category_delete(request, category_id):
    if request.method == 'POST':
        category = get_object_or_404(Category, pk=category_id)
        category.delete()
        return JsonResponse({
            'status': 'success',
            'message': 'Kategoriya muvaffaqiyatli o‘chirildi.',
        })
    else:
        return JsonResponse({
            'status': 'error',
            'message': 'Faqat POST so‘rovi orqali o‘chirish mumkin.'
        }, status=400)

@login_required
def category_products(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = Product.objects.filter(category=category)
    product_list = [
        {
            'id': product.id,
            'name': product.name,
            'quantity': product.quantity,
            'minimum_quantity': product.minimum_quantity,
        }
        for product in products
    ]
    return JsonResponse({
        'status': 'success',
        'products': product_list,
    })