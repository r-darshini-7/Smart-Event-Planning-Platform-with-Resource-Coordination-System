from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_save
import os


# ─────────────────────────────────────────────
#  CATEGORY
# ─────────────────────────────────────────────
class Category(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('completed', 'Completed'),
    ]

    name     = models.CharField(max_length=200, unique=True)
    code     = models.CharField(max_length=50, unique=True)
    image    = models.ImageField(upload_to='categories/', blank=True, null=True)
    priority = models.PositiveIntegerField(default=1)
    status   = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['priority', 'name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return f"{self.name} ({self.code})"

    def active_events_count(self):
        return self.events.filter(status='live').count()


# ─────────────────────────────────────────────
#  VENUE
# ─────────────────────────────────────────────
class Venue(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('booked', 'Booked'),
        ('maintenance', 'Under Maintenance'),
        ('unavailable', 'Unavailable'),
    ]

    name         = models.CharField(max_length=300)
    address      = models.TextField(blank=True)
    city         = models.CharField(max_length=100, blank=True)
    capacity     = models.PositiveIntegerField(default=0)
    contact_name = models.CharField(max_length=200, blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    contact_email = models.EmailField(blank=True)
    facilities   = models.TextField(blank=True, help_text='Comma-separated list of facilities')
    hourly_rate  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    notes        = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.city})"


# ─────────────────────────────────────────────
#  RESOURCE
# ─────────────────────────────────────────────
class Resource(models.Model):
    TYPE_CHOICES = [
        ('equipment', 'Equipment'),
        ('transport', 'Transportation'),
        ('staff', 'Staff'),
        ('technology', 'Technology'),
        ('furniture', 'Furniture'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('allocated', 'Allocated'),
        ('maintenance', 'Under Maintenance'),
        ('unavailable', 'Unavailable'),
    ]

    name          = models.CharField(max_length=300)
    resource_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='equipment')
    description   = models.TextField(blank=True)
    quantity      = models.PositiveIntegerField(default=1)
    unit_cost     = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    notes         = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['resource_type', 'name']

    def __str__(self):
        return f"{self.name} [{self.get_resource_type_display()}]"


# ─────────────────────────────────────────────
#  VENDOR
# ─────────────────────────────────────────────
class Vendor(models.Model):
    SERVICE_CHOICES = [
        ('catering', 'Catering'),
        ('logistics', 'Logistics'),
        ('equipment_rental', 'Equipment Rental'),
        ('marketing', 'Marketing'),
        ('security', 'Security'),
        ('photography', 'Photography/Videography'),
        ('it_support', 'IT Support'),
        ('decor', 'Decoration'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('blacklisted', 'Blacklisted'),
    ]

    name            = models.CharField(max_length=300)
    service_type    = models.CharField(max_length=30, choices=SERVICE_CHOICES, default='other')
    contact_person  = models.CharField(max_length=200, blank=True)
    email           = models.EmailField(blank=True)
    phone           = models.CharField(max_length=50, blank=True)
    address         = models.TextField(blank=True)
    contract_start  = models.DateField(null=True, blank=True)
    contract_end    = models.DateField(null=True, blank=True)
    contract_value  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    performance_rating = models.FloatField(default=0.0, help_text='Rating 0-5')
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    notes           = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_service_type_display()})"


# ─────────────────────────────────────────────
#  SPONSOR
# ─────────────────────────────────────────────
class Sponsor(models.Model):
    TIER_CHOICES = [
        ('platinum', 'Platinum'),
        ('gold', 'Gold'),
        ('silver', 'Silver'),
        ('bronze', 'Bronze'),
        ('partner', 'Partner'),
    ]

    name            = models.CharField(max_length=300)
    tier            = models.CharField(max_length=20, choices=TIER_CHOICES, default='bronze')
    contact_person  = models.CharField(max_length=200, blank=True)
    email           = models.EmailField(blank=True)
    phone           = models.CharField(max_length=50, blank=True)
    logo            = models.ImageField(upload_to='sponsors/', blank=True, null=True)
    contribution    = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes           = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['tier', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_tier_display()})"


