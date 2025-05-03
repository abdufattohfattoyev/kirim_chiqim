from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Supplier, Customer, SupplierPayment, CustomerPayment
from .forms import SupplierForm, CustomerForm, SupplierPaymentForm, CustomerPaymentForm
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils.dateparse import parse_date
from django.contrib import messages
import csv
from django.http import HttpResponse, JsonResponse
import pandas as pd
from django.db import transaction


@login_required
def supplier_list(request):
    query = request.GET.get('q')
    suppliers = Supplier.objects.all()
    if query:
        suppliers = suppliers.filter(
            Q(name__icontains=query) | Q(phone_number__icontains=query)
        )
    paginator = Paginator(suppliers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'partners/supplier_list.html', {'page_obj': page_obj, 'query': query})


@login_required
def supplier_edit(request, pk):
    supplier = Supplier.objects.get(pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ta\'minotchi muvaffaqiyatli tahrirlandi.')
            return redirect('supplier_list')
        else:
            messages.error(request, 'Forma to‘ldirishda xatolik yuz berdi.')
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'partners/supplier_form.html', {'form': form})

@login_required
def supplier_delete(request, pk):
    supplier = Supplier.objects.get(pk=pk)
    if request.method == 'POST':
        supplier.delete()
        messages.success(request, 'Ta\'minotchi muvaffaqiyatli o‘chirildi.')
        return redirect('supplier_list')
    return render(request, 'partners/supplier_confirm_delete.html', {'supplier': supplier})

@login_required
def export_suppliers_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="suppliers.csv"'

    writer = csv.writer(response)
    writer.writerow(['Nomi', 'Telefon', 'Manzil', 'Dastlabki qarz'])

    suppliers = Supplier.objects.all()
    for supplier in suppliers:
        writer.writerow([supplier.name, supplier.phone_number, supplier.address or '-', supplier.initial_debt])

    return response


@login_required
def import_suppliers_csv(request):
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Faqat CSV fayllarni yuklash mumkin.')
            return redirect('supplier_list')

        try:
            data = pd.read_csv(csv_file)
            with transaction.atomic():
                for _, row in data.iterrows():
                    Supplier.objects.update_or_create(
                        name=row['Nomi'],
                        defaults={
                            'phone_number': row['Telefon'],
                            'address': row.get('Manzil', ''),
                            'initial_debt': row.get('Dastlabki qarz', 0),
                            'created_by': request.user
                        }
                    )
            messages.success(request, 'Ta\'minotchilar muvaffaqiyatli import qilindi.')
        except Exception as e:
            messages.error(request, f'Import xatosi: {str(e)}')
        return redirect('supplier_list')

    return render(request, 'partners/import_suppliers.html')


@login_required
def supplier_create(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save(commit=False)
            supplier.created_by = request.user
            supplier.save()
            messages.success(request, 'Ta\'minotchi muvaffaqiyatli qo‘shildi.')
            return redirect('supplier_list')
        else:
            print(form.errors)  # Xatolarni konsolga chiqarish
            messages.error(request, 'Forma to‘ldirishda xatolik yuz berdi.')
    else:
        form = SupplierForm()
    return render(request, 'partners/supplier_form.html', {'form': form})


@login_required
def export_customers_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="customers.csv"'

    writer = csv.writer(response)
    writer.writerow(['Nomi', 'Telefon', 'Manzil', 'Dastlabki qarz'])

    customers = Customer.objects.all()
    for customer in customers:
        writer.writerow([customer.name, customer.phone_number, customer.address or '-', customer.initial_debt])

    return response


@login_required
def import_customers_csv(request):
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Faqat CSV fayllarni yuklash mumkin.')
            return redirect('customer_list')

        try:
            data = pd.read_csv(csv_file)
            with transaction.atomic():
                for _, row in data.iterrows():
                    Customer.objects.update_or_create(
                        name=row['Nomi'],
                        defaults={
                            'phone_number': row['Telefon'],
                            'address': row.get('Manzil', ''),
                            'initial_debt': row.get('Dastlabki qarz', 0),
                            'created_by': request.user
                        }
                    )
            messages.success(request, 'Xaridorlar muvaffaqiyatli import qilindi.')
        except Exception as e:
            messages.error(request, f'Import xatosi: {str(e)}')
        return redirect('customer_list')

    return render(request, 'partners/import_customers.html')


@login_required
def customer_list(request):
    query = request.GET.get('q', '')
    sort = request.GET.get('sort', 'name')
    customers = Customer.objects.all()

    if query:
        customers = customers.filter(
            Q(name__icontains=query) |
            Q(phone_number__icontains=query) |
            Q(notes__icontains=query)
        )

    customers = customers.order_by(sort)
    paginator = Paginator(customers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    customer_form = CustomerForm()
    return render(request, 'partners/customer_list.html', {
        'page_obj': page_obj,
        'query': query,
        'sort': sort,
        'customer_form': customer_form,
    })


@login_required
def customer_create(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.created_by = request.user
            customer.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Xaridor muvaffaqiyatli qo‘shildi.',
                    'customer': {
                        'id': customer.id,
                        'name': customer.name,
                        'phone_number': customer.phone_number,
                        'notes': customer.notes,
                        'balance': float(customer.balance),
                    }
                })
            messages.success(request, 'Xaridor muvaffaqiyatli qo‘shildi.')
            return redirect('customer_list')
        else:
            # Xato xabarlarini aniqroq qaytarish
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                error_messages = []
                for field, errors in form.errors.items():
                    for error in errors:
                        error_messages.append(f"{field}: {error}")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Forma to‘ldirishda xatolik yuz berdi.',
                    'errors': error_messages
                }, status=400)
            messages.error(request, f'Forma to‘ldirishda xatolik: {form.errors}')
    else:
        form = CustomerForm()
    return render(request, 'partners/customer_list.html', {
        'form': form,
        'customer_form': form
    })

