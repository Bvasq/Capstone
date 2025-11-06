# inventario/views.py
import csv, io
from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Q
from django.db.models.deletion import ProtectedError

from .models import Producto

# --- helper para decimales (acepta '' y comas) ---
def to_decimal(val):
    if val is None:
        return Decimal("0")
    s = str(val).strip()
    if s == "":
        return Decimal("0")
    s = s.replace(",", ".")  # permitir 1,50
    try:
        return Decimal(s)
    except InvalidOperation:
        return Decimal("0")

@login_required
def lista(request):
    q = (request.GET.get("q") or "").strip()
    productos = Producto.objects.all().order_by("nombre")
    if q:
        productos = Producto.objects.filter(
            Q(nombre__icontains=q) | Q(sku__icontains=q)
        ).order_by("nombre")
    return render(request, "inventario/lista.html", {"productos": productos, "q": q})

@login_required
def crear(request):
    if request.method == "POST":
        Producto.objects.create(
            sku=request.POST["sku"],
            nombre=request.POST["nombre"],
            categoria=request.POST.get("categoria",""),
            precio_unitario=to_decimal(request.POST.get("precio_unitario")),  # <- FIX
            stock=int(request.POST.get("stock",0) or 0),
            stock_minimo=int(request.POST.get("stock_minimo",0) or 0),
            activo=True
        )
        messages.success(request, "Producto creado.")
        return redirect("inventario:lista")
    return render(request, "inventario/crear.html")

@login_required
def editar(request, pk):
    p = get_object_or_404(Producto, pk=pk)
    if request.method == "POST":
        p.sku = request.POST["sku"]
        p.nombre = request.POST["nombre"]
        p.categoria = request.POST.get("categoria","")
        p.precio_unitario = to_decimal(request.POST.get("precio_unitario"))  # <- FIX
        p.stock = int(request.POST.get("stock",0) or 0)
        p.stock_minimo = int(request.POST.get("stock_minimo",0) or 0)
        p.activo = bool(request.POST.get("activo"))
        p.save()
        messages.success(request, "Producto actualizado.")
        return redirect("inventario:lista")
    return render(request, "inventario/editar.html", {"p": p})

@login_required
def eliminar(request, pk):
    p = get_object_or_404(Producto, pk=pk)
    try:
        p.delete()
        messages.success(request, "Producto eliminado.")
    except ProtectedError:
        p.activo = False
        p.save(update_fields=["activo"])
        messages.warning(request, "No se puede eliminar porque tiene ventas asociadas. Se desactivó.")
    return redirect("inventario:lista")

@login_required
def plantilla_csv(request):
    headers = ["sku","nombre","categoria","precio_unitario","stock","stock_minimo","activo"]
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="plantilla_inventario.csv"'
    writer = csv.writer(response)
    writer.writerow(headers)
    return response

@login_required
def importar(request):
    if request.method == "POST" and request.FILES.get("archivo"):
        content = request.FILES["archivo"].read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        creados, actualizados = 0, 0
        for row in reader:
            sku = (row.get("sku") or "").strip()
            if not sku:
                continue
            obj, created = Producto.objects.update_or_create(
                sku=sku,
                defaults={
                    "nombre": row.get("nombre",""),
                    "categoria": row.get("categoria",""),
                    "precio_unitario": to_decimal(row.get("precio_unitario")),  # <- FIX
                    "stock": int(row.get("stock") or 0),
                    "stock_minimo": int(row.get("stock_minimo") or 0),
                    "activo": (str(row.get("activo","1")).lower() in ["1","true","sí","si","y","yes"]),
                }
            )
            if created: creados += 1
            else: actualizados += 1
        messages.success(request, f"Importación OK. Creados: {creados}, Actualizados: {actualizados}")
        return redirect("inventario:lista")
    return render(request, "inventario/importar.html")
