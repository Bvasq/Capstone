from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from django.db.models.functions import TruncDate
from datetime import datetime, timedelta

from ventas.models import Venta, VentaItem

def index(request):
    hoy = timezone.localdate()

    ds = request.GET.get("desde")
    hs = request.GET.get("hasta")

    try:
        desde = datetime.strptime(ds, "%Y-%m-%d").date() if ds else hoy - timedelta(days=30)
    except Exception:
        desde = hoy - timedelta(days=30)

    try:
        hasta = datetime.strptime(hs, "%Y-%m-%d").date() if hs else hoy
    except Exception:
        hasta = hoy

    # Esto es el modulo de la venta diarioa
    ventas_diarias = (
        Venta.objects.filter(fecha__date__gte=desde, fecha__date__lte=hasta)
        .annotate(dia=TruncDate("fecha"))
        .values("dia")
        .annotate(total=Sum("total"))
        .order_by("dia")
    )
    vd_labels = [v["dia"].strftime("%Y-%m-%d") for v in ventas_diarias]
    vd_data   = [float(v["total"] or 0) for v in ventas_diarias]

    #top productos
    top = (
        VentaItem.objects.filter(venta__fecha__date__gte=desde, venta__fecha__date__lte=hasta)
        .values("producto__nombre")
        .annotate(nombre=F("producto__nombre"), cantidad=Sum("cantidad"))
        .order_by("-cantidad")[:5]
    )
    top_labels = [t["nombre"] for t in top]
    top_data   = [int(t["cantidad"] or 0) for t in top]

    # Monto de lawea
    monto_expr = ExpressionWrapper(
        F("cantidad") * F("precio_unitario"),
        output_field=DecimalField(max_digits=12, decimal_places=2)
    )
    categorias = (
        VentaItem.objects.filter(venta__fecha__date__gte=desde, venta__fecha__date__lte=hasta)
        .values("producto__categoria")
        .annotate(categoria=F("producto__categoria"), monto=Sum(monto_expr))
        .order_by("-monto")
    )
    cat_labels = [c["categoria"] or "Sin categoría" for c in categorias]
    cat_data   = [float(c["monto"] or 0) for c in categorias]

    ctx = {
        "desde": desde.strftime("%Y-%m-%d"),
        "hasta": hasta.strftime("%Y-%m-%d"),
        "vd_labels": vd_labels,
        "vd_data": vd_data,
        "top_labels": top_labels,
        "top_data": top_data,
        "cat_labels": cat_labels,
        "cat_data": cat_data,
    }
    return render(request, "analisis/index.html", ctx)

