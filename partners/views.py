from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import csv
import pandas as pd
import logging

from .models import Supplier, Customer, SupplierPayment, CustomerPayment
from .forms import SupplierForm, CustomerForm, SupplierPaymentForm, CustomerPaymentForm

logger = logging.getLogger(__name__)


# ============= SUPPLIER VIEWS =============

@login_required
def supplier_list(request):
    """Ta'minotchilar ro'yxati"""
    query = request.GET.get('q', '').strip()
    sort_by = request.GET.get('sort', 'name')

    # Validatsiya
    valid_sort_fields = ['name', 'phone_number', 'created_at', '-created_at']
    if sort_by not in valid_sort_fields:
        sort_by = 'name'

    suppliers = Supplier.objects.select_related('created_by').filter(is_active=True)

    if query:
        suppliers = suppliers.filter(
            Q(name__icontains=query) |
            Q(phone_number__icontains=query) |
            Q(company_name__icontains=query)
        )

    suppliers = suppliers.order_by(sort_by)

    paginator = Paginator(suppliers, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
        'sort': sort_by,
        'total_count': suppliers.count()
    }

    return render(request, 'partners/supplier_list.html', context)


@login_required
def supplier_create(request):
    """Yangi ta'minotchi yaratish"""
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    supplier = form.save(commit=False)
                    supplier.created_by = request.user
                    supplier.save()

                messages.success(request, "Ta'minotchi muvaffaqiyatli qo'shildi.")
                return redirect('supplier_list')

            except Exception as e:
                logger.error(f"Supplier yaratishda xatolik: {e}")
                messages.error(request, "Xatolik yuz berdi. Qaytadan urinib ko'ring.")
        else:
            messages.error(request, "Forma ma'lumotlarini to'g'ri to'ldiring.")
    else:
        form = SupplierForm()

    return render(request, 'partners/supplier_form.html', {
        'form': form,
        'title': "Yangi ta'minotchi qo'shish"
    })


@login_required
def supplier_edit(request, pk):
    """Ta'minotchini tahrirlash"""
    supplier = get_object_or_404(Supplier, pk=pk, is_active=True)

    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Ta'minotchi muvaffaqiyatli tahrirlandi.")
                return redirect('supplier_list')
            except Exception as e:
                logger.error(f"Supplier tahrirlashda xatolik: {e}")
                messages.error(request, "Xatolik yuz berdi. Qaytadan urinib ko'ring.")
        else:
            messages.error(request, "Forma ma'lumotlarini to'g'ri to'ldiring.")
    else:
        form = SupplierForm(instance=supplier)

    return render(request, 'partners/supplier_form.html', {
        'form': form,
        'supplier': supplier,
        'title': f"{supplier.name}ni tahrirlash"
    })


@login_required
@require_http_methods(["POST"])
def supplier_delete(request, pk):
    """Ta'minotchini o'chirish (soft delete)"""
    supplier = get_object_or_404(Supplier, pk=pk, is_active=True)

    try:
        # Soft delete
        supplier.is_active = False
        supplier.save()

        messages.success(request, f"{supplier.name} muvaffaqiyatli o'chirildi.")
    except Exception as e:
        logger.error(f"Supplier o'chirishda xatolik: {e}")
        messages.error(request, "Xatolik yuz berdi. Qaytadan urinib ko'ring.")

    return redirect('supplier_list')


