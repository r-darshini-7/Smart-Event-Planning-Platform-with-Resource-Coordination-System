from django.urls import path
from . import views

urlpatterns = [

    # ── Auth ───────────────────────────────────────────
    path('login/',  views.login_view,  name='login'),
    path('signup/',  views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.settings_view, name='settings'),

    # ── Dashboard ──────────────────────────────────────
    path('', views.dashboard, name='dashboard'),

    # ── Category ───────────────────────────────────────
    path('send-message/',                  views.send_message_view,     name='send_message'),
    path('create-event-category/',          views.create_event_category, name='create_event_category'),
    path('event-category/',                 views.event_category,        name='event_category'),
    path('edit-event-category/<int:pk>/',   views.edit_event_category,   name='edit_event_category'),
    path('delete-event-category/<int:pk>/', views.event_category_delete, name='event_category_delete'),

    # ── Event ──────────────────────────────────────────
    path('create-event/',        views.create_event, name='create_event'),
    path('event-list/',          views.event_list,   name='event_list'),
    path('events/type/<str:event_type>/', views.events_by_type, name='events_by_type'),
    path('event-detail/<int:pk>/', views.event_detail, name='event_detail'),
    path('edit-event/<int:pk>/', views.edit_event,   name='edit_event'),
    path('delete-event/<int:pk>/', views.delete_event, name='delete_event'),
    path('register-event/<int:pk>/', views.register_event, name='register_event'),
    path('pay-event/<int:pk>/', views.pay_event_redirect, name='pay_event_redirect'),
    path('registration-qr/<int:pk>/', views.event_registration_qr, name='event_registration_qr'),
    path('registration-qr/<int:pk>/download/', views.event_registration_qr_download, name='event_registration_qr_download'),
    path('registration-pdf/<int:pk>/download/', views.event_registration_pdf_download, name='event_registration_pdf_download'),
    path('my-activity/', views.my_activity, name='my_activity'),
    path('certificates/', views.certificates, name='certificates'),
    path('certificates/<int:pk>/download/', views.certificate_download, name='certificate_download'),

    # Event lifecycle
    path('event/<int:pk>/advance-status/', views.event_advance_status, name='event_advance_status'),
    path('event/<int:pk>/lifecycle/', views.event_lifecycle_log, name='event_lifecycle_log'),

    # Export
    path('event/<int:pk>/export/attendees/', views.export_attendees_csv, name='export_attendees_csv'),
    path('event/<int:pk>/export/budget/',    views.export_budget_csv,    name='export_budget_csv'),
    path('export/analytics/', views.export_analytics_csv, name='export_analytics_csv'),

    # ── Members / Status ───────────────────────────────
    path('add-event-member/',                views.add_event_member,     name='add_event_member'),
    path('remove-event-member/<int:pk>/',    views.remove_event_member,  name='remove_event_member'),
    path('join-event-list/',                 views.join_event_list,      name='join_event_list'),
    path('update-event-status/<int:pk>/',    views.update_event_status,  name='update_event_status'),
    path('member/<int:pk>/checkin/',         views.attendee_checkin,     name='attendee_checkin'),
    path('member/<int:pk>/category/',        views.attendee_category_update, name='attendee_category_update'),

    # ── Attendance / Marks ─────────────────────────────
    path('absense-user-list/',                       views.absense_user_list,       name='absense_user_list'),
    path('complete-event-list/',                     views.complete_event_list,     name='complete_event_list'),
    path('complete-event-user-list/<int:pk>/',       views.complete_event_user_list, name='complete_event_user_list'),
    path('create-user-mark/',                        views.create_user_mark,        name='create_user_mark'),
    path('user-mark-list/',                          views.user_mark_list,          name='user_mark_list'),

    # ── Wishlist ───────────────────────────────────────
    path('event-user-wish-list/', views.event_user_wish_list, name='event_user_wish_list'),
    path('add-event-user-wish/',  views.add_event_user_wish,  name='add_event_user_wish'),
    path('remove-event-user-wish/<int:pk>/', views.remove_event_user_wish, name='remove_event_user_wish'),

    # ── Venues ─────────────────────────────────────────
    path('venues/',                      views.venue_list,           name='venue_list'),
    path('venues/create/',               views.venue_create,         name='venue_create'),
    path('venues/<int:pk>/edit/',        views.venue_edit,           name='venue_edit'),
    path('venues/<int:pk>/delete/',      views.venue_delete,         name='venue_delete'),
    path('venue-bookings/',              views.venue_booking_list,   name='venue_booking_list'),
    path('venue-bookings/create/',       views.venue_booking_create, name='venue_booking_create'),
    path('venue-bookings/<int:pk>/confirm/', views.venue_booking_confirm, name='venue_booking_confirm'),
    path('venue-bookings/<int:pk>/cancel/', views.venue_booking_cancel,  name='venue_booking_cancel'),

    # ── Resources ──────────────────────────────────────
    path('resources/',                        views.resource_list,             name='resource_list'),
    path('resources/create/',                 views.resource_create,           name='resource_create'),
    path('resources/<int:pk>/edit/',          views.resource_edit,             name='resource_edit'),
    path('resources/<int:pk>/delete/',        views.resource_delete,           name='resource_delete'),
    path('resource-allocations/',             views.resource_allocation_list,  name='resource_allocation_list'),
    path('resource-allocations/create/',      views.resource_allocation_create, name='resource_allocation_create'),
    path('resource-allocations/<int:pk>/update/', views.resource_allocation_update, name='resource_allocation_update'),

    # ── Vendors ────────────────────────────────────────
    path('vendors/',                          views.vendor_list,               name='vendor_list'),
    path('vendors/create/',                   views.vendor_create,             name='vendor_create'),
    path('vendors/<int:pk>/edit/',            views.vendor_edit,               name='vendor_edit'),
    path('vendors/<int:pk>/delete/',          views.vendor_delete,             name='vendor_delete'),
    path('vendor-assignments/',               views.vendor_assignment_list,    name='vendor_assignment_list'),
    path('vendor-assignments/create/',        views.vendor_assignment_create,  name='vendor_assignment_create'),
    path('vendor-assignments/<int:pk>/status/', views.vendor_assignment_update_status, name='vendor_assignment_update_status'),

    # ── Sponsors ───────────────────────────────────────
    path('sponsors/',                views.sponsor_list,   name='sponsor_list'),
    path('sponsors/create/',         views.sponsor_create, name='sponsor_create'),
    path('sponsors/<int:pk>/edit/',  views.sponsor_edit,   name='sponsor_edit'),
    path('sponsors/<int:pk>/delete/', views.sponsor_delete, name='sponsor_delete'),

    # ── Budget ─────────────────────────────────────────
    path('budget/',                         views.budget_list,         name='budget_list'),
    path('budget/create/',                  views.budget_item_create,  name='budget_item_create'),
    path('budget/<int:pk>/edit/',           views.budget_item_edit,    name='budget_item_edit'),
    path('budget/<int:pk>/delete/',         views.budget_item_delete,  name='budget_item_delete'),
    path('budget/<int:pk>/approve/',        views.budget_item_approve, name='budget_item_approve'),

    # ── Approvals ──────────────────────────────────────
    path('approvals/',              views.approval_list,   name='approval_list'),
    path('approvals/create/',       views.approval_create, name='approval_create'),
    path('approvals/<int:pk>/review/', views.approval_review, name='approval_review'),

    # ── Analytics ──────────────────────────────────────
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),

    # ── REST API ───────────────────────────────────────
    path('api/events/',                        views.api_events,        name='api_events'),
    path('api/events/<int:pk>/',               views.api_event_detail,  name='api_event_detail'),
    path('api/events/<int:event_pk>/registrations/', views.api_registrations, name='api_registrations'),
    path('api/events/<int:event_pk>/budget/',  views.api_budget,        name='api_budget'),
    path('api/resources/',                     views.api_resources,     name='api_resources'),
    path('api/vendors/',                       views.api_vendors,       name='api_vendors'),
    path('api/venues/',                        views.api_venues,        name='api_venues'),
    path('api/analytics/',                     views.api_analytics,     name='api_analytics'),
    path('api/checkin-by-code/',               views.api_checkin_by_code, name='api_checkin_by_code'),
]
