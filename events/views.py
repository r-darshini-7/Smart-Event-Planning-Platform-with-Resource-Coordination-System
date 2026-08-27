from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.db.models import Q, Count
from django.urls import reverse
from django.utils import timezone
from django.utils import translation
from django.utils.text import slugify
from django.core.mail import send_mail
from functools import wraps
import json
import re
from datetime import datetime

import base64
import io
import urllib.parse

from .models import (
    Category, Event, EventMember, EventWish, UserMark, Profile, Notification,
    Venue, Resource, Vendor, Sponsor,
    VenueBooking, ResourceAllocation, VendorAssignment,
    BudgetItem, ApprovalRequest, EventLifecycleLog,
)
from .translations import translate_text
from .forms  import (
    CategoryForm, EventForm, EventCreateForm,
    EventMemberForm, EventRegistrationForm, UpdateMemberStatusForm,
    EventWishForm, UserMarkForm, ProfileForm,
    VenueForm, ResourceForm, VendorForm, SponsorForm,
    VenueBookingForm, ResourceAllocationForm, VendorAssignmentForm,
    BudgetItemForm, ApprovalRequestForm, UpdateMemberAttendeeCategoryForm,
)


# ══════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════
def _get_request_language(request):
    return 'en'


def _is_admin_email(email):
    """Return True for organization addresses, while keeping Gmail user-only."""
    normalized_email = (email or '').strip().lower()
    domain = normalized_email.rsplit('@', 1)[-1]
    return '@' in normalized_email and bool(domain and domain != 'gmail.com')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        identifier = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # allow login by email or username
        username = identifier
        if '@' in identifier:
            try:
                user_obj = User.objects.filter(email__iexact=identifier).first()
                if user_obj:
                    username = user_obj.username
            except Exception:
                username = identifier

        user = authenticate(request, username=username, password=password)
        if user:
            is_admin_login = user.is_superuser or _is_admin_email(user.email)
            if is_admin_login and not user.is_staff and not user.is_superuser:
                user.is_staff = True
                user.save(update_fields=['is_staff'])
            login(request, user)
            messages.success(request, translate_text(f'Welcome back, {user.get_full_name() or user.username}!', _get_request_language(request)))
            return redirect('dashboard')
        else:
            messages.error(request, translate_text('Invalid username or password.', _get_request_language(request)))
    return render(request, 'events/login.html')


