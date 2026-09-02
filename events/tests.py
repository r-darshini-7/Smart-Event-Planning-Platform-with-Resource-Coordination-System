from datetime import datetime, timedelta
from decimal import Decimal
import base64

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import translation, timezone

from .forms import CategoryForm, EventCreateForm, EventForm, EventRegistrationForm
from .models import Category, Event, EventAttendance, EventMember, Notification, Venue
from .translations import translate_text


class TranslationHelperTests(TestCase):
    def test_translate_text_returns_translated_value(self):
        self.assertEqual(translate_text('Login', 'hi'), 'लॉगिन')


class AuthenticationModeTests(TestCase):
    def test_gmail_login_uses_user_mode_without_mode_parameter(self):
        user = User.objects.create_user(
            username='gmail-user', email='user@gmail.com', password='pass'
        )

        response = self.client.post(reverse('login'), {
            'username': 'user@gmail.com',
            'password': 'pass',
            'mode': 'admin',
        })

        self.assertRedirects(response, reverse('dashboard'))
        user.refresh_from_db()
        self.assertFalse(user.is_staff)

    def test_organization_signup_creates_admin_account(self):
        response = self.client.post(reverse('signup'), {
            'name': 'Org Admin',
            'email': 'admin@company.in',
            'phone': '',
            'password': 'pass',
            'confirm_password': 'pass',
        })

        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(User.objects.get(email='admin@company.in').is_staff)

    def test_existing_organization_user_is_promoted_on_login(self):
        user = User.objects.create_user(
            username='existing-admin', email='existing@organization.org', password='pass'
        )

        response = self.client.post(reverse('login'), {
            'username': user.username,
            'password': 'pass',
        })

        self.assertRedirects(response, reverse('dashboard'))
        user.refresh_from_db()
        self.assertTrue(user.is_staff)

    def test_superuser_can_sign_in_as_admin_even_with_gmail_address(self):
        User.objects.create_superuser(
            username='main-admin', email='main@gmail.com', password='pass'
        )

        response = self.client.post(reverse('login'), {
            'username': 'main@gmail.com',
            'password': 'pass',
        })

        self.assertRedirects(response, reverse('dashboard'))

    def test_login_page_does_not_render_mode_selector(self):
        response = self.client.get(reverse('login'))

        self.assertNotContains(response, 'Sign in mode')
        self.assertNotContains(response, 'modeUser')
        self.assertNotContains(response, 'modeAdmin')


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
    def test_category_form_allows_new_category_without_image(self):
        form = CategoryForm()
        self.assertFalse(form.fields['image'].required)

    def test_event_form_requires_image_for_new_event(self):
        form = EventCreateForm()
        self.assertTrue(form.fields['image'].required)


class DuplicateValidationTests(TestCase):
    def setUp(self):
        self.image = SimpleUploadedFile('event.jpg', b'not-an-image', content_type='image/jpeg')
        self.category = Category.objects.create(name='Technology', code='tech')
        self.event = Event.objects.create(
            uid='event-001', title='Annual Meetup', category=self.category,
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=2),
        )

    def test_category_form_rejects_case_insensitive_duplicate_name_and_code(self):
        form = CategoryForm(data={
            'name': 'technology', 'code': 'TECH', 'priority': 1, 'status': 'active',
        }, files={'image': self.image})

        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('code', form.errors)

    def test_event_form_rejects_case_insensitive_duplicate_title_and_uid(self):
        form = EventForm(data={
            'uid': 'EVENT-001', 'title': 'annual meetup', 'category': self.category.pk,
            'mode': 'online', 'description': '', 'session_name': '', 'speaker_name': '',
            'start_time': '2030-01-01T10:00', 'end_time': '2030-01-01T12:00',
            'venue_name': '', 'location': '', 'price': '0', 'points': 0,
            'max_attendance': 100, 'job_category': 'other', 'event_type': 'others',
            'subcategory': 'others', 'status': 'live',
        }, files={'image': self.image})

        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
        self.assertIn('uid', form.errors)

    def test_custom_category_rejects_existing_category_name(self):
        form = EventCreateForm(data={
            'uid': 'event-002', 'title': 'Another Meetup', 'category_type': 'others',
            'custom_category': 'TECHNOLOGY', 'mode': 'online', 'description': '',
            'session_name': '', 'speaker_name': '', 'start_time': '2030-01-01T10:00',
            'end_time': '2030-01-01T12:00', 'venue_name': '', 'location': '',
            'price': '0', 'points': 0, 'max_attendance': 100, 'job_category': 'other',
            'event_type': 'others', 'subcategory': 'others', 'status': 'live',
        }, files={'image': self.image})

        self.assertFalse(form.is_valid())
        self.assertIn('custom_category', form.errors)


