import dataclasses
from uuid import uuid4
from typing import Tuple, Union
from django.db import transaction
from django.core.cache import cache

from vticket_app.models.event import Event
from vticket_app.models.ticket_type import TicketType
from vticket_app.models.ticket_type_detail import TicketTypeDetail
from vticket_app.models.seat_configuration import SeatConfiguration
from vticket_app.models.user_ticket import UserTicket
from vticket_app.models.booking import Booking

from vticket_app.dtos.ticket_type_dto import TicketTypeDto
from vticket_app.dtos.ticket_type_detail_dto import TicketTypeDetailDto
from vticket_app.dtos.seat_configuration_dto import SeatConfigurationDto

from vticket_app.enums.instance_error_enum import InstanceErrorEnum

class TicketService():
    booking_payment_minute = 15

    def create_ticket_types(self, dataset: list[TicketTypeDto], event: Event) -> bool:
        try:
            for data in dataset:
                _details = data.ticket_type_details
                _seats = data.seat_configurations
                
                _data = dataclasses.asdict(data)
                _data.pop("ticket_type_details")
                _data.pop("seat_configurations")

                instance = TicketType.objects.create(event=event, **_data)
                result = (
                    bool(instance.id)
                    and self.config_seats(_seats, instance)
                    and self.create_ticket_type_details(_details, instance)
                )
                
                if not result:
                    return False
                
            return True
        except Exception as e:
            print(e)
            return False
        
    def create_ticket_type_details(self, dataset: list[TicketTypeDetailDto], ticket_type: TicketType):
        try:
            instances = TicketTypeDetail.objects.bulk_create(
                [
                    TicketTypeDetail(
                        ticket_type=ticket_type, 
                        **dataclasses.asdict(data)
                    ) 
                    for data in dataset
                ]
            )
            return all(bool(instance.id) for instance in instances)
        except Exception as e:
            print(e)
            return False
        
    def config_seats(self, dataset: list[SeatConfigurationDto], ticket_type: TicketType) -> bool:
        try:
            instances = []

            for data in dataset:
                for seat_number in range(data.start_seat_number, data.end_seat_number):
                    instances.append(
                        SeatConfiguration(
                            ticket_type=ticket_type,
                            position=data.position,
                            seat_number=seat_number
                        )
                    )
            SeatConfiguration.objects.bulk_create(instances)
            
            return all(bool(instance.id) for instance in instances)
        except Exception as e:
            print(e)
            return False
        
    def booking(self, user_id: int, seats: list[SeatConfiguration]) -> Union[InstanceErrorEnum, Tuple[str, None]]:
        try:

            if any(cache.keys(f"booking:*:seat:{seat.id}") for seat in seats):
                return InstanceErrorEnum.EXISTED, None
            
            _booking_id = uuid4().hex

            self._cache_booking(_booking_id, user_id, seats)
            self._save_booking(_booking_id, user_id, seats)

            return InstanceErrorEnum.ALL_OK, _booking_id
        except Exception as e:
            print(e)
            return InstanceErrorEnum.EXCEPTION, None
        
    def _cache_booking(self, id: str, user_id: int, seats: list[SeatConfiguration]):
        _booking_data = {}

        for seat in seats:
            _booking_data[f"booking:{id}:seat:{seat.id}"] = {
                "user_id": user_id,
                "seat_id": seat.id
            }
        
        cache.set_many(_booking_data, self.booking_payment_minute*60)

    def _save_booking(self, id: str, user_id: int, seats: list[SeatConfiguration]):
        try:
            with transaction.atomic():
                instance = Booking(id=id, user_id=user_id)
                instance.save()
                instance.seats.set(seats)
        except Exception as e:
            print(e)