def signup_view(request):
    """Simple signup for regular users. Creates User + Profile and logs them in."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('confirm_password', '')

        if not (name and email and password and password2):
            messages.error(request, translate_text('Please fill all required fields.', _get_request_language(request)))
            return render(request, 'events/signup.html')
        if password != password2:
            messages.error(request, translate_text('Passwords do not match.', _get_request_language(request)))
            return render(request, 'events/signup.html')
        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, translate_text('An account with that email already exists.', _get_request_language(request)))
            return render(request, 'events/signup.html')

        # create username from email localpart if possible
        base_username = email.split('@')[0]
        username = base_username
        counter = 0
        while User.objects.filter(username=username).exists():
            counter += 1
            username = f"{base_username}{counter}"

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=_is_admin_email(email),
        )
        # set full name
        if ' ' in name:
            parts = name.split(None, 1)
            user.first_name = parts[0]
            user.last_name = parts[1]
        else:
            user.first_name = name
        user.save()

        # update profile
        try:
            profile = user.profile
            profile.phone = phone
            profile.contact_email = email
            profile.save()
        except Exception:
            pass

        login(request, user)
        messages.success(request, translate_text(f'Welcome, {user.get_full_name() or user.username}!', _get_request_language(request)))
        return redirect('dashboard')
    return render(request, 'events/signup.html')


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, translate_text('Admin access required for that action.', _get_request_language(request)))
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped


def logout_view(request):
    logout(request)
    messages.info(request, translate_text('You have been logged out.', _get_request_language(request)))
    return redirect('login')


@login_required
def profile_view(request):
    profile = getattr(request.user, 'profile', None)
    if profile is None:
        profile = Profile.objects.create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, translate_text('Profile updated successfully.', _get_request_language(request)))
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'events/profile.html', {
        'form': form,
    })


@login_required
def settings_view(request):
    if not request.session.session_key:
        request.session.save()
    current_session_key = request.session.session_key

    user_sessions = []
    for session in Session.objects.filter(expire_date__gt=timezone.now()):
        try:
            data = session.get_decoded()
        except Exception:
            continue
        if str(data.get('_auth_user_id')) != str(request.user.id):
            continue
        user_sessions.append({
            'key': session.session_key,
            'key_short': (session.session_key or '')[:8],
            'expire_date': session.expire_date,
            'current': session.session_key == current_session_key,
        })

    user_sessions.sort(key=lambda item: (not item['current'], item['expire_date']))

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'change_password':
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')
            if not request.user.check_password(current_password):
                messages.error(request, translate_text('Current password is incorrect.', _get_request_language(request)))
            elif not new_password:
                messages.error(request, translate_text('New password cannot be blank.', _get_request_language(request)))
            elif new_password != confirm_password:
                messages.error(request, translate_text('New passwords do not match.', _get_request_language(request)))
            else:
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, translate_text('Password updated successfully.', _get_request_language(request)))
            return redirect('settings')

        if action == 'sign_out_other_sessions':
            deleted = 0
            for session in user_sessions:
                if session['key'] != current_session_key:
                    Session.objects.filter(session_key=session['key']).delete()
                    deleted += 1
            messages.success(request, translate_text(f'Signed out {deleted} other session(s).', _get_request_language(request)))
            return redirect('settings')

        if action == 'delete_account':
            if request.POST.get('confirm_delete') == 'yes':
                logout(request)
                request.user.delete()
                messages.success(request, translate_text('Your account has been deleted.', _get_request_language(request)))
                return redirect('signup')
            messages.error(request, translate_text('Please confirm account deletion to proceed.', _get_request_language(request)))
            return redirect('settings')

    context = {
        'preferred_language': 'en',
        'active_sessions': user_sessions,
        'current_session_key': current_session_key,
    }
    return render(request, 'events/settings.html', context)


# ══════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════
@login_required
def dashboard(request):
    now = timezone.now()

    if request.user.is_staff:
        from django.db.models import Sum
        total_categories  = Category.objects.count()
        total_events      = Event.objects.count()
        total_registrations = EventMember.objects.count()
        completed_events  = Event.objects.filter(status='completed').count()
        live_events       = Event.objects.filter(status='live').order_by('-start_time')[:10]
        categories        = Category.objects.all()[:10]
        active_categories = Category.objects.filter(status='active')
        ongoing_events    = Event.objects.filter(status='live', start_time__lte=now, end_time__gte=now)
        # New ERP stats
        total_venues      = Venue.objects.count()
        available_venues  = Venue.objects.filter(status='available').count()
        total_resources   = Resource.objects.count()
        total_vendors     = Vendor.objects.count()
        active_vendors    = Vendor.objects.filter(status='active').count()
        total_sponsors    = Sponsor.objects.count()
        pending_approvals = ApprovalRequest.objects.filter(status='pending').count()
        total_budget      = Event.objects.aggregate(t=Sum('total_budget'))['t'] or 0
        total_expenses    = BudgetItem.objects.aggregate(t=Sum('actual_amount'))['t'] or 0

        registration_chart = (
            Event.objects.filter(status='live')
            .select_related('category')
            .annotate(registration_count=Count('members', distinct=True))
            .order_by('-registration_count', 'title')[:10]
        )

        registration_chart_labels = [
            event.category.name if event.category else 'Uncategorized'
            for event in registration_chart
        ]
        registration_chart_counts = [
            int(event.registration_count) for event in registration_chart
        ]

        context = {
            'total_categories':   total_categories,
            'total_events':       total_events,
            'total_registrations': total_registrations,
            'completed_events':   completed_events,
            'live_events':        live_events,
            'categories':         categories,
            'active_categories':  active_categories,
            'ongoing_events':     ongoing_events,
            'registration_chart_labels': registration_chart_labels,
            'registration_chart_counts': registration_chart_counts,
            # New ERP context
            'total_venues':       total_venues,
            'available_venues':   available_venues,
            'total_resources':    total_resources,
            'total_vendors':      total_vendors,
            'active_vendors':     active_vendors,
            'total_sponsors':     total_sponsors,
            'pending_approvals':  pending_approvals,
            'total_budget':       total_budget,
            'total_expenses':     total_expenses,
        }
        return render(request, 'events/dashboard.html', context)

    selected_event_type = request.GET.get('event_type', '').strip()

    events = Event.objects.filter(status='live').select_related('category').order_by('-start_time')
    if selected_event_type:
        events = events.filter(event_type=selected_event_type)

    # labels for display in template
    event_type_labels = dict(Event.EVENT_TYPE_CHOICES)

    # compute counts of live events per event_type for the card display
    event_type_items = []  # list of (value, label, count)
    for key, label in Event.EVENT_TYPE_CHOICES:
        count = Event.objects.filter(status='live', event_type=key).count()
        event_type_items.append((key, label, count))

    context = {
        'events': events,
        'selected_event_type': selected_event_type,
        'event_type_choices': Event.EVENT_TYPE_CHOICES,
        'event_type_labels': event_type_labels,
        'event_type_items': event_type_items,
        'total_events': events.count(),
        'live_events': events[:6],
    }
    # compute a friendly display label for the selected event type to avoid
    # doing dict lookups in the template (which can cause parsing errors)
    if selected_event_type:
        context['selected_event_type_display'] = event_type_labels.get(selected_event_type, selected_event_type)
    else:
        context['selected_event_type_display'] = ''
    return render(request, 'events/dashboard.html', context)


@login_required
def events_by_type(request, event_type):
    """Show a dedicated page listing events for a given event_type."""
    now = timezone.now()
    # show all events for that type (regardless of status) so users can see admin-created events;
    # non-live events will be visually marked as unpublished in the template
    events = Event.objects.filter(event_type=event_type).select_related('category').order_by('-start_time')

    # also compute total events for this type (any status) to help debug missing live events
    total_for_type = Event.objects.filter(event_type=event_type).count()

    # human friendly label
    event_type_label = dict(Event.EVENT_TYPE_CHOICES).get(event_type, event_type)

    return render(request, 'events/events_by_type.html', {
        'events': events,
        'event_type': event_type,
        'event_type_label': event_type_label,
        'total_for_type': total_for_type,
        'has_any_for_type': total_for_type > 0,
    })


# ══════════════════════════════════════════════
#  CATEGORY CRUD
# ══════════════════════════════════════════════
@admin_required
def send_message_view(request):
    if request.method != 'POST':
        return redirect('dashboard')

    title = (request.POST.get('title') or '').strip()
    message = (request.POST.get('message') or '').strip()
    target_scope = (request.POST.get('target_scope') or 'both').strip()
    if title and message:
        Notification.objects.create(
            title=title,
            message=message,
            kind='message',
            target_scope=target_scope,
            created_by=request.user,
        )
        messages.success(request, 'Message sent to the selected audience.')
    else:
        messages.error(request, 'Please provide both a title and a message.')

    referer = request.META.get('HTTP_REFERER') or reverse('dashboard')
    return redirect(referer)


@admin_required
def create_event_category(request):
    form = CategoryForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Category created successfully.')
        return redirect('event_category')
    return render(request, 'events/create_event_category.html', {'form': form})


@login_required
def event_category(request):
    query       = request.GET.get('q', '').strip()
    status_f    = request.GET.get('status', '').strip()
    sort_by     = request.GET.get('sort', 'priority').strip()

    VALID_SORTS = ['priority', 'name', '-name', '-created_at']
    if sort_by not in VALID_SORTS:
        sort_by = 'priority'

    categories = Category.objects.all()
    if query:
        from django.db.models import Q
        categories = categories.filter(
            Q(name__icontains=query) | Q(code__icontains=query)
        )
    if request.user.is_staff and status_f:
        categories = categories.filter(status=status_f)

    categories = categories.order_by(sort_by)

    return render(request, 'events/event_category.html', {
        'categories': categories,
        'filter_search': query,
        'filter_status': status_f,
        'filter_sort': sort_by,
    })


@admin_required
def edit_event_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, request.FILES or None, instance=category)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Category updated successfully.')
        return redirect('event_category')
    return render(request, 'events/edit_event_category.html', {'form': form, 'category': category})


@admin_required
def event_category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Category deleted.')
        return redirect('event_category')
    return render(request, 'events/event_category_delete.html', {'category': category})


# ══════════════════════════════════════════════
#  EVENT CRUD
# ══════════════════════════════════════════════
@admin_required
def create_event(request):
    # Support editing an existing event via ?edit=<pk> (or POST 'edit') so admins
    # can use the same create form to update events.
    edit_id = request.GET.get('edit') or request.POST.get('edit')
    event_instance = None
    if edit_id:
        try:
            event_instance = Event.objects.get(pk=int(edit_id))
        except Exception:
            event_instance = None

    if request.method == 'POST':
        form = EventCreateForm(request.POST or None, request.FILES or None, instance=event_instance)
        # Debug: log raw POST data to help diagnose missing saves
        try:
            with open('create_event_debug.log', 'a', encoding='utf-8') as fh:
                fh.write(f"[{datetime.utcnow().isoformat()}] POST keys: {list(request.POST.keys())} files: {list(request.FILES.keys())}\n")
                try:
                    fh.write('POST data: ' + json.dumps(request.POST.dict(), ensure_ascii=False) + '\n')
                except Exception:
                    fh.write('POST data: (could not serialize)\n')
        except Exception:
            pass
    else:
        form = EventCreateForm(instance=event_instance)

    if request.method == 'POST' and form.is_valid():
        event = form.save(commit=False)
        category_type = form.cleaned_data.get('category_type')
        custom_name = form.cleaned_data.get('custom_category')
        category_name = custom_name if category_type == 'others' else category_type
        category = None
        if category_name:
            code = slugify(category_name)[:45] or 'category'
            category, created = Category.objects.get_or_create(
                name=category_name,
                defaults={'code': code, 'priority': 1, 'status': 'active'},
            )
            if created:
                suffix = 1
                original_code = category.code
                while Category.objects.filter(code=category.code).exclude(pk=category.pk).exists():
                    category.code = f"{original_code[:40]}-{suffix}"
                    suffix += 1
                category.save()
        event.category = category
        # If creating new event, set created_by. If editing, preserve original creator.
        if not event.pk:
            event.created_by = request.user
        # If the user entered a custom category name, try to infer a matching
        # event_type (so e.g. 'Hack 0 Thon' maps to 'hackathons' rather than 'others').
        if category:
            name_l = (category.name or '').lower()
            infer_map = [
                ('tech', 'tech_fest'),
                ('cultur', 'cultural'),
                ('hack', 'hackathons'),
                ('competition', 'competitions'),
                ('seminar', 'seminars'),
            ]
            for substr, code in infer_map:
                if substr in name_l:
                    event.event_type = code
                    break
        # Only auto-publish for new events; when editing preserve existing status
        if not event.pk:
            event.status = 'live'
        try:
            event.save()
        except Exception as e:
            # surface DB/save errors to the admin user
            messages.error(request, f'Error saving event: {e}')
            print('Error saving event:', e)
            try:
                with open('create_event_debug.log', 'a', encoding='utf-8') as fh:
                    fh.write(f"[{datetime.utcnow().isoformat()}] Save error: {e}\n")
            except Exception:
                pass
            # fall through to re-render the form with posted data and errors
        else:
            if event_instance:
                messages.success(request, f'Event "{event.title}" updated successfully.')
            else:
                messages.success(request, f'Event "{event.title}" created successfully.')
                Notification.objects.create(
                    title=f'New event: {event.title}',
                    message=f'"{event.title}" is now live for registration.',
                    kind='notification',
                    target_scope='both',
                    event=event,
                    created_by=request.user,
                )
            return redirect('event_list')
    elif request.method == 'POST' and not form.is_valid():
        # show validation errors to the user
        messages.error(request, 'Please fix the errors in the form.')
        # also log the errors for debugging to file
        try:
            with open('create_event_debug.log', 'a', encoding='utf-8') as fh:
                fh.write(f"[{datetime.utcnow().isoformat()}] Form invalid: {form.errors.as_json()}\n")
        except Exception:
            pass
        print('EventCreateForm errors:', form.errors)
    return render(request, 'events/create_event.html', {'form': form, 'event': event_instance})


@login_required
def event_list(request):
    from collections import OrderedDict
    query       = request.GET.get('q', '').strip()
    status_f    = request.GET.get('status', '').strip()
    event_type_f = request.GET.get('event_type', '').strip()
    category_f  = request.GET.get('category', '').strip()
    date_from   = request.GET.get('date_from', '').strip()
    date_to     = request.GET.get('date_to', '').strip()
    price_min   = request.GET.get('price_min', '').strip()
    price_max   = request.GET.get('price_max', '').strip()
    sort_by     = request.GET.get('sort', '-start_time').strip()

    VALID_SORTS = ['-start_time', 'start_time', 'title', '-title', 'price', '-price', '-created_at']
    if sort_by not in VALID_SORTS:
        sort_by = '-start_time'

    all_categories = Category.objects.all().order_by('name')

    if request.user.is_staff:
        events = Event.objects.select_related('category').all()
    else:
        events = Event.objects.filter(status='live').select_related('category')

    # ── shared filters ──
    if query:
        events = events.filter(
            Q(title__icontains=query) |
            Q(category__name__icontains=query) |
            Q(venue_name__icontains=query) |
            Q(description__icontains=query)
        )
    if event_type_f:
        events = events.filter(event_type=event_type_f)
    if category_f:
        events = events.filter(category__pk=category_f)
    if date_from:
        try:
            from django.utils.dateparse import parse_date
            df = parse_date(date_from)
            if df:
                events = events.filter(start_time__date__gte=df)
        except Exception:
            pass
    if date_to:
        try:
            from django.utils.dateparse import parse_date
            dt = parse_date(date_to)
            if dt:
                events = events.filter(start_time__date__lte=dt)
        except Exception:
            pass
    if price_min:
        try:
            events = events.filter(price__gte=float(price_min))
        except ValueError:
            pass
    if price_max:
        try:
            events = events.filter(price__lte=float(price_max))
        except ValueError:
            pass

    # ── admin-only filters ──
    if request.user.is_staff and status_f:
        events = events.filter(status=status_f)

    events = events.order_by(sort_by)

    filter_ctx = {
        'search_query': query,
        'filter_status': status_f,
        'filter_event_type': event_type_f,
        'filter_category': category_f,
        'filter_date_from': date_from,
        'filter_date_to': date_to,
        'filter_price_min': price_min,
        'filter_price_max': price_max,
        'filter_sort': sort_by,
        'all_categories': all_categories,
        'status_choices': Event.STATUS_CHOICES,
        'event_type_choices': Event.EVENT_TYPE_CHOICES,
        'valid_sorts': VALID_SORTS,
    }

    if request.user.is_staff:
        return render(request, 'events/event_list.html', {
            'events': events,
            **filter_ctx,
        })

    # User view — group by category
    events_by_category = OrderedDict()
    for e in events:
        cat = e.category.name if e.category else 'Uncategorized'
        if cat not in events_by_category:
            events_by_category[cat] = {'category_obj': e.category, 'events': []}
        events_by_category[cat]['events'].append(e)

    return render(request, 'events/event_list.html', {
        'events_by_category': events_by_category,
        'total_events': events.count(),
        **filter_ctx,
    })


@login_required
def event_detail(request, pk):
    event   = get_object_or_404(Event, pk=pk)
    members = EventMember.objects.filter(event=event).select_related('user')
    wishes  = EventWish.objects.filter(event=event).select_related('user')
    marks   = UserMark.objects.filter(event=event).select_related('user')
    is_registered = False
    if request.user.is_authenticated:
        is_registered = members.filter(user=request.user).exists()
    return render(request, 'events/event_detail.html', {
        'event': event, 'members': members, 'wishes': wishes, 'marks': marks,
        'is_registered': is_registered,
    })


@login_required
def pay_event_redirect(request, pk):
    event = get_object_or_404(Event, pk=pk)
    payment_mode = request.GET.get('payment_mode', '').strip()
    upi_id = request.GET.get('upi_id', '').strip()
    other_payment_mode = request.GET.get('other_payment_mode', '').strip()
    if payment_mode == 'other':
        payment_mode_label = other_payment_mode or 'Other'
    else:
        payment_mode_label = dict(EventRegistrationForm.PAYMENT_MODE_CHOICES).get(payment_mode, payment_mode or 'Other')
    if not upi_id and event.price > 0:
        messages.error(request, 'Please provide a UPI ID before proceeding to payment.')
        return redirect('register_event', pk=event.pk)
    upi_url = None
    if upi_id:
        upi_url = f"upi://pay?pa={urllib.parse.quote(upi_id)}&am={event.price}&tn={urllib.parse.quote(event.title)}"
    return render(request, 'events/pay_event.html', {
        'event': event,
        'payment_mode': payment_mode_label,
        'upi_id': upi_id,
        'upi_url': upi_url,
    })


@login_required
def register_event(request, pk):
    """Present a registration form and create an EventMember with QR code on submit."""
    event = get_object_or_404(Event, pk=pk)
    if event.status != 'live' and not request.user.is_staff:
        messages.error(request, 'Event is not open for registration.')
        return redirect('event_detail', pk=pk)

    existing_member = EventMember.objects.filter(event=event, user=request.user).first()
    if existing_member:
        return redirect('event_registration_qr', pk=existing_member.pk)

    if request.method == 'POST':
        form = EventRegistrationForm(request.POST, user=request.user, event=event)
        if form.is_valid():
            user = request.user
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()
            profile = getattr(user, 'profile', None)
            if profile:
                profile.phone = form.cleaned_data['phone']
                profile.location = form.cleaned_data.get('location', '')
                profile.save()

            registration_data = {
                'first_name': form.cleaned_data.get('first_name'),
                'last_name': form.cleaned_data.get('last_name'),
                'email': form.cleaned_data.get('email'),
                'phone': form.cleaned_data.get('phone'),
                'location': form.cleaned_data.get('location'),
                'gender': form.cleaned_data.get('gender'),
                'role': form.cleaned_data.get('role'),
                'other_role': form.cleaned_data.get('other_role'),
                'team_name': form.cleaned_data.get('team_name'),
                'college_id': form.cleaned_data.get('college_id'),
                'college_name': form.cleaned_data.get('college_name'),
                'domain': form.cleaned_data.get('domain'),
                'course': form.cleaned_data.get('course'),
                'other_course': form.cleaned_data.get('other_course'),
                'course_specialization': form.cleaned_data.get('course_specialization'),
                'year_of_study': form.cleaned_data.get('year_of_study'),
                'graduating_year': form.cleaned_data.get('graduating_year'),
                'employee_id': form.cleaned_data.get('employee_id'),
                'company_name': form.cleaned_data.get('company_name'),
                'job_role': form.cleaned_data.get('job_role') or form.cleaned_data.get('job_title'),
                'job_title': form.cleaned_data.get('job_title'),
                'experience': form.cleaned_data.get('experience'),
                'years_of_experience': form.cleaned_data.get('years_of_experience'),
                'team_members': form.cleaned_data.get('team_members', []),
                'payment_amount': str(event.price),
                'payment_mode': form.cleaned_data.get('payment_mode'),
                'other_payment_mode': form.cleaned_data.get('other_payment_mode'),
                'upi_id': form.cleaned_data.get('upi_id'),
                'payment_completed': event.price <= 0 or bool(form.cleaned_data.get('upi_id')),
            }

            member = EventMember.objects.create(
                event=event,
                user=request.user,
                status='approved' if registration_data['payment_completed'] else 'pending',
                registration_data=registration_data,
            )
            if event.price > 0 and request.user.email:
                payment_mode_label = form.cleaned_data.get('payment_mode')
                if payment_mode_label == 'other':
                    payment_mode_label = form.cleaned_data.get('other_payment_mode') or 'Other'
                receipt_message = (
                    f"Hello {request.user.get_full_name() or request.user.username},\n\n"
                    f"Your registration for {event.title} is confirmed.\n"
                    f"Payment amount: ₹{event.price}\n"
                    f"Payment mode: {payment_mode_label}\n"
                    f"UPI ID: {form.cleaned_data.get('upi_id') or '-'}\n\n"
                    f"Thank you for registering."
                )
                send_mail(
                    subject=f"Payment receipt for {event.title}",
                    message=receipt_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[request.user.email],
                    fail_silently=True,
                )
            welcome_message = (
                f'Welcome to {event.title}! Your registration is confirmed and we look forward to seeing you there. “Let\'s make it memorable.”'
            )
            Notification.objects.create(
                title='Registration welcome',
                message=welcome_message,
                kind='message',
                target_scope='user',
                event=event,
                created_by=event.created_by or request.user,
            )
            messages.success(request, 'Registration submitted successfully. QR code generated.' if event.price <= 0 else 'Payment captured and registration completed. Receipt sent to your email.')
            request.session['show_ticket_popup'] = member.pk
            return redirect('event_registration_qr', pk=member.pk)
    else:
        form = EventRegistrationForm(user=request.user, event=event)

    return render(request, 'events/register_event.html', {
        'event': event,
        'form': form,
        'show_payment_fields': event.price > 0,
    })


def _build_qr_image(registration_code):
    import qrcode
    qr_image = qrcode.make(registration_code)
    buffer = io.BytesIO()
    qr_image.save(buffer, format='PNG')
    return buffer.getvalue()


def _escape_pdf_text(text):
    return str(text).replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


class _PdfBuilder:
    """Minimal PDF 1.4 builder — no external dependencies."""

    W = 612   # US Letter width  (pt)
    H = 792   # US Letter height (pt)

    def __init__(self):
        self._objects = []   # list of raw bytes for each object body
        self._buf = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
        self._offsets = []

    # ── low-level helpers ─────────────────────────────────────────────────
    def _add_obj(self, body: bytes) -> int:
        """Append an indirect object; return its 1-based object number."""
        self._objects.append(body)
        return len(self._objects)

    def _stream_obj(self, content: bytes, extra_dict: str = '') -> int:
        header = f'<< /Length {len(content)}{extra_dict} >>\nstream\n'.encode()
        body = header + content + b'\nendstream'
        return self._add_obj(body)

    # ── public drawing helpers ────────────────────────────────────────────
    @staticmethod
    def rgb(r, g, b):
        return f'{r/255:.3f} {g/255:.3f} {b/255:.3f}'

    def _page_stream(self, ops: list[str]) -> bytes:
        return '\n'.join(ops).encode('latin-1', 'replace')

    # ── finalise ─────────────────────────────────────────────────────────
    def build(self, page_streams: list[bytes], xobj_ids: dict = None) -> bytes:
        """Assemble catalog, pages, fonts, xobjects and return PDF bytes."""
        xobj_ids = xobj_ids or {}

        # font objects
        f1_id = self._add_obj(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
        f2_id = self._add_obj(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>')
        f3_id = self._add_obj(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique /Encoding /WinAnsiEncoding >>')

        font_dict = (
            f'<< /F1 {f1_id} 0 R /F2 {f2_id} 0 R /F3 {f3_id} 0 R >>'
        )

        xobj_res = ''
        if xobj_ids:
            parts = ' '.join(f'/Im{k} {v} 0 R' for k, v in xobj_ids.items())
            xobj_res = f' /XObject << {parts} >>'

        page_ids = []
        for ps in page_streams:
            content_id = self._stream_obj(ps)
            page_id = self._add_obj(
                f'<< /Type /Page /Parent 0 0 R /MediaBox [0 0 {self.W} {self.H}] '
                f'/Contents {content_id} 0 R '
                f'/Resources << /Font {font_dict}{xobj_res} >> >>'.encode()
            )
            page_ids.append(page_id)

        kids_str = ' '.join(f'{pid} 0 R' for pid in page_ids)
        pages_id = self._add_obj(
            f'<< /Type /Pages /Kids [{kids_str}] /Count {len(page_ids)} >>'.encode()
        )

        # fix /Parent back-references
        for pid in page_ids:
            self._objects[pid - 1] = self._objects[pid - 1].replace(
                b'/Parent 0 0 R', f'/Parent {pages_id} 0 R'.encode()
            )

        catalog_id = self._add_obj(
            f'<< /Type /Catalog /Pages {pages_id} 0 R >>'.encode()
        )

        # serialize
        for idx, body in enumerate(self._objects, start=1):
            self._offsets.append(len(self._buf))
            self._buf.extend(f'{idx} 0 obj\n'.encode())
            self._buf.extend(body + b'\nendobj\n')

        xref_pos = len(self._buf)
        n = len(self._objects) + 1
        self._buf.extend(f'xref\n0 {n}\n'.encode())
        self._buf.extend(b'0000000000 65535 f \n')
        for off in self._offsets:
            self._buf.extend(f'{off:010d} 00000 n \n'.encode())
        self._buf.extend(
            f'trailer\n<< /Size {n} /Root {catalog_id} 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n'.encode()
        )
        return bytes(self._buf)


def _build_registration_pdf_bytes(member):
    """Build a professional A4 registration-confirmation PDF with UpEvent branding."""
    import math

    ev = member.event
    e = _escape_pdf_text

    # ── palette (r,g,b ints) ──────────────────────────────────────────────
    TEAL      = (23, 162, 184)
    DARK      = (33,  37,  41)
    WHITE     = (255, 255, 255)
    LIGHT_BG  = (240, 249, 251)
    MUTED     = (100, 116, 139)
    BORDER    = (226, 232, 240)
    SUCCESS   = (34, 197, 94)
    GOLD      = (234, 179,  8)

    def rgb(*c): return f'{c[0]/255:.3f} {c[1]/255:.3f} {c[2]/255:.3f}'

    W, H = 595, 842
    ops = []

    # ── helper lambdas ───────────────────────────────────────────────────
    def filled_rect(x, y, w, h, r, g, b):
        ops.append(f'{rgb(r,g,b)} rg')
        ops.append(f'{x:.1f} {y:.1f} {w:.1f} {h:.1f} re f')

    def stroked_rect(x, y, w, h, lw, r, g, b):
        ops.append(f'{lw} w')
        ops.append(f'{rgb(r,g,b)} RG')
        ops.append(f'{x:.1f} {y:.1f} {w:.1f} {h:.1f} re S')

    def txt(text, x, y, font, size, r=255, g=255, b=255):
        ops.append('BT')
        ops.append(f'/F{font} {size} Tf')
        ops.append(f'{rgb(r,g,b)} rg')
        ops.append(f'{x:.1f} {y:.1f} Td')
        ops.append(f'({e(str(text))}) Tj')
        ops.append('ET')

    def hline(x1, y, x2, lw, r, g, b):
        ops.append(f'{lw} w')
        ops.append(f'{rgb(r,g,b)} RG')
        ops.append(f'{x1:.1f} {y:.1f} m {x2:.1f} {y:.1f} l S')

    # ══════════════════════════════════════════════════════════════
    # 1. DIAGONAL WATERMARK
    # ══════════════════════════════════════════════════════════════
    ops.append('q')
    ops.append('1 0 0 1 0 0 cm')   # identity
    angle = math.radians(45)
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    cx, cy = W / 2, H / 2
    for offset in [-200, -100, 0, 100, 200]:
        ox = cx + offset * (-sin_a)
        oy = cy + offset * cos_a
        ops.append('BT')
        ops.append(f'/F3 52 Tf')
        ops.append(f'{rgb(23,162,184)} rg')
        ops.append(f'0.06 w')
        ops.append(f'{cos_a:.4f} {sin_a:.4f} {-sin_a:.4f} {cos_a:.4f} {ox:.1f} {oy:.1f} Tm')
        ops.append('0.92 0.92 0.92 rg')   # very light grey for watermark
        ops.append(f'(UpEvent) Tj')
        ops.append('ET')
    ops.append('Q')

    # ══════════════════════════════════════════════════════════════
    # 2. HEADER BAND
    # ══════════════════════════════════════════════════════════════
    header_h = 110
    filled_rect(0, H - header_h, W, header_h, *TEAL)

    # brand icon circle
    ops.append('q')
    ops.append(f'{rgb(*DARK)} rg')
    ops.append(f'0 0 0 RG')
    # circle approximation via 4 bezier curves
    cx2, cy2, r2 = 52, H - header_h / 2, 22
    kappa = 0.5522848
    ops.append(
        f'{cx2} {cy2+r2:.1f} m '
        f'{cx2+kappa*r2:.1f} {cy2+r2:.1f} {cx2+r2:.1f} {cy2+kappa*r2:.1f} {cx2+r2:.1f} {cy2:.1f} c '
        f'{cx2+r2:.1f} {cy2-kappa*r2:.1f} {cx2+kappa*r2:.1f} {cy2-r2:.1f} {cx2} {cy2-r2:.1f} c '
        f'{cx2-kappa*r2:.1f} {cy2-r2:.1f} {cx2-r2:.1f} {cy2-kappa*r2:.1f} {cx2-r2:.1f} {cy2:.1f} c '
        f'{cx2-r2:.1f} {cy2+kappa*r2:.1f} {cx2-kappa*r2:.1f} {cy2+r2:.1f} {cx2} {cy2+r2:.1f} c f'
    )
    ops.append('Q')

    # calendar icon text inside circle
    txt('Ev', cx2 - 8, H - header_h / 2 - 6, 2, 11, *WHITE)

    # brand title
    txt('UpEvent', 85, H - 42, 2, 22, *WHITE)
    txt('Event Registration Platform', 85, H - 60, 1, 9, 200, 240, 245)

    # right-side ticket label
    filled_rect(W - 145, H - 90, 130, 72, 23, 140, 160)
    txt('REGISTRATION', W - 138, H - 44, 2, 10, *WHITE)
    txt('CONFIRMATION', W - 138, H - 58, 1, 9, 200, 240, 245)
    hline(W - 138, H - 66, W - 25, 0.5, *WHITE)
    # registration code - truncate if too long
    reg_code = str(member.registration_code)
    if len(reg_code) > 18:
        reg_code = reg_code[:15] + '...'
    txt(reg_code, W - 138, H - 82, 2, 8, 220, 255, 255)

    # ══════════════════════════════════════════════════════════════
    # 3. STATUS PILL
    # ══════════════════════════════════════════════════════════════
    status_y = H - header_h - 30
    status_text = member.get_status_display().upper()
    s_color = SUCCESS if member.status == 'approved' else (GOLD if member.status == 'pending' else MUTED)
    filled_rect(40, status_y - 8, 110, 22, *s_color)
    txt(f'STATUS: {status_text}', 46, status_y, 2, 8, *WHITE)

    # ══════════════════════════════════════════════════════════════
    # 4. EVENT INFO CARD
    # ══════════════════════════════════════════════════════════════
    card_x, card_y, card_w, card_h = 40, H - header_h - 140, W - 80, 100
    filled_rect(card_x, card_y, card_w, card_h, *LIGHT_BG)
    stroked_rect(card_x, card_y, card_w, card_h, 0.5, *BORDER)

    event_title = ev.title if len(ev.title) <= 55 else ev.title[:52] + '...'
    txt(event_title, card_x + 12, card_y + card_h - 22, 2, 14, *DARK)
    hline(card_x + 12, card_y + card_h - 28, card_x + card_w - 12, 0.5, *TEAL)

    cat_name = ev.category.name if ev.category else 'Uncategorized'
    date_str = ev.start_time.strftime('%d %b %Y, %I:%M %p') if ev.start_time else '-'
    venue_str = str(ev.venue) if ev.venue else (ev.location or '-')
    if len(venue_str) > 40:
        venue_str = venue_str[:37] + '...'

    col2_x = card_x + card_w // 2
    txt(f'Category : {cat_name}', card_x + 12, card_y + card_h - 44, 1, 9, *MUTED)
    txt(f'Date     : {date_str}',  card_x + 12, card_y + card_h - 58, 1, 9, *MUTED)
    txt(f'Venue    : {venue_str}', card_x + 12, card_y + card_h - 72, 1, 9, *MUTED)

    # ══════════════════════════════════════════════════════════════
    # 5. ATTENDEE DETAILS TABLE
    # ══════════════════════════════════════════════════════════════
    sec_y = card_y - 20
    txt('ATTENDEE DETAILS', 40, sec_y, 2, 10, *TEAL)
    hline(40, sec_y - 4, W - 40, 1, *TEAL)

    full_name = member.user.get_full_name() or member.user.username
    email_str = member.user.email or '-'
    cat_label = member.get_attendee_category_display() if hasattr(member, 'get_attendee_category_display') else (member.attendee_category or 'General')

    rows = [
        ('Full Name',        full_name),
        ('Email',            email_str),
        ('Attendee Type',    cat_label),
        ('Joined On',        member.joined_at.strftime('%d %b %Y') if member.joined_at else '-'),
    ]
    if member.check_in_time:
        rows.append(('Checked In', member.check_in_time.strftime('%d %b %Y, %I:%M %p')))

    row_y = sec_y - 18
    for label, value in rows:
        filled_rect(40, row_y - 4, W - 80, 18, *(248, 250, 252))
        txt(label, 48, row_y + 2, 2, 9, *DARK)
        val_str = str(value)
        if len(val_str) > 52:
            val_str = val_str[:49] + '...'
        txt(val_str, 200, row_y + 2, 1, 9, *MUTED)
        hline(40, row_y - 4, W - 40, 0.3, *BORDER)
        row_y -= 20

    # ══════════════════════════════════════════════════════════════
    # 6. EXTRA REGISTRATION DATA
    # ══════════════════════════════════════════════════════════════
    registration_data = member.registration_data or {}
    if registration_data:
        row_y -= 8
        txt('REGISTRATION RESPONSES', 40, row_y, 2, 10, *TEAL)
        hline(40, row_y - 4, W - 40, 1, *TEAL)
        row_y -= 18
        for key, value in list(registration_data.items())[:10]:
            if isinstance(value, bool):
                value = 'Yes' if value else 'No'
            elif value is None:
                value = '-'
            filled_rect(40, row_y - 4, W - 80, 18, *(248, 250, 252))
            txt(key.replace('_', ' ').title(), 48, row_y + 2, 2, 9, *DARK)
            val_str = str(value)[:52]
            txt(val_str, 200, row_y + 2, 1, 9, *MUTED)
            hline(40, row_y - 4, W - 40, 0.3, *BORDER)
            row_y -= 20

    # ══════════════════════════════════════════════════════════════
    # 7. QR CODE (embedded if qrcode available, else placeholder)
    # ══════════════════════════════════════════════════════════════
    qr_x, qr_y, qr_size = W - 140, 80, 100
    qr_img_id = None
    try:
        import qrcode as _qrcode
        import struct, zlib
        qr = _qrcode.make(member.registration_code)
        qr_buf = io.BytesIO()
        qr.save(qr_buf, format='PNG')
        qr_png = qr_buf.getvalue()

        builder = _PdfBuilder.__new__(_PdfBuilder)
        builder.__init__()
        # embed as Image XObject
        # We encode the PNG as an inline image stream (base85 not needed — raw PNG via DCTDecode not applicable, use flat PNG via FlateDecode via /ASCIIHexDecode)
        import base64 as _b64
        png_b64 = _b64.b64encode(qr_png).decode()
        # Not all viewers support arbitrary PNGs inline. Use a placeholder box instead.
        raise ImportError("use placeholder")
    except Exception:
        # Draw a dashed placeholder box with "QR" label
        ops.append(f'[4 2] 0 d')
        ops.append(f'0.5 w')
        ops.append(f'{rgb(*TEAL)} RG')
        ops.append(f'{qr_x:.1f} {qr_y:.1f} {qr_size:.1f} {qr_size:.1f} re S')
        ops.append('[] 0 d')
        txt('QR', qr_x + qr_size/2 - 8, qr_y + qr_size/2 - 6, 2, 18, *TEAL)
        txt('Scan at entry', qr_x + 8, qr_y + 8, 1, 7, *MUTED)

    # QR section label
    txt('VERIFY ENTRY', qr_x + 10, qr_y + qr_size + 8, 2, 8, *TEAL)

    # ══════════════════════════════════════════════════════════════
    # 8. TERMS / NOTES STRIP
    # ══════════════════════════════════════════════════════════════
    note_y = 68
    filled_rect(40, note_y, W - 80, 30, *(255, 251, 235))
    stroked_rect(40, note_y, W - 80, 30, 0.5, *GOLD)
    txt('Important:', 48, note_y + 18, 2, 8, *DARK)
    txt('Present this ticket and a valid ID at the entry gate. Non-transferable.', 105, note_y + 18, 1, 8, *MUTED)
    txt('This is an electronically generated ticket and does not require a signature.', 48, note_y + 6, 1, 7, *MUTED)

    # ══════════════════════════════════════════════════════════════
    # 9. FOOTER
    # ══════════════════════════════════════════════════════════════
    filled_rect(0, 0, W, 52, *DARK)
    txt('UpEvent  |  Event Registration Platform', 40, 32, 2, 9, *WHITE)
    txt('This document was auto-generated and is valid without a signature.', 40, 18, 1, 7, 160, 170, 180)
    txt(f'Ticket ID: {e(str(member.registration_code))}', W - 200, 18, 1, 7, 130, 160, 170)

    # ── assemble PDF ─────────────────────────────────────────────
    b = _PdfBuilder()
    page_stream = b._page_stream(ops)
    return b.build([page_stream])


@login_required
def event_registration_qr(request, pk):
    member = get_object_or_404(EventMember, pk=pk, user=request.user)
    qr_data = None
    qr_url = None
    try:
        qr_data = base64.b64encode(_build_qr_image(member.registration_code)).decode('utf-8')
    except ImportError:
        qr_url = 'https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=' + urllib.parse.quote(member.registration_code)

    show_ticket_popup = False
    if request.session.get('show_ticket_popup') == member.pk:
        show_ticket_popup = True
        del request.session['show_ticket_popup']

    return render(request, 'events/registration_qr.html', {
        'member': member,
        'qr_data': qr_data,
        'qr_url': qr_url,
        'show_ticket_popup': show_ticket_popup,
    })


@login_required
def event_registration_qr_download(request, pk):
    member = get_object_or_404(EventMember, pk=pk, user=request.user)
    try:
        image_bytes = _build_qr_image(member.registration_code)
    except ImportError:
        image_bytes = b''

    response = HttpResponse(image_bytes, content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="registration_qr_{member.pk}.png"'
    return response


@login_required
def event_registration_pdf_download(request, pk):
    member = get_object_or_404(EventMember, pk=pk, user=request.user)

    pdf_bytes = _build_registration_pdf_bytes(member)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="registration_{member.pk}.pdf"'
    return response


@login_required
def my_activity(request):
    members = EventMember.objects.filter(user=request.user).select_related('event', 'event__category').order_by('-joined_at')
    try:
        import qrcode
        qrcode_available = True
    except ImportError:
        qrcode_available = False

    grouped_items = {}
    for member in members:
        category_name = member.event.category.name if member.event.category else 'Uncategorized'
        if category_name not in grouped_items:
            grouped_items[category_name] = []

        if qrcode_available:
            qr_data = base64.b64encode(_build_qr_image(member.registration_code)).decode('utf-8')
            qr_url = None
        else:
            qr_data = None
            qr_url = 'https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=' + urllib.parse.quote(member.registration_code)

        grouped_items[category_name].append({
            'member': member,
            'qr_data': qr_data,
            'qr_url': qr_url,
        })

    category_sections = [
        {'category': category, 'items': grouped_items[category]}
        for category in grouped_items
    ]

    return render(request, 'events/my_activity.html', {
        'category_sections': category_sections,
        'preferred_language': request.session.get('preferred_language', 'en'),
    })


@login_required
def certificates(request):
    """Show attended events where user can download participation certificates."""
    members = EventMember.objects.filter(
        user=request.user,
        status__in=['approved', 'attended']
    ).select_related('event', 'event__category').order_by('-joined_at')
    return render(request, 'events/certificates.html', {
        'members': members,
    })


@login_required
def certificate_download(request, pk):
    """Download a participation certificate PDF for an event registration."""
    member = get_object_or_404(EventMember, pk=pk, user=request.user)
    if member.status not in ('approved', 'attended'):
        messages.error(request, 'Certificate not available for this registration.')
        return redirect('certificates')
    pdf_bytes = _build_certificate_pdf_bytes(member)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="certificate_{member.pk}.pdf"'
    return response


def _build_certificate_pdf_bytes(member):
    """Build a participation certificate PDF (no external dependencies)."""
    import math
    ev = member.event
    b = _PdfBuilder()
    W, H = b.W, b.H

    ops = []

    def e(t):
        return _escape_pdf_text(t)

    def rgb(r, g, b_):
        return f'{r/255:.3f} {g/255:.3f} {b_/255:.3f}'

    def filled_rect(x, y, w, h, r, g, b_):
        ops.append(f'{rgb(r, g, b_)} rg')
        ops.append(f'{x:.1f} {y:.1f} {w:.1f} {h:.1f} re f')

    def hline(x1, y, x2, lw, r, g, b_):
        ops.append(f'{lw} w')
        ops.append(f'{rgb(r, g, b_)} RG')
        ops.append(f'{x1:.1f} {y:.1f} m {x2:.1f} {y:.1f} l S')

    def txt(text, x, y, font, size, r=0, g=0, b_=0):
        ops.append('BT')
        ops.append(f'/F{font} {size} Tf')
        ops.append(f'{rgb(r, g, b_)} rg')
        ops.append(f'{x:.1f} {y:.1f} Td')
        ops.append(f'({e(str(text))}) Tj')
        ops.append('ET')

    TEAL = (23, 162, 184)
    GOLD = (212, 175, 55)
    DARK = (30, 41, 59)
    MUTED = (100, 116, 139)
    WHITE = (255, 255, 255)
    LIGHT = (248, 250, 252)

    # Background
    filled_rect(0, 0, W, H, *LIGHT)

    # Top border band
    filled_rect(0, H - 16, W, 16, *TEAL)
    # Bottom border band
    filled_rect(0, 0, W, 16, *TEAL)
    # Left border
    ops.append(f'{rgb(*TEAL)} rg')
    ops.append(f'0 0 16 {H} re f')
    # Right border
    ops.append(f'16 0 {W - 32:.1f} {H} re')
    ops.append(f'{rgb(*LIGHT)} rg')
    ops.append(f'16 16 {W - 32:.1f} {H - 32:.1f} re f')
    # Actual right bar
    ops.append(f'{rgb(*TEAL)} rg')
    ops.append(f'{W - 16:.1f} 0 16 {H} re f')

    # Inner decorative frame
    ops.append(f'2 w')
    ops.append(f'{rgb(*GOLD)} RG')
    margin = 36
    ops.append(f'{margin:.1f} {margin:.1f} {W - 2*margin:.1f} {H - 2*margin:.1f} re S')

    # Eventon brand mark and name
    filled_rect(W / 2 - 28, H - 90, 20, 20, *TEAL)
    ops.append(f'{rgb(*WHITE)} RG')
    ops.append('2 w')
    ops.append(f'{W / 2 - 24:.1f} {H - 84:.1f} m {W / 2 - 20:.1f} {H - 80:.1f} l {W / 2 - 12:.1f} {H - 88:.1f} l S')
    txt('Eventon', W / 2 - 4, H - 84, 2, 13, *DARK)

    # Title
    txt('CERTIFICATE', W / 2 - 88, H - 125, 2, 34, *TEAL)
    txt('OF PARTICIPATION', W / 2 - 80, H - 153, 1, 16, *MUTED)

    # Decorative line under title
    hline(margin + 40, H - 167, W - margin - 40, 1.5, *GOLD)

    # "This is to certify that"
    txt('This is to certify that', W / 2 - 72, H - 205, 1, 12, *MUTED)

    # Name
    full_name = ' '.join(part for part in [member.user.first_name, member.user.last_name] if part).strip()
    full_name = full_name or member.user.username
    name_x = W / 2 - len(full_name) * 6
    if name_x < margin + 40:
        name_x = margin + 40
    txt(full_name, name_x, H - 245, 2, 24, *DARK)
    hline(margin + 40, H - 253, W - margin - 40, 0.8, *GOLD)

    # "has successfully participated in"
    txt('has successfully participated in', W / 2 - 112, H - 283, 1, 12, *MUTED)

    # Event title
    event_title = ev.title if len(ev.title) <= 60 else ev.title[:57] + '...'
    et_x = W / 2 - len(event_title) * 4
    if et_x < margin + 40:
        et_x = margin + 40
    txt(event_title, et_x, H - 320, 2, 18, *TEAL)
    hline(margin + 40, H - 329, W - margin - 40, 0.8, *MUTED)

    # Date & venue
    date_str = ev.start_time.strftime('%d %B %Y') if ev.start_time else '-'
    venue_str = str(ev.venue) if ev.venue else (ev.location or '-')
    if len(venue_str) > 45:
        venue_str = venue_str[:42] + '...'

    txt(f'Held on  {date_str}', W / 2 - 80, H - 363, 1, 11, *MUTED)
    txt(f'Venue    {venue_str}', W / 2 - 80, H - 381, 1, 11, *MUTED)

    # Category
    cat_name = ev.category.name if ev.category else 'General'
    txt(f'Category  {cat_name}', W / 2 - 80, H - 399, 1, 11, *MUTED)

    # Registration code
    hline(margin + 40, H - 435, W - margin - 40, 0.5, *MUTED)
    txt(f'Registration Code : {member.registration_code}', margin + 50, H - 453, 1, 9, *MUTED)
    issued_str = member.joined_at.strftime('%d %B %Y') if member.joined_at else '-'
    txt(f'Issued on : {issued_str}', W - 220, H - 453, 1, 9, *MUTED)

    # Signature area
    sig_y = H - 570
    hline(margin + 50, sig_y, margin + 180, 1, *DARK)
    txt('Authorized Signatory', margin + 52, sig_y - 14, 1, 9, *MUTED)

    hline(W - 230, sig_y, W - margin - 50, 1, *DARK)
    txt('Event Coordinator', W - 228, sig_y - 14, 1, 9, *MUTED)

    # Footer
    txt('Eventon - Event Registration Platform', W / 2 - 110, margin + 22, 1, 9, *MUTED)

    page_stream = b._page_stream(ops)
    return b.build([page_stream])


@admin_required
def edit_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    form  = EventForm(request.POST or None, request.FILES or None, instance=event)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Event updated successfully.')
        return redirect('event_list')
    return render(request, 'events/edit_event.html', {'form': form, 'event': event})


@admin_required
def delete_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        event.delete()
        messages.success(request, 'Event deleted.')
        return redirect('event_list')
    return render(request, 'events/delete_event.html', {'event': event})


# ══════════════════════════════════════════════
#  MEMBERS / STATUS
# ══════════════════════════════════════════════
@admin_required
def add_event_member(request):
    form = EventMemberForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        member, created = EventMember.objects.get_or_create(
            event=form.cleaned_data['event'],
            user=form.cleaned_data['user'],
            defaults={'status': form.cleaned_data['status']},
        )
        if created:
            messages.success(request, 'Member added to event.')
        else:
            messages.warning(request, 'User is already a member of this event.')
        return redirect('join_event_list')
    return render(request, 'events/add_event_member.html', {'form': form})


@admin_required
def remove_event_member(request, pk):
    member = get_object_or_404(EventMember, pk=pk)
    if request.method == 'POST':
        member.delete()
        messages.success(request, 'Member removed.')
        return redirect('join_event_list')
    return render(request, 'events/remove_event_member.html', {'member': member})


@login_required
def join_event_list(request):
    members = EventMember.objects.select_related('event', 'user').all()
    return render(request, 'events/join_event_list.html', {'members': members})


@admin_required
def update_event_status(request, pk):
    member = get_object_or_404(EventMember, pk=pk)
    form   = UpdateMemberStatusForm(request.POST or None, instance=member)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Status updated.')
        return redirect('join_event_list')
    return render(request, 'events/update_event_status.html', {'form': form, 'member': member})


# ══════════════════════════════════════════════
#  ATTENDANCE / MARKS
# ══════════════════════════════════════════════
@admin_required
def absense_user_list(request):
    """Users marked as absent across all events."""
    absent_marks = UserMark.objects.filter(is_absent=True).select_related('event', 'user')
    registered_members = EventMember.objects.select_related('event', 'user').order_by('event__title', 'user__first_name')
    return render(request, 'events/absense_user_list.html', {
        'absent_marks': absent_marks,
        'registered_members': registered_members,
    })


@admin_required
def complete_event_list(request):
    """All completed events."""
    events = Event.objects.filter(status='completed').select_related('category')
    return render(request, 'events/complete_event_list.html', {'events': events})


@admin_required
def complete_event_user_list(request, pk):
    """Members of a specific completed event."""
    event   = get_object_or_404(Event, pk=pk, status='completed')
    members = EventMember.objects.filter(event=event).select_related('user')
    return render(request, 'events/complete_event_user_list.html', {
        'event': event, 'members': members
    })


@admin_required
def create_user_mark(request):
    form = UserMarkForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        mark, created = UserMark.objects.update_or_create(
            event=form.cleaned_data['event'],
            user=form.cleaned_data['user'],
            defaults={
                'marks':     form.cleaned_data['marks'],
                'is_absent': form.cleaned_data['is_absent'],
                'notes':     form.cleaned_data['notes'],
            },
        )
        action = 'created' if created else 'updated'
        messages.success(request, f'Mark {action} successfully.')
        return redirect('user_mark_list')
    return render(request, 'events/create_user_mark.html', {'form': form})


@login_required
def user_mark_list(request):
    marks = UserMark.objects.select_related('event', 'user').all()
    registered_members = EventMember.objects.select_related('event', 'user').order_by('event__title', 'user__first_name')
    return render(request, 'events/user_mark_list.html', {
        'marks': marks,
        'registered_members': registered_members,
    })


# ══════════════════════════════════════════════
#  WISHLIST
# ══════════════════════════════════════════════
@login_required
def event_user_wish_list(request):
    wishes = EventWish.objects.select_related('event', 'user').all()
    return render(request, 'events/event_user_wish_list.html', {'wishes': wishes})


@login_required
def add_event_user_wish(request):
    form = EventWishForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        event = form.cleaned_data['event']
        user  = form.cleaned_data['user']
        # Pull current registration status
        member = EventMember.objects.filter(event=event, user=user).first()
        wish, created = EventWish.objects.get_or_create(
            event=event,
            user=user,
            defaults={
                'event_user_status': member.status if member else None,
            },
        )
        if created:
            messages.success(request, 'Event added to wishlist.')
        else:
            # Update status snapshot
            wish.event_user_status = member.status if member else None
            wish.save()
            messages.info(request, 'Wishlist entry already exists; status snapshot refreshed.')
        return redirect('event_user_wish_list')
    return render(request, 'events/add_event_user_wish.html', {'form': form})


@admin_required
def remove_event_user_wish(request, pk):
    wish = get_object_or_404(EventWish, pk=pk)
    if request.method == 'POST':
        wish.delete()
        messages.success(request, 'Removed from wishlist.')
        return redirect('event_user_wish_list')
    return render(request, 'events/remove_event_user_wish.html', {'wish': wish})


# ══════════════════════════════════════════════
#  VENUE MANAGEMENT
# ══════════════════════════════════════════════
@admin_required
def venue_list(request):
    venues = Venue.objects.all()
    return render(request, 'events/venue_list.html', {'venues': venues})


@admin_required
def venue_create(request):
    form = VenueForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Venue created successfully.')
        return redirect('venue_list')
    return render(request, 'events/venue_form.html', {'form': form, 'title': 'Add Venue'})


@admin_required
def venue_edit(request, pk):
    venue = get_object_or_404(Venue, pk=pk)
    form = VenueForm(request.POST or None, instance=venue)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Venue updated.')
        return redirect('venue_list')
    return render(request, 'events/venue_form.html', {'form': form, 'title': 'Edit Venue', 'venue': venue})


@admin_required
def venue_delete(request, pk):
    venue = get_object_or_404(Venue, pk=pk)
    if request.method == 'POST':
        venue.delete()
        messages.success(request, 'Venue deleted.')
        return redirect('venue_list')
    return render(request, 'events/venue_confirm_delete.html', {'venue': venue})


# ── Venue Bookings ─────────────────────────────
@admin_required
def venue_booking_list(request):
    bookings = VenueBooking.objects.select_related('venue', 'event').all()
    return render(request, 'events/venue_booking_list.html', {'bookings': bookings})


@admin_required
def venue_booking_create(request):
    form = VenueBookingForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        booking = form.save(commit=False)
        booking.booked_by = request.user
        if booking.has_conflict():
            messages.error(request, 'Venue booking conflicts with an existing confirmed booking.')
        else:
            booking.save()
            messages.success(request, 'Venue booking created.')
            return redirect('venue_booking_list')
    return render(request, 'events/venue_booking_form.html', {'form': form, 'title': 'Book Venue'})


@admin_required
def venue_booking_confirm(request, pk):
    booking = get_object_or_404(VenueBooking, pk=pk)
    if booking.has_conflict():
        messages.error(request, 'Cannot confirm: schedule conflict detected.')
    else:
        old_status = booking.status
        booking.status = 'confirmed'
        booking.save()
        messages.success(request, 'Booking confirmed.')
    return redirect('venue_booking_list')


@admin_required
def venue_booking_cancel(request, pk):
    booking = get_object_or_404(VenueBooking, pk=pk)
    booking.status = 'cancelled'
    booking.save()
    messages.success(request, 'Booking cancelled.')
    return redirect('venue_booking_list')


# ══════════════════════════════════════════════
#  RESOURCE MANAGEMENT
# ══════════════════════════════════════════════
@admin_required
def resource_list(request):
    resources = Resource.objects.all()
    return render(request, 'events/resource_list.html', {'resources': resources})


@admin_required
def resource_create(request):
    form = ResourceForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Resource created.')
        return redirect('resource_list')
    return render(request, 'events/resource_form.html', {'form': form, 'title': 'Add Resource'})


@admin_required
def resource_edit(request, pk):
    resource = get_object_or_404(Resource, pk=pk)
    form = ResourceForm(request.POST or None, instance=resource)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Resource updated.')
        return redirect('resource_list')
    return render(request, 'events/resource_form.html', {'form': form, 'title': 'Edit Resource', 'resource': resource})


@admin_required
def resource_delete(request, pk):
    resource = get_object_or_404(Resource, pk=pk)
    if request.method == 'POST':
        resource.delete()
        messages.success(request, 'Resource deleted.')
        return redirect('resource_list')
    return render(request, 'events/resource_confirm_delete.html', {'resource': resource})


@admin_required
def resource_allocation_list(request):
    allocations = ResourceAllocation.objects.select_related('resource', 'event').all()
    return render(request, 'events/resource_allocation_list.html', {'allocations': allocations})


@admin_required
def resource_allocation_create(request):
    form = ResourceAllocationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        allocation = form.save(commit=False)
        allocation.allocated_by = request.user
        allocation.status = 'allocated'
        allocation.save()
        messages.success(request, 'Resource allocated.')
        return redirect('resource_allocation_list')
    return render(request, 'events/resource_allocation_form.html', {'form': form, 'title': 'Allocate Resource'})


@admin_required
def resource_allocation_update(request, pk):
    allocation = get_object_or_404(ResourceAllocation, pk=pk)
    new_status = request.POST.get('status')
    if new_status in dict(ResourceAllocation.STATUS_CHOICES):
        allocation.status = new_status
        allocation.save()
        messages.success(request, f'Allocation status updated to {new_status}.')
    return redirect('resource_allocation_list')


# ══════════════════════════════════════════════
#  VENDOR MANAGEMENT
# ══════════════════════════════════════════════
@admin_required
def vendor_list(request):
    vendors = Vendor.objects.all()
    return render(request, 'events/vendor_list.html', {'vendors': vendors})


@admin_required
def vendor_create(request):
    form = VendorForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Vendor onboarded successfully.')
        return redirect('vendor_list')
    return render(request, 'events/vendor_form.html', {'form': form, 'title': 'Add Vendor'})


@admin_required
def vendor_edit(request, pk):
    vendor = get_object_or_404(Vendor, pk=pk)
    form = VendorForm(request.POST or None, instance=vendor)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Vendor updated.')
        return redirect('vendor_list')
    return render(request, 'events/vendor_form.html', {'form': form, 'title': 'Edit Vendor', 'vendor': vendor})


@admin_required
def vendor_delete(request, pk):
    vendor = get_object_or_404(Vendor, pk=pk)
    if request.method == 'POST':
        vendor.delete()
        messages.success(request, 'Vendor removed.')
        return redirect('vendor_list')
    return render(request, 'events/vendor_confirm_delete.html', {'vendor': vendor})


@admin_required
def vendor_assignment_list(request):
    assignments = VendorAssignment.objects.select_related('vendor', 'event').all()
    return render(request, 'events/vendor_assignment_list.html', {'assignments': assignments})


@admin_required
def vendor_assignment_create(request):
    form = VendorAssignmentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        assignment = form.save(commit=False)
        assignment.assigned_by = request.user
        assignment.status = 'active'
        assignment.save()
        messages.success(request, 'Vendor assigned to event.')
        return redirect('vendor_assignment_list')
    return render(request, 'events/vendor_assignment_form.html', {'form': form, 'title': 'Assign Vendor'})


@admin_required
def vendor_assignment_update_status(request, pk):
    assignment = get_object_or_404(VendorAssignment, pk=pk)
    new_status = request.POST.get('status')
    quality_score = request.POST.get('quality_score')
    if new_status in dict(VendorAssignment.STATUS_CHOICES):
        assignment.status = new_status
        if quality_score:
            try:
                assignment.quality_score = float(quality_score)
            except ValueError:
                pass
        assignment.save()
        messages.success(request, f'Assignment updated.')
    return redirect('vendor_assignment_list')


# ══════════════════════════════════════════════
#  SPONSOR MANAGEMENT
# ══════════════════════════════════════════════
@admin_required
def sponsor_list(request):
    sponsors = Sponsor.objects.all()
    return render(request, 'events/sponsor_list.html', {'sponsors': sponsors})


@admin_required
def sponsor_create(request):
    form = SponsorForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Sponsor added.')
        return redirect('sponsor_list')
    return render(request, 'events/sponsor_form.html', {'form': form, 'title': 'Add Sponsor'})


@admin_required
def sponsor_edit(request, pk):
    sponsor = get_object_or_404(Sponsor, pk=pk)
    form = SponsorForm(request.POST or None, request.FILES or None, instance=sponsor)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Sponsor updated.')
        return redirect('sponsor_list')
    return render(request, 'events/sponsor_form.html', {'form': form, 'title': 'Edit Sponsor', 'sponsor': sponsor})


@admin_required
def sponsor_delete(request, pk):
    sponsor = get_object_or_404(Sponsor, pk=pk)
    if request.method == 'POST':
        sponsor.delete()
        messages.success(request, 'Sponsor removed.')
        return redirect('sponsor_list')
    return render(request, 'events/sponsor_confirm_delete.html', {'sponsor': sponsor})


# ══════════════════════════════════════════════
#  BUDGET MANAGEMENT
# ══════════════════════════════════════════════
@admin_required
def budget_list(request):
    event_pk = request.GET.get('event')
    budget_items = BudgetItem.objects.select_related('event', 'vendor', 'created_by').all()
    selected_event = None
    if event_pk:
        budget_items = budget_items.filter(event__pk=event_pk)
        selected_event = get_object_or_404(Event, pk=event_pk)

    events = Event.objects.all()
    # Summary stats
    from django.db.models import Sum
    total_projected = budget_items.aggregate(t=Sum('projected_amount'))['t'] or 0
    total_actual = budget_items.aggregate(t=Sum('actual_amount'))['t'] or 0

    return render(request, 'events/budget_list.html', {
        'budget_items': budget_items,
        'events': events,
        'selected_event': selected_event,
        'total_projected': total_projected,
        'total_actual': total_actual,
    })


@admin_required
def budget_item_create(request):
    form = BudgetItemForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.created_by = request.user
        item.save()
        # Auto-create approval request for high-value items
        if item.projected_amount > 10000:
            ApprovalRequest.objects.create(
                request_type='budget_item',
                title=f'Budget approval: {item.description}',
                description=f'Projected: ₹{item.projected_amount}',
                event=item.event,
                budget_item=item,
                requested_by=request.user,
            )
            messages.info(request, 'High-value item: approval request created.')
        messages.success(request, 'Budget item added.')
        return redirect('budget_list')
    return render(request, 'events/budget_item_form.html', {'form': form, 'title': 'Add Budget Item'})


@admin_required
def budget_item_edit(request, pk):
    item = get_object_or_404(BudgetItem, pk=pk)
    form = BudgetItemForm(request.POST or None, instance=item)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Budget item updated.')
        return redirect('budget_list')
    return render(request, 'events/budget_item_form.html', {'form': form, 'title': 'Edit Budget Item', 'item': item})


@admin_required
def budget_item_delete(request, pk):
    item = get_object_or_404(BudgetItem, pk=pk)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Budget item deleted.')
        return redirect('budget_list')
    return render(request, 'events/budget_item_confirm_delete.html', {'item': item})


@admin_required
def budget_item_approve(request, pk):
    item = get_object_or_404(BudgetItem, pk=pk)
    action = request.POST.get('action', 'approve')
    if action == 'approve':
        item.status = 'approved'
        item.approved_by = request.user
        item.save()
        messages.success(request, 'Budget item approved.')
    elif action == 'reject':
        item.status = 'rejected'
        item.save()
        messages.warning(request, 'Budget item rejected.')
    return redirect('budget_list')


# ══════════════════════════════════════════════
#  APPROVAL WORKFLOW
# ══════════════════════════════════════════════
@login_required
def approval_list(request):
    if request.user.is_staff:
        approvals = ApprovalRequest.objects.select_related('event', 'budget_item', 'requested_by').all()
    else:
        approvals = ApprovalRequest.objects.filter(requested_by=request.user).select_related('event', 'budget_item')
    return render(request, 'events/approval_list.html', {'approvals': approvals})


@login_required
def approval_create(request):
    form = ApprovalRequestForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        req = form.save(commit=False)
        req.requested_by = request.user
        req.save()
        messages.success(request, 'Approval request submitted.')
        return redirect('approval_list')
    return render(request, 'events/approval_form.html', {'form': form})


@admin_required
def approval_review(request, pk):
    approval = get_object_or_404(ApprovalRequest, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        reviewer_notes = request.POST.get('reviewer_notes', '')
        approval.reviewed_by = request.user
        approval.reviewer_notes = reviewer_notes
        approval.reviewed_at = timezone.now()
        if action == 'approve':
            approval.status = 'approved'
            # If it's an event publish request, advance event to live
            if approval.request_type == 'event_publish' and approval.event:
                old_status = approval.event.status
                approval.event.status = 'live'
                approval.event.save()
                EventLifecycleLog.objects.create(
                    event=approval.event,
                    from_status=old_status,
                    to_status='live',
                    changed_by=request.user,
                    notes=f'Approved via workflow: {reviewer_notes}',
                )
            # If it's a budget item approval
            if approval.request_type == 'budget_item' and approval.budget_item:
                approval.budget_item.status = 'approved'
                approval.budget_item.approved_by = request.user
                approval.budget_item.save()
            messages.success(request, 'Approved successfully.')
        elif action == 'reject':
            approval.status = 'rejected'
            messages.warning(request, 'Rejected.')
        approval.save()
    return redirect('approval_list')


# ══════════════════════════════════════════════
#  EVENT LIFECYCLE
# ══════════════════════════════════════════════
@admin_required
def event_lifecycle_log(request, pk):
    event = get_object_or_404(Event, pk=pk)
    logs = EventLifecycleLog.objects.filter(event=event).select_related('changed_by')
    return render(request, 'events/event_lifecycle_log.html', {'event': event, 'logs': logs})


@admin_required
def event_advance_status(request, pk):
    """Advance event lifecycle stage with validation."""
    event = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        valid_choices = [s[0] for s in Event.STATUS_CHOICES]
        if new_status in valid_choices:
            old_status = event.status
            event.status = new_status
            event.save()
            EventLifecycleLog.objects.create(
                event=event,
                from_status=old_status,
                to_status=new_status,
                changed_by=request.user,
                notes=notes,
            )
            messages.success(request, f'Event status updated to {event.get_status_display()}.')
        else:
            messages.error(request, 'Invalid status.')
    return redirect('event_detail', pk=pk)


# ══════════════════════════════════════════════
#  ATTENDEE CHECK-IN
# ══════════════════════════════════════════════
@admin_required
def attendee_checkin(request, pk):
    """Mark an event member as checked in."""
    member = get_object_or_404(EventMember, pk=pk)
    if member.status not in ('attended',):
        member.status = 'attended'
        member.check_in_time = timezone.now()
        member.save()
        messages.success(request, f'{member.user.username} checked in.')
    else:
        messages.info(request, 'Already checked in.')
    return redirect('join_event_list')


@admin_required
def attendee_category_update(request, pk):
    member = get_object_or_404(EventMember, pk=pk)
    form = UpdateMemberAttendeeCategoryForm(request.POST or None, instance=member)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Attendee category updated.')
        return redirect('join_event_list')
    return render(request, 'events/attendee_category_form.html', {'form': form, 'member': member})


# ══════════════════════════════════════════════
#  ANALYTICS DASHBOARD
# ══════════════════════════════════════════════
@admin_required
def analytics_dashboard(request):
    from django.db.models import Sum, Avg
    now = timezone.now()

    # Event stats by status
    event_status_data = {}
    for status, label in Event.STATUS_CHOICES:
        event_status_data[label] = Event.objects.filter(status=status).count()

    # Attendee category breakdown across all events
    attendee_cats = {}
    for cat, label in EventMember.ATTENDEE_CATEGORY_CHOICES:
        attendee_cats[label] = EventMember.objects.filter(attendee_category=cat).count()

    # Budget summary per event (top 10 by budget)
    budget_events = (
        Event.objects.annotate(
            total_proj=Sum('budget_items__projected_amount'),
            total_act=Sum('budget_items__actual_amount'),
        ).filter(total_proj__isnull=False).order_by('-total_proj')[:10]
    )

    # Vendor performance
    vendor_perf = Vendor.objects.filter(performance_rating__gt=0).order_by('-performance_rating')[:10]

    # Registration trends (last 12 months: monthly count)
    import calendar
    from django.utils.timezone import make_aware
    from datetime import date

    monthly_registrations = []
    for i in range(11, -1, -1):
        month = (now.month - i - 1) % 12 + 1
        year = now.year - ((i - now.month + 1) // 12)
        label = f"{calendar.month_abbr[month]} {year}"
        count = EventMember.objects.filter(
            joined_at__year=year,
            joined_at__month=month,
        ).count()
        monthly_registrations.append({'label': label, 'count': count})

    # Budget category distribution
    budget_by_cat = {}
    for cat, label in BudgetItem.CATEGORY_CHOICES:
        total = BudgetItem.objects.filter(category=cat).aggregate(t=Sum('actual_amount'))['t'] or 0
        if total > 0:
            budget_by_cat[label] = float(total)

    # Overall financials
    total_budget_all = Event.objects.aggregate(t=Sum('total_budget'))['t'] or 0
    total_actual_all = BudgetItem.objects.aggregate(t=Sum('actual_amount'))['t'] or 0
    total_sponsorship_all = Sponsor.objects.aggregate(t=Sum('contribution'))['t'] or 0

    # Top events by registration
    top_events = (
        Event.objects.annotate(reg_count=Count('members'))
        .order_by('-reg_count')[:5]
    )

    # Resource utilization
    total_resources = Resource.objects.count()
    allocated_resources = Resource.objects.filter(status='allocated').count()

    # Vendor service type distribution
    vendor_service_data = {}
    for svc, label in Vendor.SERVICE_CHOICES:
        cnt = Vendor.objects.filter(service_type=svc).count()
        if cnt > 0:
            vendor_service_data[label] = cnt

    context = {
        'event_status_data': event_status_data,
        'attendee_cats': attendee_cats,
        'budget_events': budget_events,
        'vendor_perf': vendor_perf,
        'monthly_registrations': monthly_registrations,
        'budget_by_cat': budget_by_cat,
        'total_budget_all': total_budget_all,
        'total_actual_all': total_actual_all,
        'total_sponsorship_all': total_sponsorship_all,
        'top_events': top_events,
        'total_resources': total_resources,
        'allocated_resources': allocated_resources,
        'vendor_service_data': vendor_service_data,
        'total_vendors': Vendor.objects.count(),
        'active_vendors': Vendor.objects.filter(status='active').count(),
        'total_venues': Venue.objects.count(),
        'available_venues': Venue.objects.filter(status='available').count(),
        'pending_approvals': ApprovalRequest.objects.filter(status='pending').count(),
    }
    return render(request, 'events/analytics_dashboard.html', context)


# ══════════════════════════════════════════════
#  EXPORT (CSV / PDF)
# ══════════════════════════════════════════════
import csv


@admin_required
def export_attendees_csv(request, pk):
    event = get_object_or_404(Event, pk=pk)
    members = EventMember.objects.filter(event=event).select_related('user', 'user__profile')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="attendees_{event.uid}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Registration Code', 'Name', 'Email', 'Phone', 'Status', 'Attendee Category', 'Check-in Time', 'Joined At'])
    for m in members:
        profile = getattr(m.user, 'profile', None)
        writer.writerow([
            m.registration_code,
            m.user.get_full_name() or m.user.username,
            m.user.email,
            profile.phone if profile else '',
            m.get_status_display(),
            m.get_attendee_category_display(),
            m.check_in_time.strftime('%Y-%m-%d %H:%M') if m.check_in_time else '',
            m.joined_at.strftime('%Y-%m-%d %H:%M'),
        ])
    return response


@admin_required
def export_budget_csv(request, pk):
    event = get_object_or_404(Event, pk=pk)
    items = BudgetItem.objects.filter(event=event).select_related('vendor')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="budget_{event.uid}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Category', 'Description', 'Vendor', 'Projected (INR)', 'Actual (INR)', 'Status'])
    for item in items:
        writer.writerow([
            item.get_category_display(),
            item.description,
            item.vendor.name if item.vendor else '',
            str(item.projected_amount),
            str(item.actual_amount),
            item.get_status_display(),
        ])
    return response


@admin_required
def export_analytics_csv(request):
    from django.db.models import Sum
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="analytics_report.csv"'
    writer = csv.writer(response)

    writer.writerow(['Event Analytics Report', timezone.now().strftime('%Y-%m-%d')])
    writer.writerow([])
    writer.writerow(['Event Title', 'Status', 'Registrations', 'Max Attendance', 'Total Budget', 'Actual Expenses'])
    for event in Event.objects.annotate(reg_c=Count('members')).order_by('-start_time'):
        writer.writerow([
            event.title,
            event.get_status_display(),
            event.reg_c,
            event.max_attendance,
            str(event.total_budget),
            str(event.total_expenses()),
        ])
    return response


# ══════════════════════════════════════════════
#  REST API
# ══════════════════════════════════════════════
import json as _json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


def _json_response(data, status=200):
    return HttpResponse(_json.dumps(data, default=str), content_type='application/json', status=status)


def _require_api_auth(request):
    """Return (user, error_response). Accept session auth or Basic auth."""
    if request.user.is_authenticated:
        return request.user, None
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if auth.startswith('Basic '):
        import base64 as _b64
        try:
            creds = _b64.b64decode(auth[6:]).decode('utf-8')
            username, password = creds.split(':', 1)
            user = authenticate(request, username=username, password=password)
            if user:
                return user, None
        except Exception:
            pass
    return None, _json_response({'error': 'Authentication required'}, 401)


# ── API: Events ────────────────────────────────
@csrf_exempt
@require_http_methods(['GET', 'POST'])
def api_events(request):
    user, err = _require_api_auth(request)
    if err:
        return err

    if request.method == 'GET':
        status_filter = request.GET.get('status')
        event_type = request.GET.get('event_type')
        qs = Event.objects.select_related('category').all()
        if not user.is_staff:
            qs = qs.filter(status='live')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if event_type:
            qs = qs.filter(event_type=event_type)
        data = [{
            'id': e.pk,
            'uid': e.uid,
            'title': e.title,
            'category': e.category.name if e.category else None,
            'event_type': e.event_type,
            'status': e.status,
            'start_time': e.start_time,
            'end_time': e.end_time,
            'venue_name': e.venue_name,
            'price': str(e.price),
            'max_attendance': e.max_attendance,
            'registered_count': e.registered_count(),
        } for e in qs[:100]]
        return _json_response({'results': data, 'count': len(data)})

    if not user.is_staff:
        return _json_response({'error': 'Admin only'}, 403)

    try:
        payload = _json.loads(request.body)
    except Exception:
        return _json_response({'error': 'Invalid JSON'}, 400)

    required = ['uid', 'title', 'start_time', 'end_time']
    for field in required:
        if not payload.get(field):
            return _json_response({'error': f'Missing field: {field}'}, 400)

    from django.utils.dateparse import parse_datetime
    try:
        event = Event.objects.create(
            uid=payload['uid'],
            title=payload['title'],
            description=payload.get('description', ''),
            start_time=parse_datetime(payload['start_time']),
            end_time=parse_datetime(payload['end_time']),
            venue_name=payload.get('venue_name', ''),
            location=payload.get('location', ''),
            price=payload.get('price', 0),
            total_budget=payload.get('total_budget', 0),
            max_attendance=payload.get('max_attendance', 100),
            event_type=payload.get('event_type', 'others'),
            status=payload.get('status', 'draft'),
            created_by=user,
        )
        return _json_response({'id': event.pk, 'uid': event.uid, 'title': event.title}, 201)
    except Exception as e:
        return _json_response({'error': str(e)}, 400)


@csrf_exempt
@require_http_methods(['GET', 'PUT', 'PATCH', 'DELETE'])
def api_event_detail(request, pk):
    user, err = _require_api_auth(request)
    if err:
        return err

    event = get_object_or_404(Event, pk=pk)
    if not user.is_staff and event.status != 'live':
        return _json_response({'error': 'Not found'}, 404)

    if request.method == 'GET':
        data = {
            'id': event.pk,
            'uid': event.uid,
            'title': event.title,
            'description': event.description,
            'category': event.category.name if event.category else None,
            'event_type': event.event_type,
            'status': event.status,
            'start_time': event.start_time,
            'end_time': event.end_time,
            'venue_name': event.venue_name,
            'location': event.location,
            'price': str(event.price),
            'total_budget': str(event.total_budget),
            'max_attendance': event.max_attendance,
            'registered_count': event.registered_count(),
            'total_expenses': str(event.total_expenses()),
            'budget_remaining': str(event.budget_remaining()),
            'total_sponsorship': str(event.total_sponsorship()),
        }
        return _json_response(data)

    if not user.is_staff:
        return _json_response({'error': 'Admin only'}, 403)

    if request.method == 'DELETE':
        event.delete()
        return _json_response({'deleted': True})

    try:
        payload = _json.loads(request.body)
    except Exception:
        return _json_response({'error': 'Invalid JSON'}, 400)

    from django.utils.dateparse import parse_datetime
    for field in ['title', 'description', 'venue_name', 'location', 'status', 'event_type']:
        if field in payload:
            setattr(event, field, payload[field])
    for field in ['price', 'total_budget', 'max_attendance']:
        if field in payload:
            setattr(event, field, payload[field])
    for field in ['start_time', 'end_time']:
        if field in payload:
            setattr(event, field, parse_datetime(payload[field]))
    event.save()
    return _json_response({'id': event.pk, 'status': event.status})


# ── API: Attendee Registration ─────────────────
@csrf_exempt
@require_http_methods(['GET', 'POST'])
def api_registrations(request, event_pk):
    user, err = _require_api_auth(request)
    if err:
        return err

    event = get_object_or_404(Event, pk=event_pk)

    if request.method == 'GET':
        if not user.is_staff:
            return _json_response({'error': 'Admin only'}, 403)
        members = EventMember.objects.filter(event=event).select_related('user')
        data = [{
            'id': m.pk,
            'registration_code': m.registration_code,
            'user': m.user.username,
            'email': m.user.email,
            'status': m.status,
            'attendee_category': m.attendee_category,
            'check_in_time': m.check_in_time,
            'joined_at': m.joined_at,
        } for m in members]
        return _json_response({'results': data, 'count': len(data)})

    # POST: register current user or specified user (admin)
    if EventMember.objects.filter(event=event, user=user).exists():
        return _json_response({'error': 'Already registered'}, 409)
    if event.is_full():
        return _json_response({'error': 'Event is full'}, 409)

    try:
        payload = _json.loads(request.body) if request.body else {}
    except Exception:
        payload = {}

    member = EventMember.objects.create(
        event=event,
        user=user,
        status='approved' if event.price <= 0 else 'pending',
        attendee_category=payload.get('attendee_category', 'general'),
        registration_data=payload.get('registration_data'),
    )
    return _json_response({
        'id': member.pk,
        'registration_code': member.registration_code,
        'status': member.status,
    }, 201)


# ── API: Resources ─────────────────────────────
@csrf_exempt
@require_http_methods(['GET', 'POST'])
def api_resources(request):
    user, err = _require_api_auth(request)
    if err:
        return err
    if not user.is_staff:
        return _json_response({'error': 'Admin only'}, 403)

    if request.method == 'GET':
        resources = Resource.objects.all()
        rtype = request.GET.get('type')
        if rtype:
            resources = resources.filter(resource_type=rtype)
        data = [{
            'id': r.pk,
            'name': r.name,
            'type': r.resource_type,
            'quantity': r.quantity,
            'unit_cost': str(r.unit_cost),
            'status': r.status,
        } for r in resources]
        return _json_response({'results': data})

    try:
        payload = _json.loads(request.body)
    except Exception:
        return _json_response({'error': 'Invalid JSON'}, 400)

    resource = Resource.objects.create(
        name=payload.get('name', ''),
        resource_type=payload.get('resource_type', 'equipment'),
        description=payload.get('description', ''),
        quantity=payload.get('quantity', 1),
        unit_cost=payload.get('unit_cost', 0),
        status=payload.get('status', 'available'),
    )
    return _json_response({'id': resource.pk, 'name': resource.name}, 201)


# ── API: Vendors ───────────────────────────────
@csrf_exempt
@require_http_methods(['GET', 'POST'])
def api_vendors(request):
    user, err = _require_api_auth(request)
    if err:
        return err
    if not user.is_staff:
        return _json_response({'error': 'Admin only'}, 403)

    if request.method == 'GET':
        vendors = Vendor.objects.all()
        data = [{
            'id': v.pk,
            'name': v.name,
            'service_type': v.service_type,
            'status': v.status,
            'performance_rating': v.performance_rating,
        } for v in vendors]
        return _json_response({'results': data})

    try:
        payload = _json.loads(request.body)
    except Exception:
        return _json_response({'error': 'Invalid JSON'}, 400)

    vendor = Vendor.objects.create(
        name=payload.get('name', ''),
        service_type=payload.get('service_type', 'other'),
        contact_person=payload.get('contact_person', ''),
        email=payload.get('email', ''),
        phone=payload.get('phone', ''),
    )
    return _json_response({'id': vendor.pk, 'name': vendor.name}, 201)


# ── API: Budget / Financial ────────────────────
@csrf_exempt
@require_http_methods(['GET', 'POST'])
def api_budget(request, event_pk):
    user, err = _require_api_auth(request)
    if err:
        return err
    if not user.is_staff:
        return _json_response({'error': 'Admin only'}, 403)

    event = get_object_or_404(Event, pk=event_pk)

    if request.method == 'GET':
        from django.db.models import Sum
        items = BudgetItem.objects.filter(event=event)
        total_proj = items.aggregate(t=Sum('projected_amount'))['t'] or 0
        total_act = items.aggregate(t=Sum('actual_amount'))['t'] or 0
        data = {
            'event_id': event.pk,
            'event_title': event.title,
            'total_budget': str(event.total_budget),
            'total_projected': str(total_proj),
            'total_actual': str(total_act),
            'budget_remaining': str(event.budget_remaining()),
            'total_sponsorship': str(event.total_sponsorship()),
            'items': [{
                'id': i.pk,
                'category': i.category,
                'description': i.description,
                'projected': str(i.projected_amount),
                'actual': str(i.actual_amount),
                'status': i.status,
            } for i in items],
        }
        return _json_response(data)

    try:
        payload = _json.loads(request.body)
    except Exception:
        return _json_response({'error': 'Invalid JSON'}, 400)

    item = BudgetItem.objects.create(
        event=event,
        category=payload.get('category', 'miscellaneous'),
        description=payload.get('description', ''),
        projected_amount=payload.get('projected_amount', 0),
        actual_amount=payload.get('actual_amount', 0),
        created_by=user,
    )
    return _json_response({'id': item.pk, 'description': item.description}, 201)


# ── API: Venue ─────────────────────────────────
@csrf_exempt
@require_http_methods(['GET'])
def api_venues(request):
    user, err = _require_api_auth(request)
    if err:
        return err

    venues = Venue.objects.all()
    status_filter = request.GET.get('status')
    if status_filter:
        venues = venues.filter(status=status_filter)
    data = [{
        'id': v.pk,
        'name': v.name,
        'city': v.city,
        'capacity': v.capacity,
        'hourly_rate': str(v.hourly_rate),
        'status': v.status,
    } for v in venues]
    return _json_response({'results': data})


# ── API: Analytics ─────────────────────────────
@require_http_methods(['GET'])
def api_analytics(request):
    user, err = _require_api_auth(request)
    if err:
        return err
    if not user.is_staff:
        return _json_response({'error': 'Admin only'}, 403)

    from django.db.models import Sum, Avg
    data = {
        'total_events': Event.objects.count(),
        'live_events': Event.objects.filter(status='live').count(),
        'completed_events': Event.objects.filter(status='completed').count(),
        'total_registrations': EventMember.objects.count(),
        'total_venues': Venue.objects.count(),
        'total_resources': Resource.objects.count(),
        'total_vendors': Vendor.objects.count(),
        'total_sponsors': Sponsor.objects.count(),
        'total_budget': str(Event.objects.aggregate(t=Sum('total_budget'))['t'] or 0),
        'total_expenses': str(BudgetItem.objects.aggregate(t=Sum('actual_amount'))['t'] or 0),
        'total_sponsorship': str(Sponsor.objects.aggregate(t=Sum('contribution'))['t'] or 0),
        'pending_approvals': ApprovalRequest.objects.filter(status='pending').count(),
    }
    return _json_response(data)

@csrf_exempt
@login_required
def api_checkin_by_code(request):
    """POST {"code": "<registration_code>"} → mark member attended, return JSON."""
    if not request.user.is_staff:
        return _json_response({'error': 'Admin access required.'}, 403)
    if request.method != 'POST':
        return _json_response({'error': 'POST required'}, 405)
    try:
        payload = _json.loads(request.body)
    except Exception:
        return _json_response({'error': 'Invalid JSON'}, 400)
    code = (payload.get('code') or '').strip()
    if not code:
        return _json_response({'error': 'code is required'}, 400)
    try:
        member = EventMember.objects.select_related('user', 'event').get(registration_code=code)
    except EventMember.DoesNotExist:
        return _json_response({'error': 'No registration found for this QR code.'}, 404)
    if member.status == 'attended':
        return _json_response({
            'status': 'already_checked_in',
            'message': f'{member.user.get_full_name() or member.user.username} is already checked in.',
            'name': member.user.get_full_name() or member.user.username,
            'event': member.event.title,
            'check_in_time': member.check_in_time.strftime('%d %b %Y, %I:%M %p') if member.check_in_time else '',
        })
    member.status = 'attended'
    member.check_in_time = timezone.now()
    member.save()
    # Create or update UserMark — mark present (is_absent=False)
    UserMark.objects.update_or_create(
        event=member.event,
        user=member.user,
        defaults={'is_absent': False, 'notes': f'Checked in via QR at {member.check_in_time.strftime("%d %b %Y, %I:%M %p")}'},
    )
    return _json_response({
        'status': 'checked_in',
        'message': f'{member.user.get_full_name() or member.user.username} marked present!',
        'name': member.user.get_full_name() or member.user.username,
        'event': member.event.title,
        'check_in_time': member.check_in_time.strftime('%d %b %Y, %I:%M %p'),
    })


# ── API: Calendar Events ───────────────────────
@require_http_methods(['GET'])
@login_required
def api_calendar_events(request):
    """Return events for a specific date (YYYY-MM-DD). Admin sees all; user sees only their registered events."""
    from datetime import date as _date
    date_str = request.GET.get('date', '')
    try:
        from django.utils.dateparse import parse_date
        selected_date = parse_date(date_str)
        if not selected_date:
            selected_date = timezone.now().date()
    except Exception:
        selected_date = timezone.now().date()

    qs = Event.objects.filter(
        start_time__date=selected_date
    ).order_by('start_time')

    if not request.user.is_staff:
        # user sees only their registered events
        registered_event_ids = EventMember.objects.filter(user=request.user).values_list('event_id', flat=True)
        qs = qs.filter(pk__in=registered_event_ids)

    data = [{
        'id': e.pk,
        'title': e.title,
        'start_time': e.start_time.strftime('%H:%M'),
        'end_time': e.end_time.strftime('%H:%M'),
        'status': e.status,
        'venue': e.venue_name or (e.venue.name if e.venue else ''),
        'event_type': e.event_type,
        'url': f'/event-detail/{e.pk}/',
    } for e in qs]

    # Also return dates with events for the current month (for dot indicators)
    month_start = selected_date.replace(day=1)
    import calendar as _cal
    last_day = _cal.monthrange(selected_date.year, selected_date.month)[1]
    month_end = selected_date.replace(day=last_day)

    month_qs = Event.objects.filter(
        start_time__date__gte=month_start,
        start_time__date__lte=month_end,
    )
    if not request.user.is_staff:
        registered_event_ids = EventMember.objects.filter(user=request.user).values_list('event_id', flat=True)
        month_qs = month_qs.filter(pk__in=registered_event_ids)

    event_dates = list(set(month_qs.values_list('start_time__date', flat=True)))
    event_dates_str = [str(d) for d in event_dates]

    return _json_response({
        'date': str(selected_date),
        'events': data,
        'event_dates': event_dates_str,
    })


# ── API: Eventon Chatbot ───────────────────────
def _chatbot_event_reply(request, user_message, page_path=''):
    """Answer common Eventon questions using the current user's site data."""
    question = user_message.lower()
    is_admin = request.user.is_staff or getattr(getattr(request.user, 'profile', None), 'is_organizer', False)

    events = Event.objects.select_related('category', 'venue').all()
    type_match = re.search(r'/events/type/([^/]+)/', page_path or '')
    page_event_type = type_match.group(1) if type_match else ''
    page_event_type_label = dict(Event.EVENT_TYPE_CHOICES).get(page_event_type, page_event_type)
    event = events.filter(Q(title__iexact=user_message) | Q(uid__iexact=user_message)).first()
    if not event:
        event_terms = [term for term in user_message.split() if len(term) >= 2 and term.lower() not in {'event', 'the', 'for'}]
        if event_terms:
            event = events.filter(
                *[Q(title__icontains=term) | Q(uid__icontains=term) for term in event_terms]
            ).first()
    if not event and re.search(r'\b(this|current|here|above)\s+event\b|\b(event|registration)\s+(page|details)\b', question):
        page_match = re.search(r'/(?:event-detail|register-event)/(\d+)/', page_path or '')
        if page_match:
            event = events.filter(pk=page_match.group(1)).first()

    if not event and page_event_type and (
        page_event_type_label.lower() in question
        or page_event_type.replace('_', ' ') in question
        or re.search(r'\b(list|available|upcoming|show|what)\b', question)
    ):
        category_events = events.filter(event_type=page_event_type).order_by('start_time')
        if not category_events.exists():
            return f"There are no events listed under **{page_event_type_label}** right now."
        reply = f"**{page_event_type_label} events**\n"
        for category_event in category_events[:10]:
            event_date = timezone.localtime(category_event.start_time).strftime('%d %b %Y, %I:%M %p')
            reply += f"- **{category_event.title}** — {event_date} — /event-detail/{category_event.pk}/\n"
        if category_events.count() > 10:
            reply += f"Showing 10 of {category_events.count()} events."
        return reply.rstrip()

    asks_for_details = any(word in question for word in (
        'detail', 'about', 'information', 'info', 'when', 'where', 'venue',
        'speaker', 'session', 'price', 'cost', 'fee', 'schedule', 'date',
    ))
    if event and (asks_for_details or len(user_message.split()) > 1 or user_message.lower() == event.title.lower()):
        venue = event.venue.name if event.venue else event.venue_name or event.location or 'Venue to be announced'
        category = event.category.name if event.category else event.get_event_type_display()
        status = event.get_status_display()
        price = 'Free' if not event.price else f'₹{event.price}'
        reply = (
            f"**{event.title}**\n"
            f"Status: {status}\n"
            f"Date: {timezone.localtime(event.start_time).strftime('%d %b %Y, %I:%M %p')}\n"
            f"Venue: {venue}\n"
            f"Category: {category}\n"
            f"Price: {price}\n"
            f"Capacity: {event.max_attendance}\n"
        )
        if event.speaker_name:
            reply += f"Speaker: {event.speaker_name}\n"
        if event.description:
            reply += f"Description: {event.description[:280]}\n"
        reply += f"Open event details: /event-detail/{event.pk}/"
        if not is_admin and event.status == 'live':
            reply += f"\nRegister here: /register-event/{event.pk}/"
        return reply

    if is_admin and re.search(r'categor(y|ies)|category', question):
        return (
            "In admin mode, open **Create Event Category** from the sidebar or visit "
            "/create-event-category/. Enter the category name and code, choose its priority and status, "
            "optionally upload an image, then select **Save Category**."
        )
    if is_admin and re.search(r'create|add|make|publish', question) and 'event' in question:
        return (
            "In admin mode, open **Create Event** from the sidebar or visit /create-event/. "
            "Fill in the title, category, date and time, venue, capacity, price, and description. "
            "Save the event, then update its status when it is ready to publish."
        )
    if re.search(r'register|sign up|join', question):
        return (
            "To register as a user, open **Event List**, select an event, review its details, "
            "and choose **Register**. Complete payment if the event has a fee. Your confirmation and QR code "
            "are available in **My Activity**."
        )
    if re.search(r'event list|browse|find|upcoming|available', question):
        return "Users can browse available events from **Event List** or the dashboard, then open any event to view its details."
    if re.search(r'certificate|my activity|qr|check.?in', question):
        return "Registered users can open **My Activity** to view registrations, QR codes, downloads, and certificates when available."
    if re.search(r'help|what can|how', question):
        role = 'admin' if is_admin else 'user'
        return (
            f"You are using Eventon in **{role} mode**. Ask me about an event name, "
            "how to register, event details, or how to create an event/category."
        )
    return "I can only answer questions about Eventon events, event details, registration, categories, and admin workflows."