class CategoryCreationTests(TestCase):
    def test_created_category_appears_in_category_list(self):
        admin = User.objects.create_user(
            username='category-admin', password='pass', is_staff=True, is_superuser=True
        )
        self.client.force_login(admin)
        response = self.client.post(reverse('create_event_category'), {
            'name': 'Community Events', 'code': 'community', 'priority': 1,
            'status': 'active',
        })

        self.assertRedirects(response, reverse('event_category'))
        self.assertContains(self.client.get(reverse('event_category')), 'Community Events')

    def test_created_category_without_status_is_saved_as_active(self):
        admin = User.objects.create_user(
            username='category-admin-no-status', password='pass', is_staff=True, is_superuser=True
        )
        self.client.force_login(admin)

        response = self.client.post(reverse('create_event_category'), {
            'name': 'Uncategorized Events', 'code': 'uncategorized', 'priority': 1,
            'status': '',
        })

        self.assertRedirects(response, reverse('event_category'))
        category = Category.objects.get(code='uncategorized')
        self.assertEqual(category.status, 'active')
        self.assertContains(self.client.get(reverse('event_category')), 'Uncategorized Events')


class EventMapAddressTests(SimpleTestCase):
    def test_event_forms_reverse_geocode_map_selection_into_full_address(self):
        from pathlib import Path

        for template_name in ['events/create_event.html', 'events/edit_event.html']:
            with self.subTest(template_name=template_name):
                template_path = Path(__file__).parent.parent / 'templates' / template_name
                template = template_path.read_text(encoding='utf-8')
                self.assertIn("fetch('https://nominatim.openstreetmap.org/reverse?", template)
                self.assertIn("addressField.value = data.display_name", template)
                self.assertIn('updateAddress(pos.lat, pos.lng)', template)


