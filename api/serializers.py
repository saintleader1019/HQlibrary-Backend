from rest_framework import serializers
from .models import (
    Usuario, Cliente, Administrador, 
    Libro, Ejemplar, Carrito, 
    CarritoItem, MetodoPago, Direccion, 
    Reserva, Devolucion, Noticia,
    Mensaje, RespuestaMensaje,
    PedidoItem, Pedido
)
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str

User = get_user_model()

class UsuarioSerializer(serializers.ModelSerializer):
    cc = serializers.SerializerMethodField()
    fecha_nacimiento = serializers.SerializerMethodField()
    direccion = serializers.SerializerMethodField()
    genero = serializers.SerializerMethodField()
    preferencias_literarias = serializers.SerializerMethodField()
    recibir_noticias = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = (
            'id', 'email', 'nombre', 'apellido',
            'cc', 'genero', 'direccion', 'fecha_nacimiento',
            'preferencias_literarias', 'recibir_noticias'
        )
        read_only_fields = ('id', 'email')

    def get_cc(self, obj):
        return getattr(obj, 'cliente', None) and obj.cliente.cc or None

    def get_fecha_nacimiento(self, obj):
        return getattr(obj, 'cliente', None) and obj.cliente.fecha_nacimiento or None

    def get_direccion(self, obj):
        return getattr(obj, 'cliente', None) and obj.cliente.direccion or None

    def get_genero(self, obj):
        return getattr(obj, 'cliente', None) and obj.cliente.genero or None

    def get_preferencias_literarias(self, obj):
        return getattr(obj, 'cliente', None) and obj.cliente.preferencias_literarias or None
    
    def get_recibir_noticias(self, obj):
        return getattr(obj, 'cliente', None) and obj.cliente.recibir_noticias or False
    
class EditarClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = (
            'nombre', 'apellido', 'cc',
            'fecha_nacimiento',
            'genero',
        )

class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        exclude = ('password', 'last_login', 'is_superuser', 'groups', 'user_permissions')
        read_only_fields = ('email', 'cc', 'fecha_nacimiento')


class AdministradorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Administrador
        exclude = ('password', 'last_login', 'is_superuser', 'groups', 'user_permissions')
        read_only_fields = ('email',)


class RegistroClienteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    recibir_noticias = serializers.BooleanField(default=False)  # 👈 nuevo campo

    class Meta:
        model = Cliente
        fields = ('email', 'password', 'nombre', 'apellido', 'cc', 'fecha_nacimiento', 'genero', 'recibir_noticias')

    def create(self, validated_data):
        password = validated_data.pop('password')
        recibir_noticias = validated_data.pop('recibir_noticias', False)  # 👈 Extraerlo manualmente

        cliente = Cliente(**validated_data)
        cliente.recibir_noticias = recibir_noticias  # 👈 Asignarlo manualmente
        cliente.set_password(password)
        cliente.save()
        return cliente


class RegistroAdministradorSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Administrador
        fields = ('email', 'password')

    def create(self, validated_data):
        password = validated_data.pop('password')
        admin = Administrador(**validated_data)
        admin.set_password(password)
        admin.is_staff = True
        admin.is_superuser = False
        admin.save()
        return admin


class RequestResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("No existe una cuenta con ese correo.")
        self.context['user'] = user
        return value

    @property
    def validated_data(self):
        data = super().validated_data
        data['user'] = self.context['user']
        return data


class ConfirmResetSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        try:
            uid = force_str(urlsafe_base64_decode(data['uid']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({'uid': 'Token o usuario inválido.'})

        if not default_token_generator.check_token(user, data['token']):
            raise serializers.ValidationError({'token': 'Token inválido o expirado.'})

        data['user'] = user
        return data


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        user = authenticate(username=email, password=password)

        if user is None:
            raise serializers.ValidationError("Credenciales incorrectas.")

        data['user'] = user
        return data

class LibroSerializer(serializers.ModelSerializer):
    ejemplares = serializers.SerializerMethodField()

    class Meta:
        model = Libro
        fields = [
            'id', 'titulo', 'autor', 'anio_publicacion', 'genero',
            'numero_paginas', 'editorial', 'issn', 'idioma',
            'fecha_publicacion', 'categoria', 'imagen', 'destacado', 'descripcion',
            'ejemplares'
        ]

    def get_ejemplares(self, obj):
        disponibles = obj.ejemplares.filter(disponible=True, agotado=False)
        if not disponibles.exists():
            # Opción 1: devolver al menos uno aunque esté agotado
            disponibles = obj.ejemplares.all()[:1]
        return EjemplarSerializer(disponibles, many=True).data

class EjemplarSerializer(serializers.ModelSerializer):
    libro = serializers.SerializerMethodField()

    class Meta:
        model = Ejemplar
        fields = ['id', 'codigo', 'estado', 'precio', 'disponible', 'agotado', 'libro']
        read_only_fields = ['id', 'codigo']

    def get_libro(self, obj):
        return {
            "id": obj.libro.id,
            "titulo": obj.libro.titulo,
        }

class LibroDetalleSerializer(serializers.ModelSerializer):
    ejemplares = serializers.SerializerMethodField()

    class Meta:
        model = Libro
        fields = [
            'id', 'titulo', 'autor', 'anio_publicacion', 'genero',
            'numero_paginas', 'editorial', 'issn', 'idioma',
            'fecha_publicacion', 'categoria', 'imagen', 'destacado', 'descripcion',
            'ejemplares'
        ]

    def get_ejemplares(self, obj):
        disponibles = obj.ejemplares.filter(disponible=True, agotado=False)
        return EjemplarSerializer(disponibles, many=True).data


class MetodoPagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetodoPago
        exclude = ['cliente']


class DireccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Direccion
        fields = ['id', 'detalle', 'pais', 'departamento', 'ciudad', 'codigo_postal', 'activo']
        read_only_fields = ['id', 'activo']

class ReservaSerializer(serializers.ModelSerializer):
    ejemplar = EjemplarSerializer(read_only=True)
    ejemplar_id = serializers.PrimaryKeyRelatedField(queryset=Ejemplar.objects.filter(disponible=True), source='ejemplar', write_only=True)

    class Meta:
        model = Reserva
        fields = ['id', 'cliente', 'ejemplar', 'ejemplar_id', 'fecha_creacion', 'fecha_expiracion', 'activa']
        read_only_fields = ['id', 'cliente', 'fecha_creacion', 'fecha_expiracion', 'activa']


class DevolucionSerializer(serializers.ModelSerializer):
    ejemplar = EjemplarSerializer(read_only=True)
    ejemplar_id = serializers.PrimaryKeyRelatedField(queryset=Ejemplar.objects.all(), source='ejemplar', write_only=True)
    codigo_qr_url = serializers.SerializerMethodField()

    class Meta:
        model = Devolucion
        fields = ['id', 'cliente', 'ejemplar', 'ejemplar_id', 'causa', 'motivo_ampliado', 'fecha_solicitud', 'codigo_qr_url']
        read_only_fields = ['id', 'cliente', 'fecha_solicitud', 'codigo_qr_url']

    def get_codigo_qr_url(self, obj):
        request = self.context.get('request')
        if obj.codigo_qr and hasattr(obj.codigo_qr, 'url') and request:
            return request.build_absolute_uri(obj.codigo_qr.url)
        return None


class NoticiaSerializer(serializers.ModelSerializer):
    titulo = serializers.CharField(source='libro.titulo', read_only=True)
    autor = serializers.CharField(source='libro.autor', read_only=True)
    genero = serializers.CharField(source='libro.genero', read_only=True)

    class Meta:
        model = Noticia
        fields = ['id', 'titulo', 'autor', 'genero', 'fecha_creacion']


class RespuestaMensajeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RespuestaMensaje
        fields = ['id', 'contenido', 'fecha_respuesta']

class MensajeSerializer(serializers.ModelSerializer):
    respuestas = RespuestaMensajeSerializer(many=True, read_only=True)
    cliente = serializers.SerializerMethodField()  # 👈 reemplaza el id simple por datos útiles

    class Meta:
        model = Mensaje
        fields = ['id', 'cliente', 'contenido', 'fecha_creacion', 'es_admin', 'respuestas']

    def get_cliente(self, obj):
        return {
            "id": obj.cliente.id,
            "nombre": obj.cliente.nombre,
            "apellido": obj.cliente.apellido,
            "email": obj.cliente.email
        }


class LibroMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Libro
        fields = ['id', 'titulo', 'imagen', 'autor']

class EjemplarCarritoSerializer(serializers.ModelSerializer):
    libro = LibroMiniSerializer(read_only=True)

    class Meta:
        model = Ejemplar
        fields = ['id', 'estado', 'precio', 'libro']

class CarritoItemSerializer(serializers.ModelSerializer):
    ejemplar = EjemplarCarritoSerializer(read_only=True)
    ejemplar_id = serializers.PrimaryKeyRelatedField(queryset=Ejemplar.objects.all(), source='ejemplar', write_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CarritoItem
        fields = ['id', 'ejemplar', 'ejemplar_id', 'cantidad', 'agregado', 'subtotal']
        read_only_fields = ['id', 'agregado', 'subtotal']

    def get_subtotal(self, obj):
        return obj.subtotal()        
    

class CarritoSerializer(serializers.ModelSerializer):
    items = CarritoItemSerializer(many=True, read_only=True)

    class Meta:
        model = Carrito
        fields = ['id', 'cliente', 'creado', 'actualizado', 'items']
        read_only_fields = ['id', 'cliente', 'creado', 'actualizado', 'items']

class PedidoItemSerializer(serializers.ModelSerializer):
    ejemplar_id = serializers.IntegerField(source='ejemplar.id', read_only=True)
    titulo = serializers.SerializerMethodField()
    autor = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    estado_ejemplar = serializers.SerializerMethodField()
    codigo = serializers.SerializerMethodField()
    devuelto = serializers.SerializerMethodField()

    class Meta:
        model = PedidoItem
        fields = ['ejemplar_id', 'titulo', 'autor', 'codigo', 'estado_ejemplar', 'cantidad', 'precio_unitario', 'subtotal', 'devuelto']

    def get_titulo(self, obj):
        return obj.ejemplar.libro.titulo if obj.ejemplar and obj.ejemplar.libro else 'Desconocido'

    def get_autor(self, obj):
        return obj.ejemplar.libro.autor if obj.ejemplar and obj.ejemplar.libro else 'Desconocido'

    def get_estado_ejemplar(self, obj):
        return obj.ejemplar.estado if obj.ejemplar else 'Desconocido'

    def get_codigo(self, obj):
        return obj.ejemplar.codigo if obj.ejemplar else '---'

    def get_subtotal(self, obj):
        return obj.subtotal()
    
    def get_devuelto(self, obj):
        return obj.ejemplar.devoluciones.exists()

class PedidoSerializer(serializers.ModelSerializer):
    resumen = PedidoItemSerializer(source='items', many=True)
    estado = serializers.SerializerMethodField()

    class Meta:
        model = Pedido
        fields = ['id', 'fecha_creacion', 'estado', 'total', 'resumen']

    def get_estado(self, obj):
        return "Procesado"