from django.urls import path
from . import views

app_name = "ventas"

urlpatterns = [
    path("", views.rapida, name="home"),
    path("rapida/", views.rapida, name="rapida"),
    path("buscar/", views.buscar_productos, name="buscar"),
    path("confirmar/", views.confirmar_venta, name="confirmar"),
]
