import dataclasses
from datetime import datetime
from django.utils import timezone
from typing import Union
from django.db.models import Q
import requests

from vticket_app.configs.related_services import RelatedService
from vticket_app.dtos.user_dto import UserDTO
from vticket_app.models.event import Event
from vticket_app.dtos.create_event_dto import CreateEventDto
from vticket_app.models.event_2_event_topic import Event2EventTopic
from vticket_app.models.event_topic import EventTopic
from vticket_app.models.notification_subscription import NotificationSubscription
from vticket_app.serializers.event_serializer import EventSerializer
from vticket_app.services.ticket_service import TicketService
from vticket_app.enums.fee_type_enum import FeeTypeEnum
from vticket_app.tasks.queue_tasks import async_send_email_to_all_users

class EventService():
    ticket_service = TicketService()

    def create_event(self, event: CreateEventDto) -> Event:
        try:
            _data = dataclasses.asdict(event)
            _ticket_types = event.ticket_types
            _event_topics = event.event_topics

            _data.pop("ticket_types")
            _data.pop("event_topics")

            instance = Event(**_data)
            instance.save()

            if instance.id is None:
                return None
            
            if not self.ticket_service.create_ticket_types(_ticket_types, instance):
                return None
            
            if not self.create_event_topics(_event_topics, instance):
                return None
            
            return instance
        except Exception as e:
            print(e)
            return None
        
    def create_event_topics(self, topics: list, event: Event) -> bool:
        try:
            e2et = []

            for topic in topics:
                e2et.append(
                    Event2EventTopic(
                        event=event,
                        event_topic=topic,
                        deleted_at=None
                    )
                )

            Event2EventTopic.objects.bulk_create(e2et)
            
            return True
        except Exception as e:
            print(e)
            return False
    
    def get_events_by_topic(self, topic: EventTopic) -> list[Event]:
        return Event.objects.filter(event_topic=topic)

    def all(self) -> list[Event]:
        return Event.objects.all()
    
    def search_event(self, keyword: str) -> list[Event]:
        if keyword is None:
            queryset = self.all()
        else:
            queryset = Event.objects.filter(
                Q(name__icontains=keyword)
                | Q(description__icontains=keyword)
            )
            

        return queryset.order_by("-start_date")
    
    def get_value_types_enum(self) -> list:
        values = [choice.value for choice in FeeTypeEnum]
        return values
    
    def change_banner(self, event_id: int, banner_url: str) -> bool:
        try:
            instance = Event.objects.get(id=event_id)
            instance.banner_url = banner_url
            instance.save(update_fields=["banner_url"])
            
            return True
        except Exception as e:
            print(e)
            return False

    def get_event_by_id(self, event_id: int) -> Event | None:
        try:
            return Event.objects.get(id=event_id)
        except Exception as e:
            return None
        
    def get_related_events(self, event: Event):
        today = timezone.now().date()
        events = Event.objects.filter(
            event_topic__in=event.event_topic.all(),
            start_date__gt=today
        ).exclude(id=event.id).distinct().order_by('start_date')[:8]
        return events
    
    def get_owner_info(self, event: Event):
        try:
            response = requests.get(
                url=f'{RelatedService.account}/user/{event.owner_id}/internal',
                headers={
                    "Content-type": "application/json"
                }
            )

            return response.json()["data"]
        except Exception as e:
            print(e, response.text)
            return None
    
    def get_all_event(self, user_id: int) -> list[Event]:
        return Event.objects.filter(owner_id=user_id).order_by("-start_date")
    
    def can_view_statistic(self, event: Event, user: UserDTO) -> bool:
        return event.owner_id == user.id
      
    def send_new_event_email(self, event: Event):
        try:
            emails = NotificationSubscription.objects.filter(deleted_at=None).values_list("email", flat=True)
            async_send_email_to_all_users.apply_async(kwargs={
                    "emails": list(emails),
                    "cc": [],
                    "subject": f"[Vticket] Chào đón sự kiện mới: {event.name}",
                    "template_name": "new_event.html",
                    "context": {
                        "name": event.name,
                        "start_date__day": event.start_date.day,
                        "start_date__month": event.start_date.month,
                        "start_date__year": event.start_date.year,
                        "start_time": event.start_time.strftime("%H:%M"),
                        "event_url": f"https://vticket.netlify.app/event/{event.id}",
                        "logo_url": "https://storage.googleapis.com/vticket-1ccb9.appspot.com/93e815f5-da06-4b4a-890e-48fcdd55da83_logo.png",
                        "event_banner_url": event.banner_url,
                        "location": event.location
                    }
                }
            )
        except Exception as e:
            print(e)


    def get_upcomming_events(self) -> Union[list|None]:
        try:
            _today = datetime.now().date()
            return Event.objects.filter(start_date__gte=_today).order_by("start_date")
        
        except Exception as e:
            print(e)
            return None
        
        
