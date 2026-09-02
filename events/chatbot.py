"""
Event Management Chatbot Module
Handles NLP-based queries about events, event details, dates, and reminder settings.
"""
import re
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q
from .models import Event, EventMember, Notification, Profile


class EventChatbot:
    """Chatbot for answering event-related questions"""

    def __init__(self, user):
        self.user = user
        self.intent_patterns = {
            'live_events': [
                r'what.*events.*live',
                r'which.*events.*happening',
                r'active.*events',
                r'ongoing.*events',
                r'current.*events',
                r'show.*live.*events',
            ],
            'event_details': [
                r'tell.*event.*details',
                r'event.*information',
                r'about.*event',
                r'event.*description',
            ],
            'event_dates': [
                r'when.*event',
                r'date.*event',
                r'time.*event',
                r'schedule.*event',
                r'event.*timing',
                r'start.*end.*time',
            ],
            'registered_events': [
                r'my.*events',
                r'events.*registered',
                r'joined.*events',
                r'registered.*events',
                r'events.*i.*registered',
            ],
            'event_location': [
                r'where.*event',
                r'event.*location',
                r'event.*venue',
                r'location.*event',
            ],
            'event_speakers': [
                r'who.*speaking',
                r'speaker.*event',
                r'resource.*person',
            ],
            'event_capacity': [
                r'capacity.*event',
                r'attendees.*event',
                r'how.*many.*can.*attend',
                r'event.*full',
            ],
            'reminder_settings': [
                r'reminder.*settings',
                r'notify.*event',
                r'notification.*settings',
                r'when.*notify',
                r'remind.*me',
            ],
            'event_price': [
                r'event.*price',
                r'cost.*event',
                r'how.*much',
                r'fee.*event',
                r'paid.*free',
            ],
            'join_event': [
                r'how.*join',
                r'register.*event',
                r'enroll.*event',
                r'participate.*event',
            ],
        }

    def detect_intent(self, query):
        """Detect user intent from query"""
        query_lower = query.lower().strip()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return intent
        
        return 'general'

    def extract_event_name(self, query):
        """Extract event name or keyword from query"""
        # Remove common question words
        query_lower = query.lower()
        stop_words = [
            'what', 'which', 'when', 'where', 'who', 'how', 'is', 'are', 'the',
            'event', 'events', 'tell', 'show', 'about', 'details', 'information',
            'can', 'i', 'my', 'me', 'for', 'of'
        ]
        
        words = [w for w in query_lower.split() if w not in stop_words and len(w) > 2]
        return ' '.join(words) if words else None

    def get_live_events(self):
        """Get all live/upcoming events"""
        now = timezone.now()
        events = Event.objects.filter(
            status='live',
            end_time__gte=now
        ).order_by('start_time')[:10]
        return events

    def get_user_events(self):
        """Get events where user is registered"""
        return EventMember.objects.filter(
            user=self.user
        ).select_related('event').values_list('event', flat=True)

    def format_event_details(self, event):
        """Format event information for display"""
        now = timezone.now()
        is_upcoming = event.start_time > now
        
        details = {
            'title': event.title,
            'description': event.description or 'No description available',
            'start_time': event.start_time.strftime('%B %d, %Y at %I:%M %p'),
            'end_time': event.end_time.strftime('%B %d, %Y at %I:%M %p'),
            'mode': event.get_mode_display() if hasattr(event, 'get_mode_display') else event.mode,
            'location': event.location or event.venue_name or 'Virtual',
            'status': '🔴 Live' if not is_upcoming else '🔵 Upcoming',
            'max_attendance': event.max_attendance,
            'registered_count': event.registered_count(),
            'spots_available': max(0, event.max_attendance - event.registered_count()),
            'price': f"₹{event.price}" if event.price > 0 else 'Free',
            'speaker': event.speaker_name or 'Not specified',
            'points': event.points,
        }
        return details

    def answer_live_events(self):
        """Answer query about live events"""
        events = self.get_live_events()
        
        if not events:
            return {
                'status': 'success',
                'message': 'No live events currently. Check back soon!',
                'events': []
            }
        
        events_list = []
        for event in events[:5]:
            details = self.format_event_details(event)
            events_list.append(details)
        
        return {
            'status': 'success',
            'message': f'Found {len(events_list)} live events:',
            'events': events_list
        }

    def answer_event_details(self, query):
        """Answer query about specific event details"""
        event_name = self.extract_event_name(query)
        
        if not event_name:
            # If no event name specified, show registered events
            user_event_ids = self.get_user_events()
            if user_event_ids:
                events = Event.objects.filter(id__in=user_event_ids).order_by('-start_time')[:3]
            else:
                events = self.get_live_events()[:3]
        else:
            # Search for event by name
            events = Event.objects.filter(
                Q(title__icontains=event_name) |
                Q(description__icontains=event_name)
            ).order_by('-start_time')[:3]
        
        if not events:
            return {
                'status': 'not_found',
                'message': f'No events found matching "{event_name}"',
                'events': []
            }
        
        events_list = [self.format_event_details(event) for event in events]
        
        return {
            'status': 'success',
            'message': f'Found {len(events_list)} event(s):',
            'events': events_list
        }

    def answer_event_dates(self, query):
        """Answer query about event dates and timing"""
        event_name = self.extract_event_name(query)
        
        if event_name:
            events = Event.objects.filter(
                Q(title__icontains=event_name)
            ).order_by('start_time')[:3]
        else:
            events = self.get_live_events()[:5]
        
        if not events:
            return {
                'status': 'not_found',
                'message': 'No events found',
                'events': []
            }
        
        events_list = []
        for event in events:
            events_list.append({
                'title': event.title,
                'start_date': event.start_time.strftime('%A, %B %d, %Y'),
                'start_time': event.start_time.strftime('%I:%M %p'),
                'end_date': event.end_time.strftime('%A, %B %d, %Y'),
                'end_time': event.end_time.strftime('%I:%M %p'),
                'duration': self._calculate_duration(event.start_time, event.end_time),
            })
        
        return {
            'status': 'success',
            'message': 'Event dates and timings:',
            'events': events_list
        }

    def answer_registered_events(self):
        """Answer query about user's registered events"""
        user_event_ids = self.get_user_events()
        events = Event.objects.filter(id__in=user_event_ids).order_by('start_time')
        
        if not events:
            return {
                'status': 'success',
                'message': 'You have not registered for any events yet.',
                'events': []
            }
        
        events_list = [self.format_event_details(event) for event in events[:10]]
        
        return {
            'status': 'success',
            'message': f'You are registered for {len(events)} event(s):',
            'events': events_list
        }

    def answer_reminder_settings(self):
        """Answer query about reminder/notification settings"""
        try:
            profile = Profile.objects.get(user=self.user)
        except Profile.DoesNotExist:
            return {
                'status': 'success',
                'message': 'No reminder settings configured. You can update your preferences in your profile.',
                'settings': {
                    'email_notifications': False,
                    'sms_notifications': False,
                    'event_reminders': False,
                }
            }
        
        # Get user's notification preferences (implement based on your Profile model)
        user_events = EventMember.objects.filter(user=self.user).select_related('event')
        upcoming_events = [
            um.event for um in user_events 
            if um.event.start_time > timezone.now()
        ]
        
        settings = {
            'upcoming_events': len(upcoming_events),
            'events_with_notifications': min(len(upcoming_events), 3),
            'default_reminder_time': '1 day before',
        }
        
        return {
            'status': 'success',
            'message': 'Your notification/reminder settings:',
            'settings': settings
        }

    def answer_event_location(self, query):
        """Answer query about event location"""
        event_name = self.extract_event_name(query)
        
        if event_name:
            events = Event.objects.filter(
                Q(title__icontains=event_name)
            )[:3]
        else:
            events = self.get_live_events()[:3]
        
        if not events:
            return {
                'status': 'not_found',
                'message': 'No events found',
                'events': []
            }
        
        events_list = []
        for event in events:
            events_list.append({
                'title': event.title,
                'mode': event.mode.upper() if event.mode else 'HYBRID',
                'location': event.location or event.venue_name or 'Virtual/Online',
                'venue': event.venue.name if event.venue else 'N/A',
                'latitude': event.map_latitude,
                'longitude': event.map_longitude,
            })
        
        return {
            'status': 'success',
            'message': 'Event location details:',
            'events': events_list
        }

    def answer_event_capacity(self, query):
        """Answer query about event capacity and attendance"""
        event_name = self.extract_event_name(query)
        
        if event_name:
            events = Event.objects.filter(
                Q(title__icontains=event_name)
            )[:3]
        else:
            events = self.get_live_events()[:3]
        
        if not events:
            return {
                'status': 'not_found',
                'message': 'No events found',
                'events': []
            }
        
        events_list = []
        for event in events:
            registered = event.registered_count()
            capacity = event.max_attendance
            percentage = int((registered / capacity * 100)) if capacity > 0 else 0
            
            events_list.append({
                'title': event.title,
                'max_capacity': capacity,
                'registered': registered,
                'available_spots': max(0, capacity - registered),
                'occupancy_percentage': percentage,
                'is_full': event.is_full(),
                'status': '✅ Full' if event.is_full() else f'✓ {percentage}% Full',
            })
        
        return {
            'status': 'success',
            'message': 'Event capacity information:',
            'events': events_list
        }

    def answer_general(self, query):
        """Handle general queries"""
        return {
            'status': 'success',
            'message': f'I can help you with questions about:\n'
                      f'• Live and upcoming events\n'
                      f'• Event details and information\n'
                      f'• Event dates and timings\n'
                      f'• Your registered events\n'
                      f'• Event locations and venues\n'
                      f'• Event speakers and resources\n'
                      f'• Event capacity and attendance\n'
                      f'• Reminder and notification settings\n'
                      f'• Event pricing\n\n'
                      f'Feel free to ask me anything about events!',
            'quick_questions': [
                'What events are live?',
                'When is my next event?',
                'What events am I registered for?',
                'How do I join an event?',
            ]
        }

    def process_query(self, query):
        """Main method to process user query and return response"""
        if not query or not query.strip():
            return self.answer_general('')
        
        intent = self.detect_intent(query)
        
        if intent == 'live_events':
            return self.answer_live_events()
        elif intent == 'event_details':
            return self.answer_event_details(query)
        elif intent == 'event_dates':
            return self.answer_event_dates(query)
        elif intent == 'registered_events':
            return self.answer_registered_events()
        elif intent == 'reminder_settings':
            return self.answer_reminder_settings()
        elif intent == 'event_location':
            return self.answer_event_location(query)
        elif intent == 'event_capacity':
            return self.answer_event_capacity(query)
        else:
            return self.answer_general(query)

    @staticmethod
    def _calculate_duration(start_time, end_time):
        """Calculate event duration in human-readable format"""
        diff = end_time - start_time
        hours = diff.total_seconds() / 3600
        
        if hours < 1:
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes} minutes"
        elif hours == 1:
            return "1 hour"
        elif hours < 24:
            return f"{int(hours)} hours"
        else:
            days = diff.days
            return f"{days} day(s)"
