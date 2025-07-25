from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from inventory.models import Incoming, Outgoing, Category, Product
from partners.models import Supplier, Customer, SupplierPayment, CustomerPayment
from django.db.models import Sum
from datetime import datetime, timedelta
from django.utils.dateparse import parse_date


@login_required
def report_view(request):
    # Sana filtri
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date and end_date:
        start_date = parse_date(start_date)
        end_date = parse_date(end_date)
    else:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)

    # Kirim va Chiqim summalari
    incoming_data = Incoming.objects.filter(date__range=[start_date, end_date]) \
        .values('date') \
        .annotate(total=Sum('total_amount')) \
        .order_by('date')

    outgoing_data = Outgoing.objects.filter(date__range=[start_date, end_date]) \
        .values('date') \
        .annotate(total=Sum('total_amount')) \
        .order_by('date')

    # Qarzdorlik bo'yicha
    supplier_debt_data = Supplier.objects.annotate(
        total_debt=Sum('incoming__debt') + Sum('initial_debt')
    ).values('name', 'total_debt')

    customer_debt_data = Customer.objects.annotate(
        total_debt=Sum('outgoing__debt') + Sum('initial_debt')
    ).values('name', 'total_debt')

    # Jami qarzdorlik
    total_supplier_debt = supplier_debt_data.aggregate(total=Sum('total_debt'))['total'] or 0
    total_customer_debt = customer_debt_data.aggregate(total=Sum('total_debt'))['total'] or 0

    # Kategoriyalar bo'yicha mahsulotlar
    category_data = Category.objects.annotate(
        total_quantity=Sum('product__quantity')
    ).values('name', 'total_quantity')

    # Foyda
    profit_data = Outgoing.objects.filter(date__range=[start_date, end_date]) \
        .values('date') \
        .annotate(total_profit=Sum('profit')) \
        .order_by('date')

    total_profit = profit_data.aggregate(total=Sum('total_profit'))['total'] or 0

    # To'lovlar
    supplier_payments = SupplierPayment.objects.filter(date__range=[start_date, end_date]) \
                            .aggregate(total=Sum('amount'))['total'] or 0
    customer_payments = CustomerPayment.objects.filter(date__range=[start_date, end_date]) \
                            .aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'incoming_data': list(incoming_data),
        'outgoing_data': list(outgoing_data),
        'supplier_debt_data': list(supplier_debt_data),
        'customer_debt_data': list(customer_debt_data),
        'category_data': list(category_data),
        'profit_data': list(profit_data),
        'supplier_payments': supplier_payments,
        'customer_payments': customer_payments,
        'total_supplier_debt': total_supplier_debt,
        'total_customer_debt': total_customer_debt,
        'total_profit': total_profit,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
    }
    return render(request, 'reports/report.html', context)
