
from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Supplier, Customer
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

class PartnersTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')

    def test_create_supplier(self):
        supplier = Supplier.objects.create(
            name='Ali',
            phone_number='+998901234567',
            address='Toshkent',
            initial_debt=100000,
            created_by=self.user
        )
        self.assertEqual(Supplier.objects.count(), 1)
        self.assertEqual(supplier.initial_debt, 100000)

    def test_import_suppliers_csv(self):
        csv_content = "Nomi,Telefon,Manzil,Dastlabki qarz\nAli,+998901234567,Toshkent,100000"
        csv_file = SimpleUploadedFile("test.csv", csv_content.encode('utf-8'), content_type='text/csv')
        response = self.client.post('/partners/suppliers/import/', {'csv_file': csv_file})
        self.assertEqual(response.status_code, 302)
        supplier = Supplier.objects.get(name='Ali')
        self.assertEqual(supplier.phone_number, '+998901234567')
        self.assertEqual(supplier.initial_debt, 100000)

    def test_export_suppliers_csv(self):
        Supplier.objects.create(
            name='Ali',
            phone_number='+998901234567',
            address='Toshkent',
            initial_debt=100000,
            created_by=self.user
        )
        response = self.client.get('/partners/suppliers/export/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        content = response.content.decode('utf-8')
        self.assertIn('Ali,+998901234567,Toshkent,100000', content)
