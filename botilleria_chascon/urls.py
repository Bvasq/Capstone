from . import views
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("admin/", admin.site.urls),
    path("analisis/", include("analisis.urls")),
    path("inventario/", include("inventario.urls")),
    path("ventas/", include("ventas.urls")),
    path("reportes/", include("reportes.urls")),
]