class EventCreationTests(TestCase):
    def test_event_with_empty_optional_qr_upload_is_saved_and_listed(self):
        admin = User.objects.create_user(
            username='event-create-admin', password='pass', is_staff=True, is_superuser=True
        )
        category = Category.objects.create(name='Workshops', code='workshops')
        self.client.force_login(admin)
        image_bytes = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
        )

        post_data = {
            'uid': 'event-qr-empty', 'title': 'QR Optional Event',
            'category_type': category.name, 'mode': 'online', 'description': '',
            'session_name': '', 'speaker_name': '',
            'start_time': '2030-01-01T10:00', 'end_time': '2030-01-01T12:00',
            'venue_name': '', 'location': '', 'map_latitude': '', 'map_longitude': '',
            'price': '0', 'points': '0', 'max_attendance': '100',
            'job_category': 'other', 'status': 'live', 'event_type': 'others',
            'subcategory': 'others', 'qr_code_image': SimpleUploadedFile('qr.png', b''),
            'image': SimpleUploadedFile('event.png', image_bytes, content_type='image/png'),
        }
        response = self.client.post(reverse('create_event'), post_data)

        self.assertRedirects(response, reverse('event_list'))
        self.assertTrue(Event.objects.filter(uid='event-qr-empty').exists())
        self.assertContains(self.client.get(reverse('event_list')), 'QR Optional Event')

    def test_past_start_time_prevents_event_creation(self):
        admin = User.objects.create_user(
            username='ongoing-event-admin', password='pass', is_staff=True, is_superuser=True
        )
        self.client.force_login(admin)
        image_bytes = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
        )

        response = self.client.post(reverse('create_event'), {
            'uid': 'ongoing-event', 'title': 'Ongoing Event', 'category_type': 'others',
            'custom_category': 'Ongoing Category', 'mode': 'online', 'description': '',
            'start_time': '2026-09-01T10:00', 'end_time': '2026-09-06T10:00',
            'price': '0', 'points': '0', 'max_attendance': '100',
            'job_category': 'other', 'status': 'live', 'event_type': 'others',
            'subcategory': 'others',
            'image': SimpleUploadedFile('ongoing.png', image_bytes, content_type='image/png'),
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Event.objects.filter(uid='ongoing-event').exists())
        self.assertContains(response, 'Start date and time must be in the future.')


class RegistrationObjectIdTests(TestCase):
    def test_registration_stores_ticket_popup_id_as_string(self):
        user = User.objects.create_user(
            username='registration-user', email='registration@example.com', password='pass'
        )
        event = Event.objects.create(
            uid='registration-event', title='Registration Event', status='live',
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=2),
        )
        self.client.force_login(user)

        response = self.client.post(reverse('register_event', args=[event.pk]), {
            'first_name': 'Registration', 'last_name': 'User',
            'email': 'registration@example.com', 'role': 'other',
            'other_role': 'Guest',
        })

        member = EventMember.objects.get(event=event, user=user)
        self.assertRedirects(response, reverse('event_registration_qr', args=[member.pk]))
        self.assertEqual(self.client.session['show_ticket_popup'], str(member.pk))

    def test_new_registration_code_is_12_characters_and_contains_event_uid(self):
        event = Event.objects.create(
            uid='123', title='Numbered Event', status='live',
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=2),
        )
        member = EventMember.objects.create(event=event, user=User.objects.create_user(
            username='code-user', password='pass'
        ))

        self.assertEqual(len(member.registration_code), 12)
        self.assertTrue(member.registration_code.startswith('REG123'))

    def test_team_member_gets_own_profile_and_event_registration(self):
        user = User.objects.create_user(
            username='team-leader', email='leader@example.com', password='pass'
        )
        event = Event.objects.create(
            uid='team-event', title='Team Event', status='live',
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=2),
        )
        self.client.force_login(user)

        response = self.client.post(reverse('register_event', args=[event.pk]), {
            'first_name': 'Team', 'last_name': 'Leader',
            'email': 'leader@example.com', 'role': 'other', 'other_role': 'Guest',
            'team_member_1_first_name': 'Team',
            'team_member_1_last_name': 'Member',
            'team_member_1_email': 'member@example.com',
            'team_member_1_phone': '9999999999',
            'team_member_1_role': 'other',
            'team_member_1_other_role': 'Guest',
        })

        self.assertEqual(response.status_code, 302)
        member_user = User.objects.get(email='member@example.com')
        self.assertTrue(EventMember.objects.filter(event=event, user=member_user).exists())
        self.assertTrue(EventMember.objects.get(event=event, user=member_user).registration_code)
        self.assertEqual(member_user.profile.phone, '9999999999')


