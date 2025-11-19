from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, F, Q, DecimalField, ExpressionWrapper

from inventario.models import Producto, AlertaStock
from ventas.models import Venta, VentaItem


@login_required
def index(request):
    """
    Dashboard de reportes principales del negocio.

    Incluye:
    - Estado de stock por producto
    - Productos bajo stock mínimo
    - Top productos más vendidos (últimos 30 días)
    - Ventas y margen bruto últimos 30 días
    - Sugerencias de compra
    - Alertas de stock crítico (generadas automáticamente)
    """

    hoy = timezone.now().date()
    hace_30 = hoy - timedelta(days=30)

    # 1) ESTADO DE STOCK GENERAL
    productos = Producto.objects.filter(activo=True).order_by("nombre")

    def estado_stock(p):
        if p.stock <= p.stock_minimo:
            return "BAJO"
        if p.stock <= p.stock_minimo * 1.5:
            return "MEDIO"
        return "ALTO"

    listado = [
        {
            "producto": p,
            "estado": estado_stock(p),
        }
        for p in productos
    ]

    # 2) VENTAS ÚLTIMOS 30 DÍAS (solo CONFIRMADAS)
    ventas_30 = Venta.objects.filter(
        fecha__date__gte=hace_30,
        fecha__date__lte=hoy,
        estado="CONFIRMADA",
    )

    total_vendido_30 = ventas_30.aggregate(total=Sum("total"))["total"] or 0

    # 3) MARGEN BRUTO ESTIMADO (innovación: usamos costo vs precio)
    margen_expr = ExpressionWrapper(
        F("cantidad") * (F("precio_unitario") - F("producto__costo")),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )

    margen_30 = (
        VentaItem.objects.filter(venta__in=ventas_30)
        .aggregate(ganancia=Sum(margen_expr))
        .get("ganancia")
        or 0
    )

    # 4) TOP 10 PRODUCTOS MÁS VENDIDOS (por cantidad)
    top = (
        VentaItem.objects.filter(venta__in=ventas_30)
        .values("producto__nombre")
        .annotate(
            cantidad_total=Sum("cantidad"),
            monto_total=Sum("subtotal"),
        )
        .order_by("-cantidad_total")[:10]
    )

    # 5) PRODUCTOS CON STOCK CRÍTICO
    criticos = (
        Producto.objects.filter(
            activo=True,
            stock__lte=F("stock_minimo"),
            stock_minimo__gt=0,
        )
        .order_by("stock")
    )

    # 6) SUGERENCIAS DE COMPRA (en base a lo vendido y stock)
    sugerencias = (
        Producto.objects.filter(
            activo=True,
            stock__lte=F("stock_minimo"),
            stock_minimo__gt=0,
        )
        .annotate(
            vendido_30=Sum(
                "ventaitem__cantidad",
                filter=Q(
                    ventaitem__venta__fecha__date__gte=hace_30,
                    ventaitem__venta__estado="CONFIRMADA",
                ),
            )
        )
        .order_by("-vendido_30")
    )

    # 7) ALERTAS DE STOCK CRÍTICO NO ATENDIDAS
    alertas = (
        AlertaStock.objects.filter(atendida=False)
        .select_related("producto")
        .order_by("-creado_en")[:20]
    )

    contexto = {
        "listado": listado,
        "total_vendido_30": total_vendido_30,
        "margen_30": margen_30,
        "top_productos": top,
        "criticos": criticos,
        "sugerencias": sugerencias,
        "alertas": alertas,
        "desde": hace_30,
        "hasta": hoy,
    }

    return render(request, "reportes/index.html", contexto)
