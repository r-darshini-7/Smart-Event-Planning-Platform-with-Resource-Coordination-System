from django.contrib import admin
from .models import (
    Category, Event, EventMember, EventWish, UserMark,
    Venue, Resource, Vendor, Sponsor,
    VenueBooking, ResourceAllocation, VendorAssignment,
    BudgetItem, ApprovalRequest, EventLifecycleLog, Notification,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'priority', 'status']
    search_fields = ['name', 'code']
    list_filter = ['status']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'venue_name', 'start_time', 'end_time', 'status', 'total_budget']
    search_fields = ['title', 'uid']
    list_filter = ['status', 'category', 'job_category', 'event_type']
    filter_horizontal = ['resources', 'vendors', 'sponsors']


@admin.register(EventMember)
class EventMemberAdmin(admin.ModelAdmin):
    list_display = ['event', 'user', 'status', 'attendee_category', 'joined_at']
    list_filter = ['status', 'attendee_category']


@admin.register(EventWish)
class EventWishAdmin(admin.ModelAdmin):
    list_display = ['event', 'user', 'added_at']


@admin.register(UserMark)
class UserMarkAdmin(admin.ModelAdmin):
    list_display = ['event', 'user', 'marks', 'is_absent', 'created_at']


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'capacity', 'hourly_rate', 'status']
    search_fields = ['name', 'city']
    list_filter = ['status']


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'resource_type', 'quantity', 'unit_cost', 'status']
    search_fields = ['name']
    list_filter = ['resource_type', 'status']


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ['name', 'service_type', 'contact_person', 'performance_rating', 'status']
    search_fields = ['name', 'contact_person']
    list_filter = ['service_type', 'status']


@admin.register(Sponsor)
class SponsorAdmin(admin.ModelAdmin):
    list_display = ['name', 'tier', 'contribution', 'contact_person']
    search_fields = ['name']
    list_filter = ['tier']


@admin.register(VenueBooking)
class VenueBookingAdmin(admin.ModelAdmin):
    list_display = ['venue', 'event', 'start_time', 'end_time', 'status', 'total_cost']
    list_filter = ['status']


@admin.register(ResourceAllocation)
class ResourceAllocationAdmin(admin.ModelAdmin):
    list_display = ['resource', 'event', 'quantity', 'start_time', 'end_time', 'status']
    list_filter = ['status']


@admin.register(VendorAssignment)
class VendorAssignmentAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'event', 'agreed_amount', 'status', 'delivery_deadline']
    list_filter = ['status']


@admin.register(BudgetItem)
class BudgetItemAdmin(admin.ModelAdmin):
    list_display = ['event', 'description', 'category', 'projected_amount', 'actual_amount', 'status']
    list_filter = ['category', 'status']
    search_fields = ['description']


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ['title', 'request_type', 'requested_by', 'status', 'created_at']
    list_filter = ['request_type', 'status']


@admin.register(EventLifecycleLog)
class EventLifecycleLogAdmin(admin.ModelAdmin):
    list_display = ['event', 'from_status', 'to_status', 'changed_by', 'changed_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'kind', 'target_scope', 'is_active', 'created_at']
    list_filter = ['kind', 'target_scope', 'is_active']
