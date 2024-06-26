from rest_framework import viewsets
from rest_framework.request import Request
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from vticket_app.models.event import Event
from vticket_app.helpers.page_pagination import PagePagination
from vticket_app.serializers.event_serializer import EventSerializer
from vticket_app.services.feedback_service import FeedbackService
from vticket_app.services.ticket_service import TicketService
from vticket_app.utils.response import RestResponse

from vticket_app.services.event_service import EventService
from vticket_app.services.promotion_service import PromotionService

from vticket_app.helpers.swagger_provider import SwaggerProvider
from vticket_app.helpers.image_storage_providers.image_storage_provider import ImageStorageProvider
from vticket_app.helpers.image_storage_providers.firebase_storage_provider import FirebaseStorageProvider

class EventView(viewsets.GenericViewSet):
    serializer_class = EventSerializer
    queryset = Event.objects.all()

    image_storage_provider: ImageStorageProvider = FirebaseStorageProvider()
    event_service = EventService()
    promotion_service = PromotionService()
    feedback_service = FeedbackService()
    ticket_service = TicketService()
    authentication_classes = ()

    def retrieve(self, request: Request, pk: int):
        try:
            event = self.event_service.get_event_by_id(int(pk))

            if event is None:
                return RestResponse().defined_error().set_message("Sự kiện không tồn tại!").response
            
            related_events = self.event_service.get_related_events(event)

            return RestResponse().success().set_data(
                {
                    "event": EventSerializer(event).data,
                    "related_events": EventSerializer(related_events, many=True, exclude=["ticket_types"]).data,
                    "org_info": self.event_service.get_owner_info(event)
                }
            ).response
        except Exception as e:
            print(e) 
            return RestResponse().internal_server_error().response

    @action(methods=["GET"], detail=True, url_path="promotion")
    def get_promotions(self, request: Request, pk: str):
        try:
            result = self.promotion_service.get_promotions_by_event_id(int(pk))
            return RestResponse().success().set_data({"promotions": result}).response
        except Exception as e:
            print(e)
            return RestResponse().internal_server_error().response
        
    @action(methods=["GET"], detail=False, url_path="search", pagination_class=PagePagination)
    @swagger_auto_schema(manual_parameters=[SwaggerProvider.query_param("kw", openapi.TYPE_STRING)])
    def search(self, request: Request):
        try:
            keyword = request.query_params.get("kw", None) 
            events = self.event_service.search_event(keyword=keyword)
            pevents = self.paginate_queryset(events)
            data = EventSerializer(pevents, many=True, exclude=["ticket_types"]).data
            pdata = self.get_paginated_response(data)
            return RestResponse().success().set_data(pdata).response
        except Exception as e:
            print(e)
            return RestResponse().internal_server_error().response
        
    @action(methods=["GET"], detail=False, url_path="value-types")
    def get_value_types(self, request: Request):
        try:
            ticket_types = self.event_service.get_value_types_enum()
            return RestResponse().success().set_data({"ticket_types": ticket_types}).response
        except Exception as e:
            print(e)
            return RestResponse().internal_server_error().response
        
    @action(methods=["GET"], detail=True, url_path="feedback")
    def get_feedbacks(self, request: Request, pk: str):
        try:
            result = self.feedback_service.get_feedbacks_by_event_id(int(pk))
            return RestResponse().success().set_data({"feedbacks": result}).response
        except Exception as e:
            print(e)
            return RestResponse().internal_server_error().response
    
    @action(methods=["GET"], detail=False, url_path="upcomming", pagination_class=PagePagination)
    def get_upcomming_events(self, request: Request):
        try:
            events = self.event_service.get_upcomming_events()
     
            pevents = self.paginate_queryset(events)
            data = EventSerializer(pevents, many=True, exclude=["ticket_types", "event_topic"]).data
            pdata = self.get_paginated_response(data)
            return RestResponse().success().set_data(pdata).response
        except Exception as e:
            print(e) 
            return RestResponse().internal_server_error().response
        
    @action(methods=["GET"], detail=True, url_path="tickets-sold")
    @swagger_auto_schema(manual_parameters=[SwaggerProvider.query_param("start_date", openapi.TYPE_STRING),
                                            SwaggerProvider.query_param("end_date", openapi.TYPE_STRING)])
    def get_tickets_sold(self, request: Request, pk: str):
        try:
            start_date = request.query_params.get("start_date", None) 
            end_date = request.query_params.get("end_date", None)
            result = self.ticket_service.get_tickets_sold_by_event_id(int(pk), start_date=start_date, end_date=end_date)
            return RestResponse().success().set_data(result).response
        except Exception as e:
            print(e)
            return RestResponse().internal_server_error().response