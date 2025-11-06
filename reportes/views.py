from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from inventario.models import Producto

@login_required
def index(request):
    productos = Producto.objects.order_by("nombre")
    def estado(p):
        if p.stock <= p.stock_minimo: return "BAJO"
        if p.stock <= p.stock_minimo * 1.5: return "MEDIO"
        return "ALTO"
    listado = [{"p":p, "estado": estado(p)} for p in productos]
    return render(request, "reportes/index.html", {"listado": listado})
