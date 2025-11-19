from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import F  #   IMPORTANTE
from inventario.models import Producto


@login_required
def inicio(request):
    """
    Vista principal del menú de inicio.
    Calcula si hay productos con stock bajo.
    """

    # Productos con stock crítico: stock <= stock_minimo
    stock_bajo = Producto.objects.filter(
        activo=True,
        stock__lte=F("stock_minimo"),  # aquí va stock_minimo, no stock_min
    )

    contexto = {
        "alerta_stock": stock_bajo.exists(),       # True/False
        "items_stock": stock_bajo,                 # queryset por si lo quieres mostrar después
        "total_stock_bajo": stock_bajo.count(),    # cuántos productos están críticos
    }

    return render(request, "inicio/index.html", contexto)
