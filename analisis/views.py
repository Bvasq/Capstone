from datetime import datetime, timedelta

from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone

from ventas.models import Venta, VentaItem


def index(request):
    """
    Módulo de análisis avanzado del negocio.
    Genera:
    - Ventas diarias
    - Top productos más vendidos
    - Monto por categoría
    - Filtro por rango de fechas
    """

    hoy = timezone.localdate()

    # -----------------------------
    # 1. Manejo de fechas desde GET
    # -----------------------------
    ds = request.GET.get("desde")
    hs = request.GET.get("hasta")

    def parse_date(s, fallback):
        try:
            return datetime.strptime(s, "%Y-%m-%d").date() if s else fallback
        except ValueError:
            return fallback

    desde = parse_date(ds, hoy - timedelta(days=30))
    hasta = parse_date(hs, hoy)

    # -----------------------------
    # 2. Ventas diarias (solo CONFIRMADAS)
    # -----------------------------
    ventas_diarias = (
        Venta.objects.filter(
            estado="CONFIRMADA",
            fecha__date__gte=desde,
            fecha__date__lte=hasta,
        )
        .annotate(dia=TruncDate("fecha"))
        .values("dia")
        .annotate(monto_total=Sum("total"))
        .order_by("dia")
    )

    vd_labels = [v["dia"].strftime("%Y-%m-%d") for v in ventas_diarias]
    vd_data = [float(v["monto_total"] or 0) for v in ventas_diarias]

    # -----------------------------
    # 3. Top productos más vendidos
    # -----------------------------
    top = (
        VentaItem.objects.filter(
            venta__estado="CONFIRMADA",
            venta__fecha__date__gte=desde,
            venta__fecha__date__lte=hasta,
        )
        .annotate(nombre=F("producto__nombre"))
        .values("nombre")
        .annotate(cantidad_total=Sum("cantidad"))
        .order_by("-cantidad_total")[:5]
    )

    top_labels = [t["nombre"] for t in top]
    top_data = [int(t["cantidad_total"] or 0) for t in top]

    # -----------------------------
    # 4. Monto por categoría
    # -----------------------------
    monto_expr = ExpressionWrapper(
        F("cantidad") * F("precio_unitario"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )

    categorias = (
        VentaItem.objects.filter(
            venta__estado="CONFIRMADA",
            venta__fecha__date__gte=desde,
            venta__fecha__date__lte=hasta,
        )
        .annotate(cat=F("producto__categoria__nombre"))
        .values("cat")
        .annotate(monto=Sum(monto_expr))
        .order_by("-monto")
    )

    cat_labels = [c["cat"] or "Sin categoría" for c in categorias]
    cat_data = [float(c["monto"] or 0) for c in categorias]

    # -----------------------------
    # 5. Contexto al template
    # -----------------------------
    ctx = {
        "desde": desde.strftime("%Y-%m-%d"),
        "hasta": hasta.strftime("%Y-%m-%d"),
        "vd_labels": vd_labels,
        "vd_data": vd_data,
        "top_labels": top_labels,
        "top_data": top_data,
        "cat_labels": cat_labels,
        "cat_data": cat_data,
        "categorias_tabla": categorias,
    }

    return render(request, "analisis/index.html", ctx)