@login_required
def export_suppliers_csv(request):
    """Ta'minotchilarni CSV formatida eksport qilish"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="suppliers.csv"'

    # UTF-8 BOM qo'shish Excel uchun
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow([
        'Nomi', 'Telefon', 'Email', 'Manzil',
        'Kompaniya', 'INN', 'Dastlabki qarz', 'Joriy balans'
    ])

    suppliers = Supplier.objects.filter(is_active=True).select_related('created_by')

    for supplier in suppliers:
        writer.writerow([
            supplier.name,
            supplier.phone_number,
            supplier.email or '',
            supplier.address or '',
            supplier.company_name or '',
            supplier.inn or '',
            supplier.initial_debt,
            supplier.balance
        ])

    return response


@login_required
def import_suppliers_csv(request):
    """CSV orqali ta'minotchilarni import qilish"""
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')

        if not csv_file:
            messages.error(request, 'Fayl tanlanmagan.')
            return redirect('supplier_list')

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Faqat CSV fayllarni yuklash mumkin.')
            return redirect('supplier_list')

        try:
            # Pandas bilan CSV o'qish
            data = pd.read_csv(csv_file, encoding='utf-8')

            required_columns = ['Nomi', 'Telefon']
            missing_columns = [col for col in required_columns if col not in data.columns]

            if missing_columns:
                messages.error(request, f"Quyidagi ustunlar topilmadi: {', '.join(missing_columns)}")
                return redirect('supplier_list')

            created_count = 0
            updated_count = 0

            with transaction.atomic():
                for index, row in data.iterrows():
                    try:
                        supplier, created = Supplier.objects.update_or_create(
                            phone_number=row['Telefon'],
                            defaults={
                                'name': row['Nomi'],
                                'email': row.get('Email', ''),
                                'address': row.get('Manzil', ''),
                                'company_name': row.get('Kompaniya', ''),
                                'inn': row.get('INN', ''),
                                'initial_debt': row.get('Dastlabki qarz', 0),
                                'created_by': request.user,
                                'is_active': True
                            }
                        )

                        if created:
                            created_count += 1
                        else:
                            updated_count += 1

                    except Exception as e:
                        logger.error(f"Qator {index + 1} da xatolik: {e}")
                        continue

            messages.success(
                request,
                f"Import muvaffaqiyatli yakunlandi. "
                f"Yangi qo'shildi: {created_count}, Yangilandi: {updated_count}"
            )

        except Exception as e:
            logger.error(f"CSV import xatolik: {e}")
            messages.error(request, f"Import jarayonida xatolik: {str(e)}")

        return redirect('supplier_list')

    return render(request, 'partners/import_suppliers.html')


# ============= CUSTOMER VIEWS =============

@login_required
def customer_list(request):
    """Xaridorlar ro'yxati"""
    query = request.GET.get('q', '').strip()
    sort_by = request.GET.get('sort', 'name')

    valid_sort_fields = ['name', 'phone_number', 'created_at', '-created_at', 'balance']
    if sort_by not in valid_sort_fields:
        sort_by = 'name'

    customers = Customer.objects.select_related('created_by').filter(is_active=True)

    if query:
        customers = customers.filter(
            Q(name__icontains=query) |
            Q(phone_number__icontains=query) |
            Q(company_name__icontains=query) |
            Q(notes__icontains=query)
        )

    customers = customers.order_by(sort_by)

    paginator = Paginator(customers, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
        'sort': sort_by,
        'customer_form': CustomerForm(),
        'total_count': customers.count()
    }

    return render(request, 'partners/customer_list.html', context)


@login_required
def customer_create(request):
    """Yangi xaridor yaratish"""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    customer = form.save(commit=False)
                    customer.created_by = request.user
                    customer.save()

                # AJAX so'rov bo'lsa JSON javob
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success',
                        'message': "Xaridor muvaffaqiyatli qo'shildi.",
                        'customer': {
                            'id': customer.id,
                            'name': customer.name,
                            'phone_number': customer.phone_number,
                            'balance': float(customer.balance),
                        }
                    })

                messages.success(request, "Xaridor muvaffaqiyatli qo'shildi.")
                return redirect('customer_list')

            except Exception as e:
                logger.error(f"Customer yaratishda xatolik: {e}")
                error_msg = "Xatolik yuz berdi. Qaytadan urinib ko'ring."

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': error_msg
                    }, status=500)

                messages.error(request, error_msg)
        else:
            # Form xatoliklari
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = []
                for field, field_errors in form.errors.items():
                    for error in field_errors:
                        errors.append(f"{field}: {error}")

                return JsonResponse({
                    'status': 'error',
                    'message': "Forma ma'lumotlarini to'g'ri to'ldiring.",
                    'errors': errors
                }, status=400)

            messages.error(request, "Forma ma'lumotlarini to'g'ri to'ldiring.")
    else:
        form = CustomerForm()

    return render(request, 'partners/customer_form.html', {
        'form': form,
        'title': "Yangi xaridor qo'shish"
    })


