from rest_framework import serializers

from vticket_app.models.ticket_type_detail import TicketTypeDetail

class TicketTypeDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketTypeDetail
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        existing = set(self.fields.keys())
        fields = kwargs.pop("fields", []) or existing
        exclude = kwargs.pop("exclude", [])
        
        super().__init__(*args, **kwargs)
        
        for field in exclude + list(existing - fields):
            self.fields.pop(field, None)