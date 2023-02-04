from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Car, Reservation
from .serializers import CarSerializer, ReservationSerializer
from .permissions import IsStaffOrReadOnly

from django.db.models import Q

class CarView(ModelViewSet):
    queryset = Car.objects.all()
    serializer_class = CarSerializer
    permission_classes =  (IsStaffOrReadOnly,)  # [IsStaffOrReadOnly]

    def get_queryset(self):
        if self.request.user.is_staff:
            queryset = super().get_queryset()
        else:
            queryset = super().get_queryset().filter(availability=True)
        start = self.request.query_params.get("start")
        end = self.request.query_params.get("end")

        if start is not None or end is not None:

            cond1 = Q(start_date__lt=end)
            cond2 = Q(end_date__gt=start)
            # not_available = Reservation.objects.filter(
            #     start_date__lt=end, end_date__gt=start
            # ).values_list('car_id', flat=True)  # [1, 2]

            not_available = Reservation.objects.filter(
                cond1 & cond2
            ).values_list('car_id', flat=True)  # [1, 2]
            print(not_available)

            queryset = queryset.exclude(id__in=not_available)

        return queryset

class ReservationView(ListCreateAPIView):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self): #if it is not staff, returns only own reservations 
        if self.request.user.is_staff:
            return super().get_queryset()
        return super().get_queryset().filter(customer=self.request.user)
#? to be able to extend reservation date, need to override update method
class ReservationDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        end = serializer.validated_data.get("end_date")
        car  = serializer.validated_data.get("car")
        if Reservation.objects.filter(car=car).exists():
            for res in Reservation.objects.filter(car=car):
                if res.start_date < end < res.end_date:
                    return Response({"message":"Car is not available"})
        #checking if there is another reservation between new dates or not. 

        return super().update(self, request, *args, **kwargs)