from django.contrib.auth import logout
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import get_user_model


from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.hashers import make_password
import unicodedata

from .models import (
    Cliente, Administrador, Root, 
    Libro, MetodoPago, Direccion, 
    Carrito, CarritoItem, Ejemplar, 
    Reserva, Devolucion, Noticia,
    Mensaje, RespuestaMensaje, Pedido, 
    PedidoItem
)
from django.utils import timezone
from .serializers import (
    RegistroClienteSerializer,
    ClienteSerializer,
    PedidoSerializer,
    EditarClienteSerializer,
    AdministradorSerializer,
    UsuarioSerializer,
    RegistroAdministradorSerializer,
    RequestResetSerializer,
    ConfirmResetSerializer,
    LoginSerializer,
    LibroSerializer,
    EjemplarSerializer,
    LibroDetalleSerializer,
    MetodoPagoSerializer,
    DireccionSerializer,
    CarritoSerializer,
    CarritoItemSerializer,
    ReservaSerializer,
    DevolucionSerializer,
    NoticiaSerializer,
    MensajeSerializer,
    RespuestaMensajeSerializer,
)

User = get_user_model()

from rest_framework_simplejwt.tokens import RefreshToken

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        # 🔐 Determinar el rol con lógica robusta
        if user.is_superuser:
            rol = 'root'
        elif user.is_staff:
            rol = 'administrador'
        elif hasattr(user, 'cliente'):
            rol = 'cliente'
        else:
            rol = 'usuario'

        # 🎯 Construir respuesta base
        user_data = {
            "id": user.id,
            "email": user.email,
            "nombre": user.nombre,
            "apellido": user.apellido,
            "rol": rol,
            "recibir_noticias": getattr(user.cliente, 'recibir_noticias', False) if rol == 'cliente' else False
        }

        # ✅ Incluir recibir_noticias si es cliente
        if rol == "cliente":
            user_data["recibir_noticias"] = user.cliente.recibir_noticias

        return Response({
            "access": str(access),
            "refresh": str(refresh),
            "user": user_data
        }, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    logout(request)
    return Response({"message": "Sesión cerrada exitosamente."}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def registrar_cliente(request):
    serializer = RegistroClienteSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Cliente registrado exitosamente."}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def registrar_administrador(request):
    if not hasattr(request.user, "root"):
        return Response({'error': 'Solo el usuario Root puede ver esta información.'}, status=403)


    serializer = RegistroAdministradorSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Administrador creado correctamente."}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def editar_perfil_view(request):
    try:
        cliente = request.user.cliente
    except Cliente.DoesNotExist:
        return Response({"error": "Este usuario no es un cliente."}, status=400)

    serializer = EditarClienteSerializer(cliente, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Perfil actualizado correctamente."})
    return Response(serializer.errors, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ver_perfil_view(request):
    user = request.user

    # Si el usuario tiene datos adicionales como cliente, accede al modelo relacionado
    if hasattr(user, 'cliente'):
        instancia = user.cliente
    else:
        instancia = user

    serializer = UsuarioSerializer(instancia)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_mis_pedidos(request):
    try:
        cliente = Cliente.objects.get(id=request.user.id)
    except Cliente.DoesNotExist:
        return Response({'error': 'Solo los clientes pueden ver sus pedidos.'}, status=403)

    pedidos = Pedido.objects.filter(cliente=cliente).order_by('fecha_creacion')

    data = []

    for pedido in pedidos:
        resumen = []
        items = PedidoItem.objects.filter(pedido=pedido)

        for item in items:
            ejemplar = item.ejemplar
            libro = ejemplar.libro

            devolucion = Devolucion.objects.filter(cliente=cliente, ejemplar=ejemplar).first()
            codigo_qr_url = None

            if devolucion:
                serializer = DevolucionSerializer(devolucion, context={'request': request})
                codigo_qr_url = serializer.data.get('codigo_qr_url')

            resumen.append({
                "ejemplar_id": ejemplar.id,
                "titulo": libro.titulo,
                "autor": libro.autor,
                "cantidad": item.cantidad,
                "precio_unitario": item.precio_unitario,
                "subtotal": item.cantidad * item.precio_unitario,
                "estado_ejemplar": ejemplar.estado,
                "devuelto": bool(devolucion),
                "codigo_qr": codigo_qr_url
            })

        data.append({
            'id': pedido.id,
            'fecha_creacion': pedido.fecha_creacion.isoformat(),
            'estado': pedido.estado if hasattr(pedido, 'estado') else "Procesado",
            'total': pedido.total,
            'resumen': resumen
        })
    print("QR URL para ejemplar", ejemplar.id, "→", codigo_qr_url)
    return Response(data)

@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    serializer = RequestResetSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        return Response({
            'message': 'Token generado correctamente.',
            'uid': uid,
            'token': token
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def confirm_password_reset(request):
    serializer = ConfirmResetSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        new_password = serializer.validated_data['password']
        user.password = make_password(new_password)
        user.save()
        return Response({'message': 'La contraseña ha sido restablecida correctamente.'}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def normalizar(texto):
    if not texto:
        return ""
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')  # elimina tildes
    return texto.lower().strip()

@api_view(['GET'])
@permission_classes([AllowAny])
def catalogo_view(request):
    from rest_framework.pagination import PageNumberPagination
    import unicodedata

    genero = request.GET.get('genero')
    palabra = request.GET.get('q', "")
    titulo = request.GET.get('titulo', "")
    autor = request.GET.get('autor', "")
    precio_min = request.GET.get('precio_min')
    precio_max = request.GET.get('precio_max')
    destacado = request.GET.get('destacado')

    def normalizar(texto):
        if not texto:
            return ""
        texto = unicodedata.normalize('NFD', texto)
        texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
        return texto.lower().strip()

    def contiene(texto, subtexto):
        texto_normalizado = normalizar(texto)
        subtexto_normalizado = normalizar(subtexto)

        # Dividimos en palabras y verificamos si alguna empieza por el subtexto
        return any(palabra.startswith(subtexto_normalizado) for palabra in texto_normalizado.split())

    libros = Libro.objects.filter(activo=True).prefetch_related('ejemplares').order_by('id')
    libros = [libro for libro in libros if libro.ejemplares.filter(disponible=True, agotado=False).exists()]

    # Filtro por género
    if genero:
        genero_normalizado = normalizar(genero)
        libros = [libro for libro in libros if normalizar(libro.genero) == genero_normalizado]

    # Filtro por palabra general q (titulo o autor)
    if palabra:
        libros = [libro for libro in libros if contiene(libro.titulo, palabra) or contiene(libro.autor, palabra)]

    # Filtro por autor y/o título específicos
    if autor and titulo:
        libros = [libro for libro in libros if contiene(libro.titulo, titulo) and contiene(libro.autor, autor)]
    elif autor:
        libros = [libro for libro in libros if contiene(libro.autor, autor)]
    elif titulo:
        libros = [libro for libro in libros if contiene(libro.titulo, titulo)]

    # Filtros por precio
    if precio_min:
        try:
            precio_min = float(precio_min)
            libros = [libro for libro in libros if any(ej.precio >= precio_min for ej in libro.ejemplares.all())]
        except ValueError:
            pass

    if precio_max:
        try:
            precio_max = float(precio_max)
            libros = [libro for libro in libros if any(ej.precio <= precio_max for ej in libro.ejemplares.all())]
        except ValueError:
            pass

    # Filtro por destacados
    if destacado is not None:
        if destacado.lower() in ['true', '1']:
            libros = [libro for libro in libros if libro.destacado]
        elif destacado.lower() in ['false', '0']:
            libros = [libro for libro in libros if not libro.destacado]

    paginator = PageNumberPagination()
    paginator.page_size = int(request.GET.get('page_size', 10))
    result_page = paginator.paginate_queryset(libros, request)

    serializer = LibroSerializer(result_page, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_libro(request):
    serializer = LibroSerializer(data=request.data)
    if serializer.is_valid():
        libro = serializer.save()
        cantidad = int(request.data.get('cantidad_ejemplares', 1))
        precio = float(request.data.get('precio', 0))

        for _ in range(cantidad):
            Ejemplar.objects.create(
                libro=libro,
                precio=precio,
                disponible=True,
                agotado=False
            )
        return Response(LibroSerializer(libro).data, status=201)
    return Response(serializer.errors, status=400)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def agregar_ejemplar(request, libro_id):
    try:
        libro = Libro.objects.get(id=libro_id)
    except Libro.DoesNotExist:
        return Response({'error': 'Libro no encontrado'}, status=404)

    cantidad = int(request.data.get('cantidad', 1))
    precio = float(request.data.get('precio', 0))

    for _ in range(cantidad):
        Ejemplar.objects.create(
            libro=libro,
            precio=precio,
            estado=request.data.get("estado", "nuevo"),
            disponible=request.data.get("disponible", True),
            agotado=request.data.get("agotado", False)
        )
    return Response({'message': f'Se agregaron {cantidad} ejemplares'}, status=201)


@api_view(['GET'])
@permission_classes([AllowAny])  # o IsAuthenticated si quieres restringir
def obtener_libro(request, libro_id):
    try:
        libro = Libro.objects.prefetch_related('ejemplares').get(id=libro_id, activo=True)
    except Libro.DoesNotExist:
        return Response({'error': 'Libro no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    serializer = LibroDetalleSerializer(libro)
    return Response(serializer.data)



@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def actualizar_libro(request, libro_id):
    if not hasattr(request.user, "administrador"):
        return Response({'error': 'Solo los administradores pueden editar libros.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        libro = Libro.objects.get(id=libro_id)
    except Libro.DoesNotExist:
        return Response({'error': 'Libro no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    # Solo se actualizan los campos del libro, no los ejemplares
    serializer = LibroSerializer(libro, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_libro(request, libro_id):
    if not hasattr(request.user, "administrador"):
        return Response({'error': 'Solo los administradores pueden eliminar libros.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        libro = Libro.objects.get(id=libro_id)
    except Libro.DoesNotExist:
        return Response({'error': 'Libro no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    libro.activo = False
    libro.save()
    return Response({'message': 'Libro marcado como eliminado (inactivo).'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def libros_disponibles(request):
    categoria = request.GET.get('categoria')
    
    libros = Libro.objects.filter(destacado=True)

    if categoria:
        libros = libros.filter(categoria__icontains=categoria.strip())

    libros = libros.distinct()
    libros = [libro for libro in libros if libro.ejemplares.filter(disponible=True, agotado=False).exists()]

    serializer = LibroSerializer(libros, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def agregar_metodo_pago(request):
    try:
        cliente = Cliente.objects.get(id=request.user.id)
    except Cliente.DoesNotExist:
        return Response({'error': 'Solo los clientes pueden registrar métodos de pago.'}, status=status.HTTP_403_FORBIDDEN)

    serializer = MetodoPagoSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(cliente=cliente)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_metodos_pago(request):
    try:
        cliente = Cliente.objects.get(id=request.user.id)
    except Cliente.DoesNotExist:
        return Response({'error': 'Solo los clientes pueden ver sus métodos de pago.'}, status=status.HTTP_403_FORBIDDEN)

    metodos = MetodoPago.objects.filter(cliente=request.user, activo=True)
    serializer = MetodoPagoSerializer(metodos, many=True)
    return Response(serializer.data)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_metodo_pago(request, metodo_id):
    try:
        cliente = Cliente.objects.get(id=request.user.id)
    except Cliente.DoesNotExist:
        return Response({'error': 'Solo los clientes pueden eliminar métodos de pago.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        metodo = MetodoPago.objects.get(id=metodo_id, cliente=request.user)
        metodo.activo = False
        metodo.save()
        return Response({'message': 'Método de pago desactivado.'})
    except MetodoPago.DoesNotExist:
        return Response({'error': 'Método de pago no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_administradores(request):
    if not hasattr(request.user, "root"):
        return Response({'error': 'Solo el usuario Root puede ver esta información.'}, status=403)


    administradores = Administrador.objects.all()
    serializer = AdministradorSerializer(administradores, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_libros_admin(request):
    if not hasattr(request.user, "administrador"):
        return Response({'error': 'Solo los administradores pueden ver los libros.'}, status=status.HTTP_403_FORBIDDEN)

    activo = request.GET.get('activo')
    libros = Libro.objects.all()

    if activo is not None:
        if activo.lower() in ['true', '1']:
            libros = libros.filter(activo=True)
        elif activo.lower() in ['false', '0']:
            libros = libros.filter(activo=False)

    libros = libros.prefetch_related('ejemplares')
    serializer = LibroDetalleSerializer(libros, many=True)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def restaurar_libro(request, libro_id):
    if not hasattr(request.user, "administrador"):
        return Response({'error': 'Solo los administradores pueden restaurar libros.'}, status=403)
    try:
        libro = Libro.objects.get(id=libro_id)
        libro.activo = True
        libro.save()
        return Response({'message': 'Libro restaurado correctamente.'})
    except Libro.DoesNotExist:
        return Response({'error': 'Libro no encontrado.'}, status=404)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_direcciones(request):
    try:
        cliente = Cliente.objects.get(id=request.user.id)
    except Cliente.DoesNotExist:
        return Response({'error': 'Solo los clientes pueden ver sus direcciones.'}, status=status.HTTP_403_FORBIDDEN)

    direcciones = Direccion.objects.filter(cliente=cliente, activo=True)
    serializer = DireccionSerializer(direcciones, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def agregar_direccion(request):
    try:
        cliente = Cliente.objects.get(id=request.user.id)
    except Cliente.DoesNotExist:
        return Response({'error': 'Solo los clientes pueden agregar direcciones.'}, status=status.HTTP_403_FORBIDDEN)

    serializer = DireccionSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(cliente=cliente)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def editar_direccion(request, direccion_id):
    try:
        cliente = Cliente.objects.get(id=request.user.id)
    except Cliente.DoesNotExist:
        return Response({'error': 'Solo los clientes pueden editar direcciones.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        direccion = Direccion.objects.get(id=direccion_id, cliente=cliente, activo=True)
    except Direccion.DoesNotExist:
        return Response({'error': 'Dirección no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    serializer = DireccionSerializer(direccion, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_direccion(request, direccion_id):
    try:
        cliente = Cliente.objects.get(id=request.user.id)
    except Cliente.DoesNotExist:
        return Response({'error': 'Solo los clientes pueden eliminar direcciones.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        direccion = Direccion.objects.get(id=direccion_id, cliente=cliente, activo=True)
    except Direccion.DoesNotExist:
        return Response({'error': 'Dirección no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

    direccion.activo = False
    direccion.save()
    return Response({'message': 'Dirección eliminada correctamente.'})


# ========== VISTAS DEL CARRITO ==========

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def agregar_al_carrito(request):
    try:
        cliente = Cliente.objects.get(id=request.user.id)
    except Cliente.DoesNotExist:
        return Response({'error': 'Solo los clientes pueden agregar al carrito.'}, status=status.HTTP_403_FORBIDDEN)

    # Asegurarse de que el cliente tenga un carrito
    carrito, created = Carrito.objects.get_or_create(cliente=cliente)

    serializer = CarritoItemSerializer(data=request.data)
    if serializer.is_valid():
        ejemplar = serializer.validated_data['ejemplar']

        # Validar que el ejemplar esté disponible
        if not ejemplar.disponible or ejemplar.agotado:
            return Response({'error': 'Este ejemplar no está disponible.'}, status=status.HTTP_400_BAD_REQUEST)

        # Verificar que no esté ya agregado
        if CarritoItem.objects.filter(carrito=carrito, ejemplar=ejemplar).exists():
            return Response({'error': 'Este ejemplar ya está en tu carrito.'}, status=status.HTTP_400_BAD_REQUEST)

        CarritoItem.objects.create(
            carrito=carrito,
            ejemplar=ejemplar,
            cantidad=serializer.validated_data.get('cantidad', 1)
        )
        return Response({'message': 'Ejemplar agregado al carrito.'}, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ver_carrito(request):
    try:
        cliente = Cliente.objects.get(id=request.user.id)
        carrito = cliente.carrito
    except (Cliente.DoesNotExist, Carrito.DoesNotExist):
        return Response({'error': 'El carrito no existe.'}, status=status.HTTP_404_NOT_FOUND)

    serializer = CarritoSerializer(carrito)
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def eliminar_item_carrito(request, item_id):
    try:
        cliente = Cliente.objects.get(id=request.user.id)
        carrito = cliente.carrito
    except (Cliente.DoesNotExist, Carrito.DoesNotExist):
        return Response({'error': 'No tienes un carrito activo.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        item = CarritoItem.objects.get(id=item_id, carrito=carrito)
        item.delete()
        return Response({'message': 'Item eliminado del carrito.'}, status=status.HTTP_200_OK)
    except CarritoItem.DoesNotExist:
        return Response({'error': 'Item no encontrado en tu carrito.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def comprar_carrito(request):
    try:
        cliente = Cliente.objects.get(id=request.user.id)
        carrito = cliente.carrito
    except (Cliente.DoesNotExist, Carrito.DoesNotExist):
        return Response({'error': 'No tienes un carrito activo.'}, status=404)

    items = carrito.items.all()
    if not items.exists():
        return Response({'error': 'Tu carrito está vacío.'}, status=400)

    direccion_id = request.data.get('direccion_id')
    metodo_id = request.data.get('metodo_pago_id')

    if not direccion_id or not metodo_id:
        return Response({'error': 'Falta seleccionar dirección o método de pago.'}, status=400)

    if not cliente.direcciones.filter(id=direccion_id, activo=True).exists():
        return Response({'error': 'Dirección inválida.'}, status=400)

    if not cliente.metodos_pago.filter(id=metodo_id, activo=True).exists():
        return Response({'error': 'Método de pago inválido.'}, status=400)

    total = sum(item.subtotal() for item in items)

    # Crear pedido principal
    pedido = Pedido.objects.create(
        cliente=cliente,
        direccion_id=direccion_id,
        metodo_pago_id=metodo_id,
        total=total,
    )

    # Crear los items del pedido
    for item in items:
        PedidoItem.objects.create(
            pedido=pedido,
            ejemplar=item.ejemplar,
            cantidad=item.cantidad,
            precio_unitario=item.ejemplar.precio,
        )
        item.ejemplar.disponible = False
        item.ejemplar.save()

    # Vaciar carrito
    items.delete()

    ejemplares_codigos = [item.ejemplar.codigo.hex for item in carrito.items.all()]

    # Actualizar historial
    cliente.historial_compras.append({
        "total": str(total),
        "fecha": pedido.fecha_creacion.strftime("%Y-%m-%d %H:%M"),
        "direccion_id": direccion_id,
        "metodo_pago_id": metodo_id,
        "pedido_id": pedido.id,
        "ejemplares": ejemplares_codigos
    })
    cliente.save()

    return Response({
        'message': 'Compra realizada exitosamente.',
        'total': str(total),
        'pedido_id': pedido.id,
        'fecha': pedido.fecha_creacion.strftime("%Y-%m-%d %H:%M")
    }, status=200)


# ========== VISTAS DE RESERVAS ==========

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_reserva(request):
    try:
        cliente = Cliente.objects.get(id=request.user.id)
    except Cliente.DoesNotExist:
        return Response({'error': 'Solo los clientes pueden hacer reservas.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        ejemplar = Ejemplar.objects.get(id=request.data.get('ejemplar_id'), disponible=True)
    except Ejemplar.DoesNotExist:
        return Response({'error': 'Este ejemplar no está disponible.'}, status=status.HTTP_400_BAD_REQUEST)

    # Validar reservas activas del cliente
    reservas_activas = Reserva.objects.filter(cliente=cliente, activa=True)

    if reservas_activas.count() >= 5:
        return Response({'error': 'Solo puedes tener máximo 5 libros reservados.'}, status=status.HTTP_400_BAD_REQUEST)

    # Contar reservas activas del mismo libro por este cliente
    reservas_mismo_libro = reservas_activas.filter(ejemplar__libro=ejemplar.libro).count()
    if reservas_mismo_libro >= 3:
        return Response({'error': 'No puedes reservar más de 3 ejemplares del mismo libro.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = ReservaSerializer(data=request.data)
    if serializer.is_valid():
        reserva = serializer.save(cliente=cliente)
        return Response(ReservaSerializer(reserva).data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_reservas_activas(request):
    try:
        cliente = Cliente.objects.get(id=request.user.id)
    except Cliente.DoesNotExist:
        return Response({'error': 'Solo los clientes pueden ver reservas.'}, status=status.HTTP_403_FORBIDDEN)

    reservas = Reserva.objects.filter(cliente=cliente, activa=True)
    serializer = ReservaSerializer(reservas, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_reservas_inactivas(request):
    try:
        cliente = Cliente.objects.get(id=request.user.id)
    except Cliente.DoesNotExist:
        return Response({'error': 'Solo los clientes pueden ver reservas.'}, status=status.HTTP_403_FORBIDDEN)

    reservas = Reserva.objects.filter(cliente=cliente, activa=False)
    serializer = ReservaSerializer(reservas, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancelar_reserva(request, reserva_id):
    try:
        cliente = Cliente.objects.get(id=request.user.id)
    except Cliente.DoesNotExist:
        return Response({'error': 'Solo los clientes pueden cancelar reservas.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        reserva = Reserva.objects.get(id=reserva_id, cliente=cliente, activa=True)
    except Reserva.DoesNotExist:
        return Response({'error': 'Reserva no encontrada o ya cancelada.'}, status=status.HTTP_404_NOT_FOUND)

    reserva.cancelar()
    return Response({'message': 'Reserva cancelada exitosamente.'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verificar_reservas_expiradas(request):
    # Este endpoint sería llamado manualmente o por CRON en producción
    reservas = Reserva.objects.filter(activa=True)
    expiradas = 0

    for reserva in reservas:
        if timezone.now() >= reserva.fecha_expiracion:
            reserva.cancelar()
            expiradas += 1

    return Response({'message': f'{expiradas} reservas expiradas fueron liberadas.'}, status=status.HTTP_200_OK)


# ========== VISTAS DE DEVOLUCIONES ==========

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def solicitar_devolucion(request):
    try:
        cliente = Cliente.objects.get(id=request.user.id)
    except Cliente.DoesNotExist:
        return Response({'error': 'Solo los clientes pueden solicitar devoluciones.'}, status=status.HTTP_403_FORBIDDEN)

    ejemplar_id = request.data.get('ejemplar_id')
    if not ejemplar_id:
        return Response({'error': 'Debe proporcionar el ID del ejemplar a devolver.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        ejemplar = Ejemplar.objects.get(id=ejemplar_id)
    except Ejemplar.DoesNotExist:
        return Response({'error': 'Ejemplar no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    # Validar si la compra es reciente (menos de 8 días)
    historial = cliente.historial_compras
    compra_valida = False
    for compra in historial:
        for compra in historial:
            for compra in historial:
                if compra.get('fecha'):
                    try:
                        fecha_compra = timezone.datetime.strptime(compra['fecha'], "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        fecha_compra = timezone.datetime.strptime(compra['fecha'], "%Y-%m-%d %H:%M")
                    fecha_compra = timezone.make_aware(fecha_compra)

                    # Si solo tienes pedido_id pero no la lista de ejemplares:
                    if 'pedido_id' in compra and compra['pedido_id'] == ejemplar.pedidoitem_set.first().pedido.id:
                        if (timezone.now() - fecha_compra).days <= 8:
                            compra_valida = True
                            break

    if not compra_valida:
        return Response({'error': 'El tiempo para devolución ha expirado o no se encontró compra reciente.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = DevolucionSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        devolucion = serializer.save(cliente=cliente)
        return Response(DevolucionSerializer(devolucion).data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_mis_devoluciones(request):
    try:
        cliente = Cliente.objects.get(id=request.user.id)
    except Cliente.DoesNotExist:
        return Response({'error': 'Solo los clientes pueden ver sus devoluciones.'}, status=status.HTTP_403_FORBIDDEN)

    devoluciones = Devolucion.objects.filter(cliente=cliente)
    serializer = DevolucionSerializer(devoluciones, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_ejemplares_agotados(request):
    if not hasattr(request.user, "administrador"):
        return Response({'error': 'Solo los administradores pueden ver ejemplares agotados.'}, status=status.HTTP_403_FORBIDDEN)

    ejemplares = Ejemplar.objects.filter(agotado=True)
    serializer = EjemplarSerializer(ejemplares, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def listar_noticias(request):
    noticias = Noticia.objects.select_related('libro').order_by('-fecha_creacion')
    serializer = NoticiaSerializer(noticias, many=True)
    return Response(serializer.data)

# ========== VISTAS DE MENSAJERÍA ==========

# Cliente crea mensaje
User = get_user_model()

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_mensaje(request):
    try:
        cliente = Cliente.objects.get(pk=request.user.pk)
    except Cliente.DoesNotExist:
        return Response({'error': 'Solo los clientes pueden crear mensajes.'}, status=status.HTTP_403_FORBIDDEN)

    serializer = MensajeSerializer(data=request.data)
    if serializer.is_valid():
        mensaje = serializer.save(cliente=cliente)
        return Response(MensajeSerializer(mensaje).data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Admin lista todos los mensajes
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_mensajes(request):
    if not hasattr(request.user, "administrador"):
        return Response({'error': 'Solo los administradores pueden ver los mensajes.'}, status=status.HTTP_403_FORBIDDEN)

    mensajes = Mensaje.objects.all().order_by('-fecha_creacion')
    serializer = MensajeSerializer(mensajes, many=True)
    return Response(serializer.data)


# Ver detalle de un mensaje (cliente o admin)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ver_mensaje_detalle(request, mensaje_id):
    try:
        mensaje = Mensaje.objects.get(id=mensaje_id)
    except Mensaje.DoesNotExist:
        return Response({'error': 'Mensaje no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    # Clientes solo pueden ver sus propios mensajes
    if hasattr(request.user, "cliente") and mensaje.cliente != request.user:
        return Response({'error': 'No tienes permiso para ver este mensaje.'}, status=status.HTTP_403_FORBIDDEN)

    serializer = MensajeSerializer(mensaje)
    return Response(serializer.data)


# Admin responde un mensaje
from api.models import Administrador

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def responder_mensaje(request, mensaje_id):
    if not hasattr(request.user, "administrador"):
        return Response({'error': 'Solo los administradores pueden responder mensajes.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        mensaje = Mensaje.objects.get(id=mensaje_id)
    except Mensaje.DoesNotExist:
        return Response({'error': 'Mensaje no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        admin = Administrador.objects.get(pk=request.user.id)
    except Administrador.DoesNotExist:
        return Response({'error': 'Administrador no válido.'}, status=status.HTTP_403_FORBIDDEN)

    serializer = RespuestaMensajeSerializer(data=request.data)
    if serializer.is_valid():
        respuesta = serializer.save(administrador=admin, mensaje=mensaje)
        return Response(RespuestaMensajeSerializer(respuesta).data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def foro_mensajes(request):
    user = request.user

    # Crear mensaje (solo cliente)
    if request.method == 'POST':
        if not hasattr(user, 'cliente'):
            return Response({'error': 'Solo los clientes pueden crear mensajes.'}, status=403)
        
        serializer = MensajeSerializer(data=request.data)
        if serializer.is_valid():
            mensaje = serializer.save(cliente=user.cliente)
            return Response(MensajeSerializer(mensaje).data, status=201)
        return Response(serializer.errors, status=400)

    # Listar mensajes
    if hasattr(user, 'administrador'):
        mensajes = Mensaje.objects.all().order_by('-fecha_creacion')
    elif hasattr(user, 'cliente'):
        mensajes = Mensaje.objects.filter(cliente=user.cliente).order_by('-fecha_creacion')
    else:
        return Response({'error': 'No autorizado.'}, status=403)

    serializer = MensajeSerializer(mensajes, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def listar_pedidos_cliente(request):
    cliente = Cliente.objects.get(id=request.user.id)
    pedidos = Pedido.objects.filter(cliente=cliente).order_by('-fecha_creacion')
    serializer = PedidoSerializer(pedidos, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Opcional: solo admins pueden ejecutar
def avanzar_estado_pedidos(request):
    ahora = timezone.now()
    actualizados = []

    for pedido in Pedido.objects.all():
        segundos = (ahora - pedido.fecha_creacion).total_seconds()

        if pedido.estado == 'EN PREPARACION' and segundos >= 120:
            pedido.estado = 'ENVIADO'
            pedido.save()
            actualizados.append((pedido.id, 'ENVIADO'))
        elif pedido.estado == 'ENVIADO' and segundos >= 240:
            pedido.estado = 'ENTREGADO'
            pedido.save()
            actualizados.append((pedido.id, 'ENTREGADO'))

    return Response({
        "mensaje": "Actualización completada",
        "pedidos_actualizados": actualizados
    })