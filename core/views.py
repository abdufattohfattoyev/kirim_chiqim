from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from django.db import transaction
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import ListView
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import ValidationError
import logging

from inventory.models import Product, Outgoing, Incoming
from .models import User, Permission, UserSession
from .forms import UserForm, PermissionFormSet, LoginForm

# Setup logging
logger = logging.getLogger(__name__)


def is_superuser(user):
    """Helper function to check if user is superuser"""
    return user.is_superuser


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    Handle user login with enhanced security
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = LoginForm(request.POST or None)  # Instantiate the form

    if request.method == 'POST':
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            remember_me = form.cleaned_data.get('remember_me')

            user = authenticate(request, username=username, password=password)

            if user is not None:
                if user.is_active:
                    login(request, user)

                    # Set session expiry based on remember_me
                    if not remember_me:
                        request.session.set_expiry(0)  # Session expires on browser close
                    else:
                        request.session.set_expiry(1209600)  # 2 weeks

                    # Log user session
                    try:
                        UserSession.objects.create(
                            user=user,
                            session_key=request.session.session_key,
                            ip_address=get_client_ip(request),
                            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
                        )
                    except Exception as e:
                        logger.error(f"Session logging error for user {username}: {str(e)}")

                    messages.success(request, f'Xush kelibsiz, {user.username}!')

                    # Redirect to next page if available
                    next_page = request.GET.get('next', 'dashboard')
                    return redirect(next_page)
                else:
                    messages.error(request, 'Hisobingiz faol emas. Administrator bilan bog\'laning.')
            else:
                messages.error(request, 'Foydalanuvchi nomi yoki parol xato.')
                logger.warning(f"Failed login attempt for username: {username} from IP: {get_client_ip(request)}")
        else:
            # Display form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{form[field].label}: {error}')

    return render(request, 'core/login.html', {'form': form})  # Pass form to template

@login_required
def logout_view(request):
    """
    Handle user logout with session cleanup
    """
    try:
        # Deactivate user session
        UserSession.objects.filter(
            user=request.user,
            session_key=request.session.session_key
        ).update(is_active=False)

        username = request.user.username
        logout(request)
        messages.success(request, f'{username}, tizimdan muvaffaqiyatli chiqdingiz.')

    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        logout(request)

    return redirect('login')


@login_required
def dashboard_view(request):
    """
    Main dashboard view with user statistics and warehouse metrics
    """
    # Get today's date for filtering
    today = date.today()

    # Initialize context
    context = {
        'user_menus': request.user.get_user_menus(),
        'total_users': User.objects.count() if request.user.is_superuser else None,
        'active_sessions': UserSession.objects.filter(is_active=True).count() if request.user.is_superuser else None,
        'total_products': 0,
        'today_incoming': 0,
        'today_outgoing': 0,
        'warnings_count': 0,
        'recent_activities': [],
        'low_stock_products': [],
    }

    try:
        # Total products (assuming Product model has a quantity field)
        context['total_products'] = Product.objects.count()

        # Today's incoming transactions (assuming Incoming model has date and quantity fields)
        context['today_incoming'] = Incoming.objects.filter(
            date__date=today
        ).count()

        # Today's outgoing transactions (assuming Outgoing model has date and quantity fields)
        context['today_outgoing'] = Outgoing.objects.filter(
            date__date=today
        ).count()

        # Low stock products (assuming Product model has quantity and warning_threshold fields)
        context['low_stock_products'] = Product.objects.filter(
            quantity__lte=5
        )[:5]  # Limit to 5 for display

        # Warnings count (products with quantity < warning_threshold, default 5)
        context['warnings_count'] = Product.objects.filter(
            quantity__lte=5
        ).count()



    except Exception as e:
        # Log error and keep default values to prevent crashes
        logger.error(f"Error fetching dashboard data: {str(e)}")

    return render(request, 'index.html', context)


@login_required
@user_passes_test(is_superuser, login_url='dashboard')
def user_permissions(request, user_id):
    """
    View user permissions details
    """
    user = get_object_or_404(User, id=user_id)
    permissions = user.permissions.select_related().order_by('menu', 'permission_type')

    context = {
        'user': user,
        'permissions': permissions,
        'menu_choices': Permission.MENU_CHOICES,
        'permission_types': Permission.PERMISSION_TYPES,
    }

    return render(request, 'core/user_permissions.html', context)

@login_required
@user_passes_test(is_superuser, login_url='dashboard')
def user_list(request):
    """
    Display list of all users with pagination and search
    """
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')

    users = User.objects.all().order_by('-date_joined')

    # Apply search filter
    if search_query:
        users = users.filter(username__icontains=search_query)

    # Apply role filter
    if role_filter:
        users = users.filter(role=role_filter)

    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
        'role_choices': User.ROLE_CHOICES,
        'total_count': users.count(),
    }

    return render(request, 'core/user_list.html', context)