class UserChatbotTests(TestCase):
    def test_user_chatbot_returns_reply_for_browser(self):
        user = User.objects.create_user(username='chat-user', password='pass')
        self.client.force_login(user)

        response = self.client.post(
            reverse('api_chatbot'),
            data='{"message":"How do I register for an event?"}',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('reply', response.json())
        self.assertTrue(response.json()['reply'])


class QRScannerUiTests(SimpleTestCase):
    def test_scanner_waits_five_seconds_and_displays_logged_out_state(self):
        from pathlib import Path

        template = (Path(__file__).parent.parent / 'templates' / 'base.html').read_text(encoding='utf-8')
        self.assertIn("remaining=5", template)
        self.assertIn("_resumeTimer=setTimeout", template)
        self.assertIn("d.status==='checked_out'", template)
        self.assertIn('User Logged Out', template)


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


class QRCheckinTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='qr-admin', password='pass', is_staff=True, is_superuser=True
        )
        self.user = User.objects.create_user(
            username='qr-user', password='pass', email='qr@example.com'
        )
        self.other_user = User.objects.create_user(
            username='other-user', password='pass', email='other@example.com'
        )
        now = timezone.now()
        self.event = Event.objects.create(
            uid='evt-qr', title='QR Event', start_time=now - timedelta(minutes=5),
            end_time=now + timedelta(minutes=5), status='live',
        )
        self.member = EventMember.objects.create(
            event=self.event, user=self.user, status='approved', registration_code='qr-code'
        )
        self.client.force_login(self.admin)

    def scan(self):
        return self.client.post(
            reverse('api_checkin_by_code'),
            data={'code': self.member.registration_code},
            content_type='application/json',
        )

    def test_repeated_scans_toggle_attendance_and_notify_registered_user(self):
        first = self.scan()
        self.assertEqual(first.json()['status'], 'checked_in')
        self.member.refresh_from_db()
        self.assertEqual(self.member.status, 'attended')
        self.assertTrue(Notification.objects.filter(recipient=self.user, message__icontains='present').exists())

        second = self.scan()
        self.assertEqual(second.json()['status'], 'checked_out')
        self.member.refresh_from_db()
        self.assertEqual(self.member.status, 'absent')
        self.assertIsNone(self.member.check_in_time)
        self.assertTrue(Notification.objects.filter(recipient=self.user, message__icontains='absent').exists())

    def test_scan_outside_event_window_does_not_change_attendance(self):
        self.event.start_time = timezone.now() - timedelta(hours=2)
        self.event.end_time = timezone.now() - timedelta(hours=1)
        self.event.save(update_fields=['start_time', 'end_time'])

        response = self.scan()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'event_not_active')
        self.member.refresh_from_db()
        self.assertEqual(self.member.status, 'approved')
        self.assertFalse(Notification.objects.filter(event=self.event).exists())

    def test_recipient_notification_is_not_visible_to_another_user(self):
        self.scan()
        self.client.force_login(self.other_user)

        response = self.client.get(reverse('dashboard'))

        self.assertNotContains(response, 'Your attendance for QR Event')


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
        self.assertIn(b'/Subtype /Image', response.content)


class CertificateEligibilityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='certificate-user', password='pass')
        now = timezone.now()
        self.event = Event.objects.create(
            uid='certificate-event', title='Completed Workshop',
            start_time=now - timedelta(days=3), end_time=now - timedelta(days=1),
            status='completed',
        )
        self.member = EventMember.objects.create(event=self.event, user=self.user, status='attended')
        self.client.force_login(self.user)

    def test_certificate_is_available_only_after_attending_every_event_day(self):
        start_date = timezone.localtime(self.event.start_time).date()
        for offset in range(3):
            EventAttendance.objects.create(
                event_member=self.member,
                attendance_date=start_date + timedelta(days=offset),
                is_present=True,
            )

        response = self.client.get(reverse('certificates'))

        self.assertContains(response, 'Completed Workshop')

    def test_certificate_is_not_available_when_one_event_day_is_missing(self):
        start_date = timezone.localtime(self.event.start_time).date()
        EventAttendance.objects.create(
            event_member=self.member, attendance_date=start_date, is_present=True,
        )

        response = self.client.get(reverse('certificates'))

        self.assertNotContains(response, 'Completed Workshop')


