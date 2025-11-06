from django.urls import path
from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("crear/", views.crear, name="crear"),
    path("<int:pk>/editar/", views.editar, name="editar"),
    path("<int:pk>/eliminar/", views.eliminar, name="eliminar"),
    path("importar/", views.importar, name="importar"),
    path("plantilla.csv", views.plantilla_csv, name="plantilla"),
]