@login_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            customer = form.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Xaridor muvaffaqiyatli tahrirlandi.',
                    'customer': {
                        'id': customer.id,
                        'name': customer.name,
                        'phone_number': customer.phone_number,
                        'notes': customer.notes,
                        'balance': float(customer.balance),
                    }
                })
            messages.success(request, 'Xaridor muvaffaqiyatli tahrirlandi.')
            return redirect('customer_list')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                error_messages = []
                for field, errors in form.errors.items():
                    for error in errors:
                        error_messages.append(f"{field}: {error}")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Forma to‘ldirishda xatolik yuz berdi.',
                    'errors': error_messages
                }, status=400)
            messages.error(request, f'Forma to‘ldirishda xatolik: {form.errors}')
    else:
        form = CustomerForm(instance=customer)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'form': {
                    'name': customer.name,
                    'phone_number': customer.phone_number,
                    'notes': customer.notes,
                    'initial_debt': float(customer.initial_debt),
                }
            })
    return render(request, 'partners/customer_list.html', {
        'form': form,
        'customer_form': form,
        'customer': customer
    })

@login_required
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        customer.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': 'Xaridor muvaffaqiyatli o‘chirildi.',
                'customer_id': pk
            })
        messages.success(request, 'Xaridor muvaffaqiyatli o‘chirildi.')
        return redirect('customer_list')
    return render(request, 'partners/customer_confirm_delete.html', {'customer': customer})


@login_required
def supplier_payment_create(request):
    if request.method == 'POST':
        form = SupplierPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.created_by = request.user
            payment.save()
            messages.success(request, 'To‘lov muvaffaqiyatli qo‘shildi.')
            return redirect('supplier_payment_list')
        else:
            messages.error(request, 'Forma to‘ldirishda xatolik yuz berdi.')
    else:
        form = SupplierPaymentForm()
    return render(request, 'partners/supplier_payment_form.html', {'form': form})


@login_required
def supplier_payment_list(request):
    query = request.GET.get('q')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    payments = SupplierPayment.objects.all().order_by('-date')

    if query:
        payments = payments.filter(
            Q(supplier__name__icontains=query) | Q(note__icontains=query)
        )

    if start_date and end_date:
        start_date = parse_date(start_date)
        end_date = parse_date(end_date)
        payments = payments.filter(date__range=[start_date, end_date])

    paginator = Paginator(payments, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
        'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
        'end_date': end_date.strftime('%Y-%m-%d') if end_date else '',
    }
    return render(request, 'partners/supplier_payment_list.html', context)


@login_required
def customer_payment_create(request):
    if request.method == 'POST':
        form = CustomerPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.created_by = request.user
            payment.save()
            messages.success(request, 'To‘lov muvaffaqiyatli qo‘shildi.')
            return redirect('customer_payment_list')
        else:
            messages.error(request, 'Forma to‘ldirishda xatolik yuz berdi.')
    else:
        form = CustomerPaymentForm()
    return render(request, 'partners/customer_payment_form.html', {'form': form})


@login_required
def customer_payment_list(request):
    query = request.GET.get('q')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    payments = CustomerPayment.objects.all().order_by('-date')

    if query:
        payments = payments.filter(
            Q(customer__name__icontains=query) | Q(note__icontains=query)
        )

    if start_date and end_date:
        start_date = parse_date(start_date)
        end_date = parse_date(end_date)
        payments = payments.filter(date__range=[start_date, end_date])

    paginator = Paginator(payments, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
        'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
        'end_date': end_date.strftime('%Y-%m-%d') if end_date else '',
    }
    return render(request, 'partners/customer_payment_list.html', context)