# ─────────────────────────────────────────────
#  EVENT
# ─────────────────────────────────────────────
class Event(models.Model):
    MODE_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('planning', 'Planning'),
        ('approval', 'Pending Approval'),
        ('live', 'Live'),
        ('execution', 'In Execution'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    JOB_CATEGORY_CHOICES = [
        ('technical', 'Technical'),
        ('non_technical', 'Non-Technical'),
        ('management', 'Management'),
        ('research', 'Research'),
        ('other', 'Other'),
    ]

    EVENT_TYPE_CHOICES = [
        ('tech_fest', 'Tech Fest'),
        ('cultural', 'Cultural'),
        ('hackathons', 'Hackathons'),
        ('seminars', 'Seminars'),
        ('competitions', 'Competitions'),
        ('others', 'Others'),
    ]

    SUBCATEGORY_CHOICES = [
        ('internships', 'Internships'),
        ('jobs', 'Jobs'),
        ('competitions', 'Competitions'),
        ('mock_tests', 'Mock Tests'),
        ('mentorships', 'Mentorships'),
        ('courses', 'Courses'),
        ('interviews', 'Interviews'),
        ('hundred_days_to', '100 Days to'),
        ('others', 'Others'),
    ]

    # Core identifiers
    uid          = models.CharField(max_length=100, unique=True, help_text='Unique Event ID')
    title        = models.CharField(max_length=300)
    category     = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='events')
    mode         = models.CharField(max_length=10, choices=MODE_CHOICES, default='online')
    description  = models.TextField(blank=True)
    image        = models.ImageField(upload_to='events/', blank=True, null=True)
    qr_code_image = models.ImageField(upload_to='events/qr_codes/', blank=True, null=True)

    # Session / Speaker
    session_name = models.CharField(max_length=200, blank=True)
    speaker_name = models.CharField(max_length=200, blank=True)

    # Schedule
    start_time = models.DateTimeField()
    end_time   = models.DateTimeField()

    # Venue (legacy text fields kept for backward compat + new FK)
    venue       = models.ForeignKey(Venue, on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    venue_name  = models.CharField(max_length=300, blank=True)
    location    = models.TextField(blank=True, help_text='Full address')
    map_latitude = models.FloatField(blank=True, null=True, help_text='Latitude for event pin')
    map_longitude = models.FloatField(blank=True, null=True, help_text='Longitude for event pin')

    # Financials / Gamification
    price        = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_budget = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    points       = models.PositiveIntegerField(default=0, help_text='Points awarded on completion')

    # Capacity & Classification
    max_attendance = models.PositiveIntegerField(default=100)
    job_category   = models.CharField(max_length=30, choices=JOB_CATEGORY_CHOICES, default='other')
    event_type     = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES, default='others')
    subcategory    = models.CharField(max_length=30, choices=SUBCATEGORY_CHOICES, default='others')

    # Resources / Vendors / Sponsors
    resources = models.ManyToManyField(Resource, blank=True, related_name='events')
    vendors   = models.ManyToManyField(Vendor, blank=True, related_name='events')
    sponsors  = models.ManyToManyField(Sponsor, blank=True, related_name='events')

    # Operational notes
    operational_requirements = models.TextField(blank=True)

    # Status & lifecycle
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_events')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.title} [{self.uid}]"

    def registered_count(self):
        return self.members.count()

    def is_full(self):
        return self.registered_count() >= self.max_attendance

    def total_expenses(self):
        return sum(item.actual_amount for item in self.budget_items.all() if item.actual_amount)

    def budget_remaining(self):
        return self.total_budget - (self.total_expenses() or 0)

    def total_sponsorship(self):
        return sum(s.contribution for s in self.sponsors.all())


# ─────────────────────────────────────────────
#  EVENT LIFECYCLE LOG
# ─────────────────────────────────────────────
class EventLifecycleLog(models.Model):
    event      = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='lifecycle_logs')
    from_status = models.CharField(max_length=20, blank=True)
    to_status   = models.CharField(max_length=20)
    changed_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='lifecycle_changes')
    notes       = models.TextField(blank=True)
    changed_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.event.title}: {self.from_status} → {self.to_status}"


# ─────────────────────────────────────────────
#  VENUE BOOKING
# ─────────────────────────────────────────────
class VenueBooking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]

    venue      = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='bookings')
    event      = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='venue_bookings')
    start_time = models.DateTimeField()
    end_time   = models.DateTimeField()
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes      = models.TextField(blank=True)
    booked_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='venue_bookings')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.venue.name} for {self.event.title} ({self.status})"

    def has_conflict(self):
        """Check if booking overlaps with another confirmed booking for the same venue."""
        return VenueBooking.objects.filter(
            venue=self.venue,
            status='confirmed',
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
        ).exclude(pk=self.pk).exists()


# ─────────────────────────────────────────────
#  RESOURCE ALLOCATION
# ─────────────────────────────────────────────
class ResourceAllocation(models.Model):
    STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('allocated', 'Allocated'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled'),
    ]

    resource   = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='allocations')
    event      = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='resource_allocations')
    quantity   = models.PositiveIntegerField(default=1)
    start_time = models.DateTimeField()
    end_time   = models.DateTimeField()
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')
    notes      = models.TextField(blank=True)
    allocated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='resource_allocations')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.resource.name} → {self.event.title} ({self.status})"


# ─────────────────────────────────────────────
#  VENDOR ASSIGNMENT
# ─────────────────────────────────────────────
class VendorAssignment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    vendor      = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='assignments')
    event       = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='vendor_assignments')
    service_description = models.TextField(blank=True)
    agreed_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    delivery_deadline = models.DateTimeField(null=True, blank=True)
    quality_score = models.FloatField(null=True, blank=True, help_text='Post-event quality score 0-10')
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes       = models.TextField(blank=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='vendor_assignments')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.vendor.name} → {self.event.title} ({self.status})"


