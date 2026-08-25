from decimal import Decimal
import re

from django import forms
from django.contrib.auth.models import User
from django.utils import translation
from django.utils.text import slugify
from .models import Category, Event, EventMember, EventWish, UserMark, Profile
from .translations import translate_text


def prepend_blank_choice(field, label='---------'):
    if not hasattr(field, 'choices'):
        return
    if isinstance(field, forms.ModelChoiceField):
        field.empty_label = label
        field.required = False
        return

    choices = list(field.choices)
    if not choices or choices[0][0] == '':
        return
    field.choices = [('', label)] + choices


# ─────────────────────────────────────────────
#  PROFILE FORMS
class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )

    class Meta:
        model = Profile
        fields = ['image', 'first_name', 'last_name', 'father_name', 'dob', 'phone', 'organization', 'location']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'father_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Father's Name"}),
            'dob': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'organization': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'College'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Location'}),
        }
        labels = {
            'father_name': "Father's Name",
            'dob': 'Date of Birth',
            'organization': 'College',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        language = translation.get_language() or 'en'
        self.fields['first_name'].label = translate_text('First Name', language)
        self.fields['last_name'].label = translate_text('Last Name', language)
        self.fields['father_name'].label = translate_text("Father's Name", language)
        self.fields['dob'].label = translate_text('Date of Birth', language)
        self.fields['phone'].label = translate_text('Phone Number', language)
        self.fields['organization'].label = translate_text('College', language)
        self.fields['location'].label = translate_text('Location', language)
        self.fields['image'].label = translate_text('Image', language)
        self.fields['first_name'].widget.attrs['placeholder'] = translate_text('First Name', language)
        self.fields['last_name'].widget.attrs['placeholder'] = translate_text('Last Name', language)
        self.fields['father_name'].widget.attrs['placeholder'] = translate_text("Father's Name", language)
        self.fields['phone'].widget.attrs['placeholder'] = translate_text('Phone Number', language)
        self.fields['organization'].widget.attrs['placeholder'] = translate_text('College', language)
        self.fields['location'].widget.attrs['placeholder'] = translate_text('Location', language)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        profile.contact_email = user.email
        if commit:
            user.save()
            profile.save()
        return profile


# ─────────────────────────────────────────────
#  CATEGORY FORMS
# ─────────────────────────────────────────────
class CategoryForm(forms.ModelForm):
    image = forms.ImageField(required=True, widget=forms.FileInput(attrs={'class': 'form-control'}))

    class Meta:
        model  = Category
        fields = ['name', 'code', 'image', 'priority', 'status']
        widgets = {
            'name':     forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category Name'}),
            'code':     forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 001'}),
            'image':    forms.FileInput(attrs={'class': 'form-control'}),
            'priority': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'status':   forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and getattr(self.instance, 'image', None):
            self.fields['image'].required = False
        language = translation.get_language() or 'en'
        self.fields['name'].label = translate_text('Category Name', language)
        self.fields['code'].label = translate_text('Code', language)
        self.fields['priority'].label = translate_text('Priority', language)
        self.fields['status'].label = translate_text('Status', language)
        self.fields['name'].widget.attrs['placeholder'] = translate_text('Category Name', language)
        self.fields['code'].widget.attrs['placeholder'] = translate_text('e.g. 001', language)
        self.fields['status'].choices = [
            (value, translate_text(value.replace('_', ' ').title(), language))
            for value, _ in Category.STATUS_CHOICES
        ]
        prepend_blank_choice(self.fields['status'])


# ─────────────────────────────────────────────
#  EVENT FORMS
# ─────────────────────────────────────────────
class EventForm(forms.ModelForm):
    image = forms.ImageField(required=True, widget=forms.FileInput(attrs={'class': 'form-control'}))

    class Meta:
        model  = Event
        fields = [
            'uid', 'title', 'category', 'description', 'image', 'qr_code_image',
            'session_name', 'speaker_name',
            'start_time', 'end_time',
            'venue_name', 'location', 'map_latitude', 'map_longitude',
            'price', 'points', 'max_attendance',
            'job_category', 'event_type', 'subcategory', 'status',
        ]
        widgets = {
            'uid':           forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unique Event ID'}),
            'title':         forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Event Title'}),
            'category':      forms.Select(attrs={'class': 'form-select'}),
            'description':   forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'image':         forms.FileInput(attrs={'class': 'form-control'}),
            'qr_code_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'session_name':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Session Name'}),
            'speaker_name':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Speaker Name'}),
            'start_time':    forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'end_time':      forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'venue_name':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Venue Name'}),
            'location':      forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Full Address'}),
            'map_latitude':  forms.HiddenInput(),
            'map_longitude': forms.HiddenInput(),
            'price':         forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'points':        forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'max_attendance':forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'job_category':  forms.Select(attrs={'class': 'form-select'}),
            'event_type':    forms.Select(attrs={'class': 'form-select'}),
            'subcategory':   forms.Select(attrs={'class': 'form-select'}),
            'status':        forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and getattr(self.instance, 'image', None):
            self.fields['image'].required = False
        language = translation.get_language() or 'en'
        self.fields['uid'].label = translate_text('UID', language)
        self.fields['title'].label = translate_text('Event Title', language)
        if 'category' in self.fields:
            self.fields['category'].label = translate_text('Category', language)
        self.fields['description'].label = translate_text('Description', language)
        self.fields['session_name'].label = translate_text('Session Name', language)
        self.fields['speaker_name'].label = translate_text('Speaker Name', language)
        self.fields['venue_name'].label = translate_text('Venue Name', language)
        self.fields['location'].label = translate_text('Location', language)
        self.fields['price'].label = translate_text('Price', language)
        self.fields['points'].label = translate_text('Points', language)
        self.fields['max_attendance'].label = translate_text('Max Attendance', language)
        self.fields['job_category'].label = translate_text('Job Category', language)
        self.fields['event_type'].label = translate_text('Event Type', language)
        self.fields['subcategory'].label = translate_text('Subcategory', language)
        self.fields['status'].label = translate_text('Status', language)
        self.fields['image'].label = translate_text('Image', language)
        self.fields['qr_code_image'].label = translate_text('Payment QR Code', language)
        if 'category' in self.fields:
            prepend_blank_choice(self.fields['category'])
        self.fields['uid'].widget.attrs['placeholder'] = translate_text('Unique Event ID', language)
        self.fields['title'].widget.attrs['placeholder'] = translate_text('Event Title', language)
        self.fields['session_name'].widget.attrs['placeholder'] = translate_text('Session Name', language)
        self.fields['speaker_name'].widget.attrs['placeholder'] = translate_text('Speaker Name', language)
        self.fields['venue_name'].widget.attrs['placeholder'] = translate_text('Venue Name', language)
        self.fields['location'].widget.attrs['placeholder'] = translate_text('Full Address', language)
        self.fields['status'].choices = [
            (value, translate_text(value.replace('_', ' ').title(), language))
            for value, _ in Event.STATUS_CHOICES
        ]
        self.fields['job_category'].choices = [
            (value, translate_text(value.replace('_', ' ').title(), language))
            for value, _ in Event.JOB_CATEGORY_CHOICES
        ]
        self.fields['event_type'].choices = [
            (value, translate_text(label, language)) for value, label in Event.EVENT_TYPE_CHOICES
        ]
        self.fields['subcategory'].choices = [
            (value, translate_text(label, language)) for value, label in Event.SUBCATEGORY_CHOICES
        ]
        prepend_blank_choice(self.fields['status'])
        prepend_blank_choice(self.fields['job_category'])
        prepend_blank_choice(self.fields['event_type'])
        prepend_blank_choice(self.fields['subcategory'])
        # Make datetime fields use local format
        self.fields['start_time'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['end_time'].input_formats   = ['%Y-%m-%dT%H:%M']

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_time')
        end   = cleaned.get('end_time')
        if start and end and end <= start:
            raise forms.ValidationError('End time must be after start time.')
        return cleaned


class EventCreateForm(EventForm):

    category_type = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Category',
        required=True,
    )
    custom_category = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter other category'}),
        label='Other Category',
    )

    class Meta(EventForm.Meta):
        fields = [
            'uid', 'title', 'description', 'image', 'qr_code_image',
            'session_name', 'speaker_name',
            'start_time', 'end_time',
            'venue_name', 'location', 'map_latitude', 'map_longitude',
            'price', 'points', 'max_attendance',
            'job_category', 'event_type', 'subcategory', 'status',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        language = translation.get_language() or 'en'
        self.fields['category_type'].label = translate_text('Category', language)
        self.fields['custom_category'].label = translate_text('Other Category', language)
        # Build choices dynamically from all saved categories + Others fallback
        db_choices = [('', '---------')] + [
            (cat.name, cat.name) for cat in Category.objects.order_by('name')
        ] + [('others', translate_text('Others', language))]
        self.fields['category_type'].choices = db_choices
        self.fields['custom_category'].widget.attrs['placeholder'] = translate_text('Enter other category', language)

        if self.instance and getattr(self.instance, 'category', None):
            category_name = self.instance.category.name
            known_names = [name for name, _ in db_choices if name and name != 'others']
            if category_name in known_names:
                self.fields['category_type'].initial = category_name
            else:
                self.fields['category_type'].initial = 'others'
                self.fields['custom_category'].initial = category_name

    def clean(self):
        cleaned = super().clean()
        category_type = cleaned.get('category_type')
        custom_category = cleaned.get('custom_category')
        if category_type == 'others' and not custom_category:
            self.add_error('custom_category', 'Please enter a category name for Others.')
        return cleaned


# ─────────────────────────────────────────────
#  EVENT MEMBER FORMS
# ─────────────────────────────────────────────
class EventMemberForm(forms.ModelForm):
    class Meta:
        model  = EventMember
        fields = ['event', 'user', 'status']
        widgets = {
            'event':  forms.Select(attrs={'class': 'form-select'}),
            'user':   forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['event', 'user', 'status']:
            if field_name in self.fields:
                prepend_blank_choice(self.fields[field_name])


class EventRegistrationForm(forms.Form):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('working_professional', 'Working Professional'),
        ('other', 'Other'),
    ]
    DOMAIN_CHOICES = [
        ('management', 'Management'),
        ('engineering', 'Engineering'),
        ('art_science', 'Art & Science'),
        ('medicine', 'Medicine'),
        ('law', 'Law'),
    ]
    COURSE_CHOICES = [
        ('mtech_me', 'M.Tech/ME'),
        ('integrated_dual_degree', 'Integrated/Dual Degree'),
        ('bca', 'BCA'),
        ('mca', 'MCA'),
        ('phd', 'PhD'),
        ('diploma', 'Diploma'),
        ('other', 'Others'),
    ]
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('prefer_not_to_say', 'Prefer not to say'),
    ]

    first_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email',
            'readonly': 'readonly',
        })
    )
    phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'})
    )
    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Location'})
    )
    gender = forms.ChoiceField(
        required=False,
        choices=GENDER_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    role = forms.ChoiceField(
        required=True,
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    other_role = forms.CharField(
        required=False,
        label='Others',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Specify your role'})
    )
    team_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Team Name'})
    )
    college_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'College Name'})
    )
    college_id = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'College ID'})
    )
    year_of_study = forms.CharField(
        required=False,
        widget=forms.Select(choices=[('', 'Select year')] + [(str(year), str(year)) for year in range(1, 6)], attrs={'class': 'form-select'})
    )
    graduating_year = forms.IntegerField(
        required=False,
        min_value=1900,
        max_value=2200,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Graduating Year'})
    )
    domain = forms.ChoiceField(
        required=False,
        choices=DOMAIN_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    course = forms.ChoiceField(
        required=False,
        choices=COURSE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    other_course = forms.CharField(
        required=False,
        label='Others',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Specify your course'})
    )
    course_specialization = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Course Specialization'})
    )
    employee_id = forms.CharField(
        required=False,
        label='Emp ID',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Employee ID'})
    )
    experience = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Experience'})
    )
    years_of_experience = forms.DecimalField(
        required=False,
        min_value=0,
        max_digits=4,
        decimal_places=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.1', 'placeholder': 'Years of Experience'})
    )
    # Kept for compatibility with older saved registration snapshots.
    year_of_passing = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    company_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company Name'})
    )
    job_title = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Job Title'})
    )
    job_role = forms.CharField(
        required=False,
        label='Job Role',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Job Role'})
    )
    industry = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Industry'})
    )
    PAYMENT_MODE_CHOICES = [
        ('phonepe', 'PhonePe'),
        ('gpay', 'Google Pay'),
        ('paytm', 'Paytm'),
        ('other', 'Other'),
    ]
    payment_mode = forms.ChoiceField(
        required=False,
        choices=PAYMENT_MODE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    other_payment_mode = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter payment method'})
    )
    upi_id = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'UPI ID'})
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        self.event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)
        prepend_blank_choice(self.fields['gender'])
        prepend_blank_choice(self.fields['role'])
        prepend_blank_choice(self.fields['payment_mode'])
        if self.event and self.event.price and Decimal(str(self.event.price)) > Decimal('0.00'):
            self.fields['payment_mode'].required = True
            self.fields['upi_id'].required = True
        else:
            self.fields['payment_mode'].required = False
            self.fields['upi_id'].required = False
        if user is not None:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
            profile = getattr(user, 'profile', None)
            if profile:
                self.fields['phone'].initial = profile.phone
                self.fields['location'].initial = profile.location

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get('role')
        team_members = []
        member_indexes = sorted({
            int(match.group(1))
            for key in self.data
            for match in [re.match(r'team_member_(\d+)_', key)]
            if match
        })
        member_fields = [
            'first_name', 'last_name', 'email', 'phone', 'gender', 'location',
            'role', 'other_role', 'college_id', 'college_name', 'domain', 'course',
            'other_course', 'course_specialization', 'graduating_year', 'year_of_study',
            'employee_id', 'company_name', 'job_role', 'experience', 'years_of_experience',
        ]
        for index in member_indexes:
            prefix = f'team_member_{index}_'
            member = {field_name: self.data.get(f'{prefix}{field_name}', '').strip() for field_name in member_fields}
            if not member['first_name']:
                self.add_error(None, f'Team member {index} requires first name.')
            if member['email'] and '@' not in member['email']:
                self.add_error(None, f'Team member {index} requires a valid email.')
            self._validate_role_fields(member, f'Team member {index}')
            team_members.append(member)
        cleaned['team_members'] = team_members
        if self.event and self.event.price and Decimal(str(self.event.price)) > Decimal('0.00'):
            if not cleaned.get('payment_mode'):
                self.add_error('payment_mode', 'Please select a payment mode.')
            if cleaned.get('payment_mode') == 'other' and not cleaned.get('other_payment_mode'):
                self.add_error('other_payment_mode', 'Please enter the other payment method.')
            if not cleaned.get('upi_id'):
                self.add_error('upi_id', 'UPI ID is required for paid events.')
        if role == 'student':
            self._validate_role_fields(cleaned, 'Registration')
        elif role == 'working_professional':
            self._validate_role_fields(cleaned, 'Registration')
        return cleaned

    def _validate_role_fields(self, values, label):
        role = values.get('role')
        required_fields = {
            'student': ['college_id', 'college_name', 'domain', 'course', 'course_specialization', 'graduating_year', 'year_of_study'],
            'working_professional': ['employee_id', 'company_name', 'job_role', 'experience', 'years_of_experience'],
        }
        for field_name in required_fields.get(role, []):
            if not values.get(field_name):
                self.add_error(None, f'{label} requires {field_name.replace("_", " ")}.')
        if role == 'other' and not values.get('other_role'):
            self.add_error(None, f'{label} requires others.')
        if role == 'student' and values.get('course') == 'other' and not values.get('other_course'):
            self.add_error(None, f'{label} requires other course.')


