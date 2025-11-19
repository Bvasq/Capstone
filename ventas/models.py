from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.utils import timezone

from inventario.models import Producto

User = get_user_model()

from django.conf import settings
from django.utils import timezone
from django.db import models

class Venta(models.Model):
    ESTADOS = [
        ("PENDIENTE", "Pendiente"),
        ("CONFIRMADA", "Confirmada"),
        ("ANULADA", "Anulada"),
    ]

    fecha = models.DateTimeField(auto_now_add=True)

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ventas",
    )

    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="PENDIENTE")

    # 👇 estos son los nuevos
    anulada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ventas_anuladas",
    )
    motivo_anulacion = models.TextField(blank=True, null=True)
    anulada_en = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Venta #{self.id} - {self.estado}"

    def anular(self, user, motivo=""):
        if self.estado == "ANULADA":
            return False

        for item in self.items.all():
            prod = item.producto
            prod.stock += item.cantidad
            prod.save()

        self.estado = "ANULADA"
        self.anulada_por = user
        self.motivo_anulacion = motivo
        self.anulada_en = timezone.now()
        self.save()
        return True




    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"Venta #{self.id} - {self.fecha:%Y-%m-%d %H:%M}"

    @transaction.atomic
    def anular(self, usuario=None, motivo=""):
        """
        Anula una venta y devuelve el stock a los productos.
        """
        if self.estado == "ANULADA":
            return  # ya está anulada

        # Revertir stock de cada item
        for item in self.items.all():
            producto = item.producto
            producto.stock += item.cantidad
            producto.save()

        self.estado = "ANULADA"
        self.motivo_anulacion = motivo
        self.anulada_en = timezone.now()
        self.save()


class VentaItem(models.Model):
    venta = models.ForeignKey(
        Venta,
        related_name="items",
        on_delete=models.CASCADE
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT
    )

    cantidad = models.PositiveIntegerField(default=1)

    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    def __str__(self):
        return f"{self.producto} x {self.cantidad}"

    def save(self, *args, **kwargs):
        # Calcular subtotal por coherencia
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)
