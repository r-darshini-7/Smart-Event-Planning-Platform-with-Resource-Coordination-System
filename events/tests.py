from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import translation, timezone

from .forms import CategoryForm, EventCreateForm, EventForm, EventRegistrationForm
from .models import Category, Event, EventMember, Notification
from .translations import translate_text


class TranslationHelperTests(TestCase):
    def test_translate_text_returns_translated_value(self):
        self.assertEqual(translate_text('Login', 'hi'), 'लॉगिन')


class DashboardAnalyticsTests(TestCase):
    def test_dashboard_context_contains_registration_chart_data(self):
        admin = User.objects.create_user(username='admin', password='pass', is_staff=True, is_superuser=True)
        category = Category.objects.create(name='Tech', code='tech', priority=1, status='active')
        event = Event.objects.create(
            uid='evt-001',
            title='Launch Event',
            category=category,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=1),
            status='live',
            created_by=admin,
        )
        EventMember.objects.create(event=event, user=admin, status='approved')

        self.client.force_login(admin)
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.context['registration_chart_labels'], ['Tech'])
        self.assertEqual(response.context['registration_chart_counts'], [1])


class AdminFormRequirementTests(TestCase):
    def test_category_form_requires_image_for_new_category(self):
        form = CategoryForm()
        self.assertTrue(form.fields['image'].required)

    def test_event_form_requires_image_for_new_event(self):
        form = EventCreateForm()
        self.assertTrue(form.fields['image'].required)


class NotificationTests(TestCase):
    def test_admin_can_create_user_notification(self):
        admin = User.objects.create_user(username='notify-admin', password='pass', is_staff=True, is_superuser=True)
        self.client.force_login(admin)

        response = self.client.post(reverse('send_message'), {
            'send_message': '1',
            'title': 'Welcome update',
            'message': 'A new event is now live.',
            'target_scope': 'user',
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Notification.objects.filter(title='Welcome update').exists())
        notification = Notification.objects.get(title='Welcome update')
        self.assertEqual(notification.target_scope, 'user')


class RegistrationPdfTests(TestCase):
    def test_user_can_download_registration_pdf(self):
        user = User.objects.create_user(username='pdf-user', email='pdf@example.com', password='pass')
        category = Category.objects.create(name='Design', code='design', priority=1, status='active')
        event = Event.objects.create(
            uid='evt-pdf',
            title='Design Meetup',
            category=category,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=1),
            status='live',
        )
        member = EventMember.objects.create(
            event=event,
            user=user,
            registration_data={
                'first_name': 'Ada',
                'last_name': 'Lovelace',
                'email': 'pdf@example.com',
                'phone': '9999999999',
            },
        )

        self.client.force_login(user)
        response = self.client.get(reverse('event_registration_pdf_download', args=[member.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn(b'PDF', response.content)


class EventRegistrationFormTests(TestCase):
    def test_paid_event_registration_form_requires_payment_fields(self):
        event = Event(price=Decimal('100.00'))
        form = EventRegistrationForm(event=event)
        self.assertTrue(form.fields['payment_mode'].required)
        self.assertTrue(form.fields['upi_id'].required)

    def test_free_event_registration_form_does_not_require_payment_fields(self):
        event = Event(price=Decimal('0.00'))
        form = EventRegistrationForm(event=event)
        self.assertFalse(form.fields['payment_mode'].required)
        self.assertFalse(form.fields['upi_id'].required)

    def test_translate_text_falls_back_to_english(self):
        self.assertEqual(translate_text('Unknown String', 'hi'), 'Unknown String')

    def test_language_selector_label_is_translated(self):
        self.assertEqual(translate_text('English', 'hi'), 'अंग्रेज़ी')

    def test_event_form_status_choices_follow_active_language(self):
        translation.activate('hi')
        form = EventForm()
        self.assertEqual(form.fields['status'].choices[0], ('', '---------'))
        self.assertIn(("draft", translate_text('Draft', 'hi')), form.fields['status'].choices)

    def test_event_create_form_instantiates_without_category_field(self):
        translation.activate('en')
        form = EventCreateForm()
        self.assertIn('category_type', form.fields)
        self.assertNotIn('category', form.fields)

    def test_dropdown_fields_have_placeholder_option_first(self):
        translation.activate('en')
        event_form = EventForm()
        for field_name in ['status', 'job_category', 'event_type', 'subcategory']:
            self.assertEqual(event_form.fields[field_name].choices[0], ('', '---------'))

        registration_form = EventRegistrationForm()
        self.assertEqual(registration_form.fields['gender'].choices[0], ('', '---------'))
        self.assertEqual(registration_form.fields['role'].choices[0], ('', '---------'))
