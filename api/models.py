from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.mail import send_mail
from django.conf import settings
import uuid
from django.utils import timezone
from datetime import timedelta
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

# ===========================
#        USUARIOS
# ===========================

class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El correo electrónico es obligatorio')
        email = self.normalize_email(email)
        usuario = self.model(email=email, **extra_fields)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class Usuario(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    nombre = models.CharField(max_length=255)
    apellido = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'apellido']

    def __str__(self):
        return self.email

    def enviar_email(self, subject, message):
        send_mail(subject, message, settings.EMAIL_HOST_USER, [self.email], fail_silently=False)

class Root(Usuario):
    def crear_administradores(self, email, password, **extra_fields):
        return Administrador.objects.create_user(email=email, password=password, **extra_fields)

    def eliminar_administradores(self, administrador):
        administrador.delete()

class Administrador(Usuario):
    direccion = models.CharField(max_length=255)
    genero = models.CharField(max_length=50)

    def editar_perfil(self, nuevos_datos):
        for key, value in nuevos_datos.items():
            setattr(self, key, value)
        self.save()

class Cliente(Usuario):
    cc = models.CharField(max_length=20)
    fecha_nacimiento = models.DateField()
    direccion = models.CharField(max_length=255)
    genero = models.CharField(max_length=50)
    historial_compras = models.JSONField(default=list)
    reservas = models.JSONField(default=list)
    preferencias_literarias = models.JSONField(default=list)
    recibir_noticias = models.BooleanField(default=False)

    def editar_perfil(self, nuevos_datos):
        for key, value in nuevos_datos.items():
            setattr(self, key, value)
        self.save()

# ===========================
#         LIBROS
# ===========================

class Libro(models.Model):
    titulo = models.CharField(max_length=200)
    autor = models.CharField(max_length=100)
    anio_publicacion = models.PositiveIntegerField()
    genero = models.CharField(max_length=100)
    numero_paginas = models.PositiveIntegerField()
    editorial = models.CharField(max_length=100)
    issn = models.CharField(max_length=20)
    idioma = models.CharField(max_length=50)
    fecha_publicacion = models.DateField()
    categoria = models.CharField(max_length=100)
    imagen = models.URLField(blank=True)
    destacado = models.BooleanField(default=False)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)


    def __str__(self):
        return f"{self.titulo} - {self.autor}"


class Ejemplar(models.Model):
    libro = models.ForeignKey(Libro, on_delete=models.CASCADE, related_name="ejemplares")
    codigo = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    estado = models.CharField(max_length=10, choices=[("nuevo", "Nuevo"), ("usado", "Usado")])
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    disponible = models.BooleanField(default=True)
    agotado = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.codigo} - {self.libro.titulo} ({self.estado})"

class MetodoPago(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='metodos_pago')
    numero_tarjeta = models.CharField(max_length=16)
    nombre_titular = models.CharField(max_length=100)
    vencimiento = models.DateField()
    cvv = models.CharField(max_length=4)
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"**** **** **** {self.numero_tarjeta[-4:]} ({self.cliente.email})"


class Direccion(models.Model):
    cliente = models.ForeignKey('Cliente', on_delete=models.CASCADE, related_name='direcciones')
    detalle = models.CharField(max_length=255)  # Calle, número, apartamento
    pais = models.CharField(max_length=100)
    departamento = models.CharField(max_length=100)
    ciudad = models.CharField(max_length=100)
    codigo_postal = models.CharField(max_length=20)
    activo = models.BooleanField(default=True)  # Para borrado lógico
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.detalle}, {self.ciudad}, {self.pais} ({self.cliente.email})"


class Carrito(models.Model):
    cliente = models.OneToOneField('Cliente', on_delete=models.CASCADE, related_name='carrito')
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Carrito de {self.cliente.email}"