class UpdateMemberStatusForm(forms.ModelForm):
    class Meta:
        model  = EventMember
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


# ─────────────────────────────────────────────
#  EVENT WISH FORMS
# ─────────────────────────────────────────────
class EventWishForm(forms.ModelForm):
    class Meta:
        model  = EventWish
        fields = ['event', 'user', 'event_user_status']
        widgets = {
            'event':             forms.Select(attrs={'class': 'form-select'}),
            'user':              forms.Select(attrs={'class': 'form-select'}),
            'event_user_status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['event', 'user', 'event_user_status']:
            if field_name in self.fields:
                prepend_blank_choice(self.fields[field_name])
        self.fields['event_user_status'].required = False


# ─────────────────────────────────────────────
#  USER MARK FORMS
# ─────────────────────────────────────────────
class UserMarkForm(forms.ModelForm):
    class Meta:
        model  = UserMark
        fields = ['event', 'user', 'marks', 'is_absent', 'notes']
        widgets = {
            'event':     forms.Select(attrs={'class': 'form-select'}),
            'user':      forms.Select(attrs={'class': 'form-select'}),
            'marks':     forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_absent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes':     forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['event', 'user']:
            if field_name in self.fields:
                prepend_blank_choice(self.fields[field_name])

# ─────────────────────────────────────────────
#  VENUE FORMS
# ─────────────────────────────────────────────
from .models import Venue, Resource, Vendor, Sponsor, VenueBooking, ResourceAllocation, VendorAssignment, BudgetItem, ApprovalRequest


class VenueForm(forms.ModelForm):
    class Meta:
        model = Venue
        fields = ['name', 'address', 'city', 'capacity', 'contact_name', 'contact_phone', 'contact_email', 'facilities', 'hourly_rate', 'status', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'facilities': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'hourly_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ['name', 'resource_type', 'description', 'quantity', 'unit_cost', 'status', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'resource_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ['name', 'service_type', 'contact_person', 'email', 'phone', 'address', 'contract_start', 'contract_end', 'contract_value', 'performance_rating', 'status', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'service_type': forms.Select(attrs={'class': 'form-select'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'contract_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'contract_end': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'contract_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'performance_rating': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '5'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class SponsorForm(forms.ModelForm):
    class Meta:
        model = Sponsor
        fields = ['name', 'tier', 'contact_person', 'email', 'phone', 'logo', 'contribution', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'tier': forms.Select(attrs={'class': 'form-select'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'contribution': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class VenueBookingForm(forms.ModelForm):
    class Meta:
        model = VenueBooking
        fields = ['venue', 'event', 'start_time', 'end_time', 'total_cost', 'notes']
        widgets = {
            'venue': forms.Select(attrs={'class': 'form-select'}),
            'event': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'total_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['start_time'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['end_time'].input_formats = ['%Y-%m-%dT%H:%M']

    def clean(self):
        cleaned = super().clean()
        venue = cleaned.get('venue')
        start = cleaned.get('start_time')
        end = cleaned.get('end_time')
        if start and end and end <= start:
            raise forms.ValidationError('End time must be after start time.')
        if venue and start and end:
            conflict = VenueBooking.objects.filter(
                venue=venue,
                status='confirmed',
                start_time__lt=end,
                end_time__gt=start,
            )
            if self.instance and self.instance.pk:
                conflict = conflict.exclude(pk=self.instance.pk)
            if conflict.exists():
                raise forms.ValidationError(f'Venue "{venue.name}" is already booked during this time slot.')
        return cleaned


class ResourceAllocationForm(forms.ModelForm):
    class Meta:
        model = ResourceAllocation
        fields = ['resource', 'event', 'quantity', 'start_time', 'end_time', 'notes']
        widgets = {
            'resource': forms.Select(attrs={'class': 'form-select'}),
            'event': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'start_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'end_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['start_time'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['end_time'].input_formats = ['%Y-%m-%dT%H:%M']


class VendorAssignmentForm(forms.ModelForm):
    class Meta:
        model = VendorAssignment
        fields = ['vendor', 'event', 'service_description', 'agreed_amount', 'delivery_deadline', 'notes']
        widgets = {
            'vendor': forms.Select(attrs={'class': 'form-select'}),
            'event': forms.Select(attrs={'class': 'form-select'}),
            'service_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'agreed_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'delivery_deadline': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['delivery_deadline'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['delivery_deadline'].required = False


class BudgetItemForm(forms.ModelForm):
    class Meta:
        model = BudgetItem
        fields = ['event', 'category', 'description', 'projected_amount', 'actual_amount', 'vendor', 'notes']
        widgets = {
            'event': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'projected_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'actual_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'vendor': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        prepend_blank_choice(self.fields['vendor'])


class ApprovalRequestForm(forms.ModelForm):
    class Meta:
        model = ApprovalRequest
        fields = ['request_type', 'title', 'description', 'event', 'budget_item']
        widgets = {
            'request_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'event': forms.Select(attrs={'class': 'form-select'}),
            'budget_item': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        prepend_blank_choice(self.fields['event'])
        prepend_blank_choice(self.fields['budget_item'])
        self.fields['event'].required = False
        self.fields['budget_item'].required = False


class UpdateMemberAttendeeCategoryForm(forms.ModelForm):
    class Meta:
        model = EventMember
        fields = ['attendee_category']
        widgets = {
            'attendee_category': forms.Select(attrs={'class': 'form-select'}),
        }
