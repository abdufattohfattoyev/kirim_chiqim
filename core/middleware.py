
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from .models import Permission

class PermissionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.menu_url_mapping = {
            'kirim': 'kirim_list',
            'chiqim': 'chiqim_list',
            'ombor': 'ombor_list',
            'taminotchilar': 'supplier_list',
            'taminotchi_tolov': 'supplier_payment_list',
            'xaridorlar': 'customer_list',
            'xaridor_tolov': 'customer_payment_list',
            'hisobot': 'report',
            'foydalanuvchilar': 'user_list',
        }

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_superuser:
            path = request.path_info
            for menu, url_name in self.menu_url_mapping.items():
                url = reverse(url_name)
                if path.startswith(url):
                    if not Permission.objects.filter(
                        user=request.user,
                        menu=menu,
                        permission_type='view'
                    ).exists():
                        messages.error(request, f"Sizda {menu} bo‘limiga kirish ruxsati yo‘q.")
                        return redirect('dashboard')
        return self.get_response(request)
