from django.contrib import admin
from .models import Venta, VentaItem

class VentaItemInline(admin.TabularInline):
    model = VentaItem
    extra = 0
    readonly_fields = ("subtotal",)

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ("id", "fecha", "total")
    inlines = [VentaItemInline]