@csrf_exempt
@login_required
def api_chatbot(request):
    """Answer Eventon questions from local site data, with Gemini as an optional fallback."""
    if request.method != 'POST':
        return _json_response({'error': 'POST required'}, 405)
    try:
        payload = _json.loads(request.body)
    except Exception:
        return _json_response({'error': 'Invalid JSON'}, 400)

    user_message = (payload.get('message') or '').strip()
    if not user_message:
        return _json_response({'error': 'message is required'}, 400)

    page_path = (payload.get('page_url') or '').strip()
    local_reply = _chatbot_event_reply(request, user_message, page_path=page_path)
    if local_reply:
        return _json_response({'reply': local_reply})

    from django.conf import settings as _settings
    import urllib.request as _urllib_request
    import urllib.error as _urllib_error

    api_key = getattr(_settings, 'GEMINI_API_KEY', '')
    if not api_key:
        return _json_response({'error': 'Gemini API key not configured.'}, 503)

    system_instruction = (
        "You are Eventon Assistant, an AI chatbot for the Eventon event management platform. "
        "You ONLY answer questions related to events, event registration, event schedules, "
        "venues, categories, speakers, tickets, QR codes, attendance, certificates, "
        "event prices, organizers, and event platform features. "
        "If the user asks anything unrelated to events or the Eventon platform, politely redirect them. "
        "Keep answers concise and helpful."
    )

    # Build Gemini API request
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    body = _json.dumps({
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"{system_instruction}\n\nUser question: {user_message}"}]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 512,
        }
    }).encode('utf-8')

    req = _urllib_request.Request(url, data=body, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with _urllib_request.urlopen(req, timeout=15) as resp:
            result = _json.loads(resp.read().decode('utf-8'))
        reply = result['candidates'][0]['content']['parts'][0]['text']
        return _json_response({'reply': reply})
    except _urllib_error.HTTPError as e:
        err_body = e.read().decode('utf-8', errors='replace')
        return _json_response({'error': f'Gemini API error {e.code}: {err_body}'}, 502)
    except Exception as e:
        return _json_response({'error': str(e)}, 502)