class EventRegistrationFormTests(TestCase):
    def test_student_registration_requires_and_accepts_student_details(self):
        base = {
            'first_name': 'Asha', 'email': 'asha@example.com', 'role': 'student',
        }
        form = EventRegistrationForm(data=base)
        self.assertFalse(form.is_valid())
        self.assertIn('college id', ' '.join(form.non_field_errors()))

        base.update({
            'college_id': 'C-10', 'college_name': 'City College', 'domain': 'engineering',
            'course': 'bca', 'course_specialization': 'Data', 'graduating_year': '2027',
            'year_of_study': '2',
        })
        self.assertTrue(EventRegistrationForm(data=base).is_valid())

    def test_working_employee_registration_requires_employee_details(self):
        data = {
            'first_name': 'Ravi', 'email': 'ravi@example.com', 'role': 'working_professional',
            'employee_id': 'E-10', 'company_name': 'Acme', 'job_role': 'Engineer',
            'experience': 'Backend development', 'years_of_experience': '3.5',
        }
        form = EventRegistrationForm(data=data)
        self.assertTrue(form.is_valid())

    def test_team_member_details_are_collected_without_team_size(self):
        data = {
            'first_name': 'Asha', 'email': 'asha@example.com', 'role': 'other', 'other_role': 'Volunteer',
            'team_member_1_first_name': 'Ravi', 'team_member_1_email': 'ravi@example.com',
            'team_member_1_role': 'other', 'team_member_1_other_role': 'Guest',
        }
        form = EventRegistrationForm(data=data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['team_members'][0]['first_name'], 'Ravi')

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


class EventonAssistantTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='assistant-user', email='assistant@example.com', password='pass'
        )
        self.client.force_login(self.user)

    def test_assistant_answers_eventon_questions(self):
        response = self.client.post(
            reverse('api_chatbot'),
            data='{"message":"How do I register for an event?"}',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('register', response.json()['reply'].lower())

    def test_assistant_answers_attendance_questions_for_admin(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        response = self.client.post(
            reverse('api_chatbot'),
            data='{"message":"How do I mark attendance?"}',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('attendance', response.json()['reply'].lower())
        self.assertIn('qr', response.json()['reply'].lower())

    def test_assistant_answers_project_management_questions(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        response = self.client.post(
            reverse('api_chatbot'),
            data='{"message":"How do I manage event budgets?"}',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('budget', response.json()['reply'].lower())

    def test_assistant_lists_current_events_instead_of_matching_present_as_attendance(self):
        Event.objects.create(
            uid='evt-current', title='Current Workshop', status='live',
            start_time=timezone.now(), end_time=timezone.now() + timedelta(hours=1),
        )
        response = self.client.post(
            reverse('api_chatbot'),
            data='{"message":"events currently present"}',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('Current Workshop', response.json()['reply'])
        self.assertNotIn('attendance', response.json()['reply'].lower())

    def test_assistant_refuses_unrelated_questions(self):
        response = self.client.post(
            reverse('api_chatbot'),
            data='{"message":"Can you give me a study plan?"}',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('only answer questions about eventon', response.json()['reply'].lower())

    def test_assistant_provides_contact_information(self):
        response = self.client.post(
            reverse('api_chatbot'),
            data='{"message":"contact info"}',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('eventon@gmail.com', response.json()['reply'])
        self.assertIn('1234567890', response.json()['reply'])
        self.assertIn('/settings/', response.json()['reply'])

    def test_assistant_answers_sidebar_navigation_questions(self):
        questions_and_expected = [
            ('where is my profile', '/profile/'),
            ('how do I open settings', '/settings/'),
            ('where are my registered events', '/my-activity/'),
            ('where can I see certificates', '/certificates/'),
            ('where is the event list', '/event-list/'),
            ('how do I view the calendar', 'Calendar'),
        ]
        for question, expected in questions_and_expected:
            with self.subTest(question=question):
                response = self.client.post(
                    reverse('api_chatbot'),
                    data='{"message":"%s"}' % question,
                    content_type='application/json',
                )

                self.assertEqual(response.status_code, 200)
                self.assertIn(expected, response.json()['reply'])

    def test_assistant_uses_current_event_page_for_short_event_questions(self):
        event = Event.objects.create(
            uid='evt-hr', title='HR', status='live',
            start_time=timezone.now(), end_time=timezone.now() + timedelta(hours=1),
        )
        response = self.client.post(
            reverse('api_chatbot'),
            data='{"message":"hr event", "page_url":"/register-event/%s/"}' % event.pk,
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('**HR**', response.json()['reply'])

    def test_assistant_does_not_map_named_event_to_current_page(self):
        current_event = Event.objects.create(
            uid='evt-hack', title='Hack', status='live',
            start_time=timezone.now(), end_time=timezone.now() + timedelta(hours=1),
        )
        Event.objects.create(
            uid='evt-hr', title='HR', status='live',
            start_time=timezone.now(), end_time=timezone.now() + timedelta(hours=1),
        )
        response = self.client.post(
            reverse('api_chatbot'),
            data='{"message":"hr event", "page_url":"/register-event/%s/"}' % current_event.pk,
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('**HR**', response.json()['reply'])
        self.assertNotIn('**Hack**', response.json()['reply'])

    def test_assistant_uses_current_category_page_for_category_questions(self):
        Event.objects.create(
            uid='evt-seminar', title='Leadership Seminar', event_type='seminars', status='live',
            start_time=timezone.now(), end_time=timezone.now() + timedelta(hours=1),
        )
        response = self.client.post(
            reverse('api_chatbot'),
            data='{"message":"seminars", "page_url":"/events/type/seminars/"}',
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('Leadership Seminar', response.json()['reply'])


class EventCategoryTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='category-admin', email='category@example.com', password='pass'
        )
        self.client.force_login(self.admin)

    def test_category_list_renders_actions_for_mongodb_object_id(self):
        Category.objects.create(name='Seminars', code='seminars')

        response = self.client.get(reverse('event_category'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '/edit-event-category/')
        self.assertContains(response, '/delete-event-category/')


class VenueUrlTests(TestCase):
    def test_venue_list_renders_object_id_action_links(self):
        admin = User.objects.create_superuser(
            username='venue-admin', email='venue@example.com', password='pass'
        )
        Venue.objects.create(name='Main Hall', city='Bengaluru')
        self.client.force_login(admin)

        response = self.client.get(reverse('venue_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '/venues/')
        self.assertContains(response, '/edit/')


class EventUrlTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='event-admin', email='event@example.com', password='pass'
        )
        self.client.force_login(self.admin)

    def test_event_list_renders_object_id_detail_link(self):
        Event.objects.create(
            uid='evt-object-id', title='Object ID Event', status='live',
            start_time=timezone.now(), end_time=timezone.now() + timedelta(hours=1),
            created_by=self.admin,
        )

        response = self.client.get(reverse('event_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '/event-detail/')


class CalendarEventRangeTests(TestCase):
    def test_multi_day_event_is_returned_for_each_inclusive_date(self):
        admin = User.objects.create_superuser(
            username='calendar-admin', email='calendar@example.com', password='pass'
        )
        start = timezone.make_aware(datetime(2030, 1, 1, 10, 0))
        end = timezone.make_aware(datetime(2030, 1, 5, 18, 0))
        Event.objects.create(
            uid='calendar-range', title='Five Day Event', status='live',
            start_time=start, end_time=end, created_by=admin,
        )
        self.client.force_login(admin)

        for day in range(1, 6):
            with self.subTest(day=day):
                response = self.client.get(
                    reverse('api_calendar_events'),
                    {'date': f'2030-01-0{day}'},
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.json()['events']), 1)

        outside_response = self.client.get(
            reverse('api_calendar_events'), {'date': '2030-01-06'}
        )
        self.assertEqual(outside_response.status_code, 200)
        self.assertEqual(outside_response.json()['events'], [])

    def test_month_markers_include_each_date_of_multi_day_event(self):
        admin = User.objects.create_superuser(
            username='calendar-marker-admin', email='markers@example.com', password='pass'
        )
        Event.objects.create(
            uid='calendar-markers', title='Month Markers', status='live',
            start_time=timezone.make_aware(datetime(2030, 1, 1, 10, 0)),
            end_time=timezone.make_aware(datetime(2030, 1, 5, 18, 0)),
            created_by=admin,
        )
        self.client.force_login(admin)

        response = self.client.get(
            reverse('api_calendar_events'), {'date': '2030-01-03'}
        )

        self.assertEqual(response.json()['event_dates'], [
            '2030-01-01', '2030-01-02', '2030-01-03', '2030-01-04', '2030-01-05',
        ])