@login_required
def customer_edit(request, pk):
    """Xaridorni tahrirlash"""
    customer = get_object_or_404(Customer, pk=pk, is_active=True)

    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            try:
                customer = form.save()

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Xaridor muvaffaqiyatli tahrirlandi.',
                        'customer': {
                            'id': customer.id,
                            'name': customer.name,
                            'phone_number': customer.phone_number,
                            'balance': float(customer.balance),
                        }
                    })

                messages.success(request, 'Xaridor muvaffaqiyatli tahrirlandi.')
                return redirect('customer_list')

            except Exception as e:
                logger.error(f"Customer tahrirlashda xatolik: {e}")
                error_msg = "Xatolik yuz berdi. Qaytadan urinib ko'ring."

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': error_msg
                    }, status=500)

                messages.error(request, error_msg)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = []
                for field, field_errors in form.errors.items():
                    for error in field_errors:
                        errors.append(f"{field}: {error}")

                return JsonResponse({
                    'status': 'error',
                    'message': "Forma ma'lumotlarini to'g'ri to'ldiring.",
                    'errors': errors
                }, status=400)

            messages.error(request, "Forma ma'lumotlarini to'g'ri to'ldiring.")
    else:
        form = CustomerForm(instance=customer)

        # AJAX so'rov bo'lsa form ma'lumotlarini qaytarish
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'form_data': {
                    'name': customer.name,
                    'phone_number': customer.phone_number,
                    'email': customer.email or '',
                    'address': customer.address or '',
                    'company_name': customer.company_name or '',
                    'inn': customer.inn or '',
                    'initial_debt': float(customer.initial_debt),
                    'credit_limit': float(customer.credit_limit),
                    'discount_percent': float(customer.discount_percent),
                    'notes': customer.notes or '',
                }
            })

    return render(request, 'partners/customer_form.html', {
        'form': form,
        'customer': customer,
        'title': f"{customer.name}ni tahrirlash"
    })


@login_required
@require_http_methods(["POST"])
def customer_delete(request, pk):
    """Xaridorni o'chirish"""
    customer = get_object_or_404(Customer, pk=pk, is_active=True)

    try:
        # Soft delete
        customer.is_active = False
        customer.save()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': f"{customer.name} muvaffaqiyatli o'chirildi.",
                'customer_id': pk
            })

        messages.success(request, f"{customer.name} muvaffaqiyatli o'chirildi.")

    except Exception as e:
        logger.error(f"Customer o'chirishda xatolik: {e}")
        error_msg = "Xatolik yuz berdi. Qaytadan urinib ko'ring."

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': error_msg
            }, status=500)

        messages.error(request, error_msg)

    return redirect('customer_list')