# ─────────────────────────────────────────────
#  BUDGET ITEM
# ─────────────────────────────────────────────
class BudgetItem(models.Model):
    CATEGORY_CHOICES = [
        ('venue', 'Venue Booking'),
        ('catering', 'Catering'),
        ('staffing', 'Staffing'),
        ('marketing', 'Marketing'),
        ('logistics', 'Logistics'),
        ('equipment', 'Equipment'),
        ('technology', 'Technology'),
        ('decor', 'Decoration'),
        ('miscellaneous', 'Miscellaneous'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    ]

    event          = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='budget_items')
    category       = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='miscellaneous')
    description    = models.CharField(max_length=300)
    projected_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    actual_amount  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    vendor         = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True, blank=True, related_name='budget_items')
    approved_by    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_budget_items')
    notes          = models.TextField(blank=True)
    created_by     = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_budget_items')
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'description']

    def __str__(self):
        return f"{self.event.title} | {self.description} (₹{self.actual_amount})"


# ─────────────────────────────────────────────
#  APPROVAL WORKFLOW
# ─────────────────────────────────────────────
class ApprovalRequest(models.Model):
    TYPE_CHOICES = [
        ('event_publish', 'Event Publish'),
        ('budget_item', 'Budget Item'),
        ('vendor_contract', 'Vendor Contract'),
        ('venue_booking', 'Venue Booking'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    request_type  = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title         = models.CharField(max_length=300)
    description   = models.TextField(blank=True)
    event         = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True, related_name='approval_requests')
    budget_item   = models.ForeignKey(BudgetItem, on_delete=models.CASCADE, null=True, blank=True, related_name='approval_requests')
    requested_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_approval_requests')
    reviewed_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_approval_requests')
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewer_notes = models.TextField(blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    reviewed_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.request_type}] {self.title} ({self.status})"


# ─────────────────────────────────────────────
#  EVENT MEMBER (Registration)
# ─────────────────────────────────────────────
class Notification(models.Model):
    TARGET_SCOPE_CHOICES = [
        ('admin', 'Admin'),
        ('user', 'User'),
        ('both', 'Both'),
    ]
    KIND_CHOICES = [
        ('notification', 'Notification'),
        ('message', 'Message'),
    ]

    title = models.CharField(max_length=200)
    message = models.TextField()
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default='notification')
    target_scope = models.CharField(max_length=20, choices=TARGET_SCOPE_CHOICES, default='both')
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_notifications')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class EventMember(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('attended', 'Attended'),
        ('absent', 'Absent'),
    ]

    ATTENDEE_CATEGORY_CHOICES = [
        ('general', 'General'),
        ('vip', 'VIP'),
        ('guest', 'Guest'),
        ('speaker', 'Speaker'),
        ('sponsor', 'Sponsor'),
        ('volunteer', 'Volunteer'),
    ]

    event             = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='members')
    user              = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_registrations')
    registration_code = models.CharField(max_length=64, unique=True, blank=True)
    registration_data = models.JSONField(blank=True, null=True)
    status            = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    attendee_category = models.CharField(max_length=20, choices=ATTENDEE_CATEGORY_CHOICES, default='general')
    check_in_time     = models.DateTimeField(null=True, blank=True)
    joined_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'user')
        ordering = ['-joined_at']

    def save(self, *args, **kwargs):
        if not self.registration_code:
            import secrets
            self.registration_code = secrets.token_urlsafe(16)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} → {self.event.title} ({self.status})"


# ─────────────────────────────────────────────
#  EVENT WISH (Wishlist)
# ─────────────────────────────────────────────
class EventWish(models.Model):
    event    = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='wishes')
    user     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_wishes')
    added_at = models.DateTimeField(auto_now_add=True)

    # Snapshot of user's registration status at wish-add time
    event_user_status = models.CharField(
        max_length=20,
        choices=EventMember.STATUS_CHOICES,
        blank=True,
        null=True,
        help_text='Registration status of the user for this event when wish was added',
    )

    class Meta:
        unique_together = ('event', 'user')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username} ♥ {self.event.title}"


# ─────────────────────────────────────────────
#  USER MARK (Attendance / Score)
# ─────────────────────────────────────────────
class UserMark(models.Model):
    event      = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='marks')
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_marks')
    marks      = models.PositiveIntegerField(default=0)
    is_absent  = models.BooleanField(default=False)
    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('event', 'user')
        ordering = ['-created_at']

    def __str__(self):
        absent_tag = ' [ABSENT]' if self.is_absent else ''
        return f"{self.user.username} | {self.event.title} | {self.marks} pts{absent_tag}"


# ─────────────────────────────────────────────
#  USER PROFILE
# ─────────────────────────────────────────────
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    father_name = models.CharField(max_length=255, blank=True)
    dob = models.DateField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True)
    contact_email = models.EmailField(blank=True)
    organization = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    is_organizer = models.BooleanField(default=False, help_text='Organizers can access admin features')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile: {self.user.username}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        # ensure profile exists
        if not hasattr(instance, 'profile'):
            Profile.objects.create(user=instance)
        else:
            instance.profile.save()
