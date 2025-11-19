import json
from decimal import Decimal

from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db import transaction

from inventario.models import Producto, AlertaStock
from .models import Venta, VentaItem


@login_required
def rapida(request):
    """
    Vista principal de venta rápida.
    """
    return render(request, "ventas/rapida.html")


@require_GET
@login_required
def buscar_productos(request):
    """
    Busca productos activos y no bloqueados para el buscador en vivo.
    """
    q = request.GET.get("q", "").strip()

    productos = Producto.objects.filter(activo=True, bloqueado=False)

    if q:
        productos = productos.filter(nombre__icontains=q) | productos.filter(sku__icontains=q)

    data = [
        {
            "id": p.id,
            "sku": p.sku,
            "nombre": p.nombre,
            "precio": float(p.precio_unitario),
            "stock": p.stock,
        }
        for p in productos.order_by("nombre")[:20]
    ]

    return JsonResponse({"results": data})


def _crear_alerta_stock(producto):
    """
    Genera una alerta si el stock está bajo el mínimo.
    """
    if producto.stock <= producto.stock_minimo and producto.stock_minimo > 0:
        AlertaStock.objects.get_or_create(
            producto=producto,
            atendida=False,
            defaults={
                "mensaje": f"Stock crítico: {producto.stock} unidades (mínimo {producto.stock_minimo})"
            },
        )


@require_POST
@login_required
def confirmar_venta(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
        items = payload.get("items", [])

        if not items:
            return HttpResponseBadRequest("No se enviaron ítems en la venta.")

        # TRANSACCIÓN ATÓMICA
        with transaction.atomic():
            venta = Venta.objects.create(usuario=request.user)
            total = Decimal("0")

            for it in items:
                prod_id = it.get("id")
                cant = int(it.get("cantidad", 0))

                if cant <= 0:
                    return HttpResponseBadRequest("Cantidad inválida.")

                # Bloqueo de fila para evitar condiciones de carrera
                producto = Producto.objects.select_for_update().get(id=prod_id)

                # Reglas de negocio
                if not producto.activo:
                    return HttpResponseBadRequest(f"El producto {producto.nombre} está inactivo.")

                if producto.bloqueado:
                    return HttpResponseBadRequest(f"El producto {producto.nombre} está bloqueado y no puede venderse.")

                if producto.stock < cant:
                    return HttpResponseBadRequest(f"Stock insuficiente para {producto.nombre}.")

                precio = producto.precio_unitario
                subtotal = precio * cant

                # Crear ítem
                VentaItem.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=cant,
                    precio_unitario=precio,
                    subtotal=subtotal,
                )

                # Actualizar stock
                producto.stock -= cant
                producto.save(update_fields=["stock"])

                # Generar alerta si corresponde
                _crear_alerta_stock(producto)

                total += subtotal

            venta.total = total
            venta.save(update_fields=["total"])

        return JsonResponse({"ok": True, "venta_id": venta.id, "total": float(total)})

    except Producto.DoesNotExist:
        return HttpResponseBadRequest("Producto no encontrado.")

    except Exception as e:
        return HttpResponseBadRequest(str(e))

@login_required
def anular_venta(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)

    if request.method == "POST":
        motivo = request.POST.get("motivo", "")
        venta.anular(request.user, motivo)
        messages.success(request, "La venta fue ANULADA y el stock fue actualizado.")
        return redirect("ventas_historial")

    return render(request, "ventas/anular.html", {"venta": venta})