@login_required
def export_customers_csv(request):
    """Xaridorlarni CSV formatida eksport qilish"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="customers.csv"'

    # UTF-8 BOM qo'shish
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow([
        'Nomi', 'Telefon', 'Email', 'Manzil', 'Kompaniya',
        'INN', 'Dastlabki qarz', 'Kredit limiti',
        'Chegirma foizi', 'Joriy balans', 'Izoh'
    ])

    customers = Customer.objects.filter(is_active=True).select_related('created_by')

    for customer in customers:
        writer.writerow([
            customer.name,
            customer.phone_number,
            customer.email or '',
            customer.address or '',
            customer.company_name or '',
            customer.inn or '',
            customer.initial_debt,
            customer.credit_limit,
            customer.discount_percent,
            customer.balance,
            customer.notes or ''
        ])

    return response


@login_required
def import_customers_csv(request):
    """CSV orqali xaridorlarni import qilish"""
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')

        if not csv_file:
            messages.error(request, 'Fayl tanlanmagan.')
            return redirect('customer_list')

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Faqat CSV fayllarni yuklash mumkin.')
            return redirect('customer_list')

        try:
            data = pd.read_csv(csv_file, encoding='utf-8')

            required_columns = ['Nomi', 'Telefon']
            missing_columns = [col for col in required_columns if col not in data.columns]

            if missing_columns:
                messages.error(request, f"Quyidagi ustunlar topilmadi: {', '.join(missing_columns)}")
                return redirect('customer_list')

            created_count = 0
            updated_count = 0

            with transaction.atomic():
                for index, row in data.iterrows():
                    try:
                        customer, created = Customer.objects.update_or_create(
                            phone_number=row['Telefon'],
                            defaults={
                                'name': row['Nomi'],
                                'email': row.get('Email', ''),
                                'address': row.get('Manzil', ''),
                                'company_name': row.get('Kompaniya', ''),
                                'inn': row.get('INN', ''),
                                'initial_debt': row.get('Dastlabki qarz', 0),
                                'credit_limit': row.get('Kredit limiti', 0),
                                'discount_percent': row.get('Chegirma foizi', 0),
                                'notes': row.get('Izoh', ''),
                                'created_by': request.user,
                                'is_active': True
                            }
                        )

                        if created:
                            created_count += 1
                        else:
                            updated_count += 1

                    except Exception as e:
                        logger.error(f"Qator {index + 1} da xatolik: {e}")
                        continue

            messages.success(
                request,
                f"Import muvaffaqiyatli yakunlandi. "
                f"Yangi qo'shildi: {created_count}, Yangilandi: {updated_count}"
            )

        except Exception as e:
            logger.error(f"CSV import xatolik: {e}")
            messages.error(request, f"Import jarayonida xatolik: {str(e)}")

        return redirect('customer_list')

    return render(request, 'partners/import_customers.html')


# ============= PAYMENT VIEWS =============

@login_required
def supplier_payment_create(request):
    """Ta'minotchiga to'lov yaratish"""
    if request.method == 'POST':
        form = SupplierPaymentForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    payment = form.save(commit=False)
                    payment.created_by = request.user
                    payment.save()

                messages.success(request, "To'lov muvaffaqiyatli qo'shildi.")
                return redirect('supplier_payment_list')

            except Exception as e:
                logger.error(f"Supplier payment yaratishda xatolik: {e}")
                messages.error(request, "Xatolik yuz berdi. Qaytadan urinib ko'ring.")
        else:
            messages.error(request, "Forma ma'lumotlarini to'g'ri to'ldiring.")
    else:
        form = SupplierPaymentForm()

    return render(request, 'partners/supplier_payment_form.html', {
        'form': form,
        'title': "Yangi ta'minotchi to'lovi"
    })


@login_required
def supplier_payment_list(request):
    """Ta'minotchi to'lovlari ro'yxati"""
    query = request.GET.get('q', '').strip()
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')

    payments = SupplierPayment.objects.select_related('supplier', 'created_by').order_by('-date', '-created_at')

    if query:
        payments = payments.filter(
            Q(supplier__name__icontains=query) |
            Q(note__icontains=query) |
            Q(reference_number__icontains=query)
        )

    # Sana filtri
    if start_date_str and end_date_str:
        try:
            start_date = parse_date(start_date_str)
            end_date = parse_date(end_date_str)
            if start_date and end_date:
                payments = payments.filter(date__range=[start_date, end_date])
        except ValueError:
            messages.warning(request, "Sana formati noto'g'ri.")

    paginator = Paginator(payments, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'total_count': payments.count()
    }

    return render(request, 'partners/supplier_payment_list.html', context)


@login_required
def customer_payment_create(request):
    """Xaridordan to'lov yaratish"""
    if request.method == 'POST':
        form = CustomerPaymentForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    payment = form.save(commit=False)
                    payment.created_by = request.user
                    payment.save()

                messages.success(request, "To'lov muvaffaqiyatli qo'shildi.")
                return redirect('customer_payment_list')

            except Exception as e:
                logger.error(f"Customer payment yaratishda xatolik: {e}")
                messages.error(request, "Xatolik yuz berdi. Qaytadan urinib ko'ring.")
        else:
            messages.error(request, "Forma ma'lumotlarini to'g'ri to'ldiring.")
    else:
        form = CustomerPaymentForm()

    return render(request, 'partners/customer_payment_form.html', {
        'form': form,
        'title': "Yangi xaridor to'lovi"
    })


@login_required
def customer_payment_list(request):
    """Xaridor to'lovlari ro'yxati"""
    query = request.GET.get('q', '').strip()
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')

    payments = CustomerPayment.objects.select_related('customer', 'created_by').order_by('-date', '-created_at')

    if query:
        payments = payments.filter(
            Q(customer__name__icontains=query) |
            Q(note__icontains=query) |
            Q(reference_number__icontains=query)
        )

    # Sana filtri
    if start_date_str and end_date_str:
        try:
            start_date = parse_date(start_date_str)
            end_date = parse_date(end_date_str)
            if start_date and end_date:
                payments = payments.filter(date__range=[start_date, end_date])
        except ValueError:
            messages.warning(request, "Sana formati noto'g'ri.")

    paginator = Paginator(payments, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'total_count': payments.count()
    }

    return render(request, 'partners/customer_payment_list.html', context)