class CarritoItem(models.Model):
    carrito = models.ForeignKey('Carrito', on_delete=models.CASCADE, related_name='items')
    ejemplar = models.ForeignKey('Ejemplar', on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    agregado = models.DateTimeField(default=timezone.now)

    def subtotal(self):
        return self.ejemplar.precio * self.cantidad

    def __str__(self):
        return f"{self.cantidad} x {self.ejemplar.libro.titulo} ({self.ejemplar.codigo})"

class Pedido(models.Model):
    ESTADOS = [
        ('EN PREPARACION', 'En preparación'),
        ('ENVIADO', 'Enviado'),
        ('ENTREGADO', 'Entregado'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADOS, default='EN PREPARACION')
    cliente = models.ForeignKey('Cliente', on_delete=models.CASCADE, related_name='pedidos')
    direccion = models.ForeignKey('Direccion', on_delete=models.SET_NULL, null=True)
    metodo_pago = models.ForeignKey('MetodoPago', on_delete=models.SET_NULL, null=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_creacion = models.DateTimeField(default=timezone.now)  # ✅ Aquí está el campo

    def __str__(self):
        return f"Pedido #{self.id} - {self.cliente.email}"

class PedidoItem(models.Model):
    pedido = models.ForeignKey('Pedido', on_delete=models.CASCADE, related_name='items')
    ejemplar = models.ForeignKey('Ejemplar', on_delete=models.SET_NULL, null=True)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f"{self.cantidad} x {self.ejemplar.libro.titulo if self.ejemplar else 'Desconocido'}"


class Reserva(models.Model):
    cliente = models.ForeignKey('Cliente', on_delete=models.CASCADE, related_name='reservas_activas')
    ejemplar = models.ForeignKey('Ejemplar', on_delete=models.CASCADE, related_name='reservas')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateTimeField()
    activa = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Si es nueva reserva, definir expiración a 24 horas
        if not self.id:
            self.fecha_expiracion = timezone.now() + timedelta(hours=24)
            # Marcar el ejemplar como no disponible
            self.ejemplar.disponible = False
            self.ejemplar.save()
        super().save(*args, **kwargs)

    def cancelar(self):
        # Liberar el ejemplar y desactivar reserva
        self.activa = False
        self.ejemplar.disponible = True
        self.ejemplar.save()
        self.save()

    def verificar_expiracion(self):
        if self.activa and timezone.now() >= self.fecha_expiracion:
            self.cancelar()

    def __str__(self):
        return f"Reserva de {self.ejemplar.libro.titulo} por {self.cliente.email}"


class Devolucion(models.Model):
    CAUSAS = [
        ('mal_estado', 'Producto en mal estado'),
        ('no_expectativas', 'No llenó las expectativas'),
        ('pedido_tarde', 'El pedido llegó tarde'),
    ]

    cliente = models.ForeignKey('Cliente', on_delete=models.CASCADE, related_name='devoluciones')
    ejemplar = models.ForeignKey('Ejemplar', on_delete=models.CASCADE, related_name='devoluciones')
    causa = models.CharField(max_length=50, choices=CAUSAS)
    motivo_ampliado = models.TextField(blank=True)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    codigo_qr = models.ImageField(upload_to='qrs/', blank=True)

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)

        if creating and not self.codigo_qr:
            qr_content = (
                f"Devolución #{self.id}\n"
                f"Cliente: {self.cliente.email}\n"
                f"Libro: {self.ejemplar.libro.titulo}\n"
                f"Fecha: {self.fecha_solicitud.strftime('%Y-%m-%d %H:%M')}"
            )
            qr_image = qrcode.make(qr_content)

            buffer = BytesIO()
            qr_image.save(buffer)

            # Asegura que el nombre de archivo no tenga saltos de línea o espacios
            filename = f"qr_devolucion_{self.id}.png".replace('\n', '').replace('\r', '').strip()

            file_content = ContentFile(buffer.getvalue())
            self.codigo_qr.save(filename, file_content, save=False)

            super().save(update_fields=["codigo_qr"])

    def __str__(self):
        return f"Devolución de {self.ejemplar.libro.titulo} ({self.cliente.email})"


class Noticia(models.Model):
    libro = models.ForeignKey('Libro', on_delete=models.CASCADE, related_name='noticias')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Noticia: {self.libro.titulo} ({self.fecha_creacion.strftime('%Y-%m-%d')})"


class Mensaje(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    contenido = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    es_admin = models.BooleanField(default=False)

    def __str__(self):
        return f"Mensaje de {self.cliente.email}: {self.contenido[:30]}"


class RespuestaMensaje(models.Model):
    mensaje = models.ForeignKey(Mensaje, on_delete=models.CASCADE, related_name='respuestas')
    administrador = models.ForeignKey(Administrador, on_delete=models.CASCADE)
    contenido = models.TextField()
    fecha_respuesta = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Respuesta de {self.administrador.email} al mensaje {self.mensaje.id}"
