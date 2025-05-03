
from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Product, Category, Incoming, IncomingItem, Outgoing
from .views import import_products_csv
from partners.models import Supplier, Customer
from django.core.files.uploadedfile import SimpleUploadedFile
import csv
import io

User = get_user_model()

class InventoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        self.category = Category.objects.create(name='Elektronika')
        self.product = Product.objects.create(name='Telefon', category=self.category, quantity=100)
        self.supplier = Supplier.objects.create(name='Ali', phone_number='+998901234567', created_by=self.user)
        self.customer = Customer.objects.create(name='Vali', phone_number='+998912345678', created_by=self.user)

    def test_create_incoming(self):
        incoming = Incoming.objects.create(
            supplier=self.supplier,
            total_amount=1000000,
            paid_amount=500000,
            debt=500000,
            created_by=self.user
        )
        IncomingItem.objects.create(
            incoming=incoming,
            product=self.product,
            quantity=10,
            price=100000,
            total=1000000
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 110)  # 100 + 10
        self.assertEqual(incoming.debt, 500000)

    def test_create_outgoing_insufficient_quantity(self):
        response = self.client.post('/inventory/chiqim/create/', {
            'customer': self.customer.id,
            'total_amount': 1000000,
            'paid_amount': 500000,
            'items-TOTAL_FORMS': 1,
            'items-INITIAL_FORMS': 0,
            'items-0-product': self.product.id,
            'items-0-quantity': 150,  # Omborda faqat 100 ta bor
            'items-0-price': 10000,
        })
        self.assertContains(response, 'yetarli miqdor mavjud emas')

    def test_import_products_csv(self):
        csv_content = "Mahsulot nomi,Kategoriya,Miqdor\nSmartfon,Elektronika,50"
        csv_file = SimpleUploadedFile("test.csv", csv_content.encode('utf-8'), content_type='text/csv')
        response = self.client.post('/inventory/ombor/import/', {'csv_file': csv_file})
        self.assertEqual(response.status_code, 302)  # Redirect
        product = Product.objects.get(name='Smartfon')
        self.assertEqual(product.quantity, 50)
        self.assertEqual(product.category.name, 'Elektronika')

    def test_export_products_csv(self):
        response = self.client.get('/inventory/ombor/export/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        content = response.content.decode('utf-8')
        self.assertIn('Telefon,Elektronika,100', content)