@login_required
@user_passes_test(is_superuser, login_url='dashboard')
@csrf_protect
def user_create(request):
    """
    Create new user with permissions
    """
    if request.method == 'POST':
        form = UserForm(request.POST)
        formset = PermissionFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)

                    # Set password if provided
                    if form.cleaned_data.get('password'):
                        user.set_password(form.cleaned_data['password'])

                    user.save()

                    # Save permissions
                    formset.instance = user
                    formset.save()

                    messages.success(request, f'Foydalanuvchi "{user.username}" muvaffaqiyatli qo\'shildi.')
                    logger.info(f"New user created: {user.username} by {request.user.username}")

                    return redirect('user_list')

            except Exception as e:
                messages.error(request, f'Xatolik yuz berdi: {str(e)}')
                logger.error(f"User creation error: {str(e)}")
        else:
            # Display form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{form[field].label}: {error}')
    else:
        form = UserForm()
        formset = PermissionFormSet()

    context = {
        'form': form,
        'formset': formset,
        'title': 'Yangi foydalanuvchi qo\'shish',
        'submit_text': 'Qo\'shish',
    }

    return render(request, 'core/user_form.html', context)


@login_required
@user_passes_test(is_superuser, login_url='dashboard')
@csrf_protect
def user_edit(request, user_id):
    """
    Edit existing user and permissions
    """
    user = get_object_or_404(User, id=user_id)

    # Prevent editing of superuser by non-superuser (additional security)
    if user.is_superuser and not request.user.is_superuser:
        messages.error(request, 'Super admin foydalanuvchini tahrirlash mumkin emas.')
        return redirect('user_list')

    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        formset = PermissionFormSet(request.POST, instance=user)

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)

                    # Update password if provided
                    if form.cleaned_data.get('password'):
                        user.set_password(form.cleaned_data['password'])

                    user.save()

                    # Save permissions
                    formset.save()

                    messages.success(request, f'Foydalanuvchi "{user.username}" muvaffaqiyatli yangilandi.')
                    logger.info(f"User updated: {user.username} by {request.user.username}")

                    return redirect('user_list')

            except Exception as e:
                messages.error(request, f'Xatolik yuz berdi: {str(e)}')
                logger.error(f"User update error: {str(e)}")
        else:
            # Display form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{form[field].label}: {error}')
    else:
        form = UserForm(instance=user)
        formset = PermissionFormSet(instance=user)

    context = {
        'form': form,
        'formset': formset,
        'user': user,
        'title': f'"{user.username}" foydalanuvchisini tahrirlash',
        'submit_text': 'Yangilash',
    }

    return render(request, 'core/user_form.html', context)


@login_required
@user_passes_test(is_superuser, login_url='dashboard')
@require_http_methods(["POST"])
def user_delete(request, user_id):
    """
    Delete user (AJAX request)
    """
    user = get_object_or_404(User, id=user_id)

    # Prevent deleting superuser
    if user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Super admin foydalanuvchini o\'chirish mumkin emas.'})

    # Prevent self-deletion
    if user.id == request.user.id:
        return JsonResponse({'success': False, 'message': 'O\'zingizni o\'chira olmaysiz.'})

    try:
        username = user.username
        user.delete()
        logger.info(f"User deleted: {username} by {request.user.username}")
        return JsonResponse({'success': True, 'message': f'Foydalanuvchi "{username}" muvaffaqiyatli o\'chirildi.'})
    except Exception as e:
        logger.error(f"User deletion error: {str(e)}")
        return JsonResponse({'success': False, 'message': f'Xatolik yuz berdi: {str(e)}'})


@login_required
@user_passes_test(is_superuser, login_url='dashboard')
def user_permissions(request, user_id):
    """
    View user permissions details
    """
    user = get_object_or_404(User, id=user_id)
    permissions = user.permissions.select_related().order_by('menu', 'permission_type')

    context = {
        'user': user,
        'permissions': permissions,
        'menu_choices': Permission.MENU_CHOICES,
        'permission_types': Permission.PERMISSION_TYPES,
    }

    return render(request, 'core/user_permissions.html', context)


@login_required
def user_profile(request):
    """
    View and edit current user's profile
    """
    if request.method == 'POST':
        # Handle profile update (basic fields only)
        username = request.POST.get('username', '').strip()
        if username and username != request.user.username:
            if not User.objects.filter(username=username).exists():
                request.user.username = username
                request.user.save()
                messages.success(request, 'Profil muvaffaqiyatli yangilandi.')
            else:
                messages.error(request, 'Bu foydalanuvchi nomi allaqachon mavjud.')

    context = {
        'user': request.user,
        'user_permissions': request.user.permissions.all() if not request.user.is_superuser else None,
        'recent_sessions': UserSession.objects.filter(user=request.user, is_active=True)[:5],
    }

    return render(request, 'core/user_profile.html', context)