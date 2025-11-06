import json
from decimal import Decimal
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db import transaction
from inventario.models import Producto
from .models import Venta, VentaItem

@login_required
def rapida(request):
    return render(request, "ventas/rapida.html")

@require_GET
@login_required
def buscar_productos(request):
    q = request.GET.get("q","").strip()
    qs = Producto.objects.filter(activo=True)
    if q:
        qs = qs.filter(nombre__icontains=q) | qs.filter(sku__icontains=q)
    data = [{
        "id": p.id, "sku": p.sku, "nombre": p.nombre,
        "precio": float(p.precio_unitario)
    } for p in qs.order_by("nombre")[:20]]
    return JsonResponse({"results": data})

@require_POST
@login_required
def confirmar_venta(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
        items = payload.get("items", [])
        if not items:
            return HttpResponseBadRequest("Sin items")

        with transaction.atomic():
            venta = Venta.objects.create()
            total = Decimal("0")

            for it in items:
                p = Producto.objects.select_for_update().get(id=it["id"])
                cant = int(it["cantidad"])
                if cant <= 0:
                    return HttpResponseBadRequest("Cantidad inválida")
                if p.stock < cant:
                    return HttpResponseBadRequest(f"Stock insuficiente para {p.nombre}")

                precio = p.precio_unitario
                sub = precio * cant

                VentaItem.objects.create(
                    venta=venta,
                    producto=p,
                    cantidad=cant,
                    precio_unitario=precio,
                    subtotal=sub,
                )

                p.stock -= cant
                p.save(update_fields=["stock"])

                total += sub

            venta.total = total
            venta.save(update_fields=["total"])

        return JsonResponse({"ok": True, "venta_id": venta.id, "total": float(total)})

    except Exception as e:
        return HttpResponseBadRequest(str(e))
