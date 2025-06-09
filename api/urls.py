from django.urls import path
from .views import (
    crear_libro,
    obtener_libro,
    actualizar_libro,
    eliminar_libro,
    listar_libros_admin,
    restaurar_libro,
    agregar_al_carrito,
    ver_carrito,
    eliminar_item_carrito,
    comprar_carrito,
    crear_reserva,
    foro_mensajes,
    listar_reservas_activas,
    listar_reservas_inactivas,
    listar_pedidos_cliente,
    cancelar_reserva,
    verificar_reservas_expiradas,
    solicitar_devolucion,
    catalogo_view,
    listar_mis_devoluciones,
    agregar_ejemplar,
    libros_disponibles,
    agregar_metodo_pago,
    listar_metodos_pago,
    eliminar_metodo_pago,
    listar_administradores,
    registrar_administrador,
    agregar_direccion,
    editar_direccion,
    eliminar_direccion,
    listar_direcciones,
    login_view,
    editar_perfil_view,
    registrar_cliente,
    logout_view,

    # verificar_correo,
    request_password_reset,
    confirm_password_reset,
    listar_mis_pedidos,
    ver_perfil_view,
    listar_ejemplares_agotados,
    listar_noticias,
    crear_mensaje,
    listar_mensajes,
    ver_mensaje_detalle,
    responder_mensaje,
    avanzar_estado_pedidos
)

from django.contrib.auth import views as auth_views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


urlpatterns = [

    path('login/', login_view, name='login'),
    path('editar_perfil/', editar_perfil_view, name='editar_perfil'),
    path('registrar_cliente/', registrar_cliente, name='registrar_cliente'),
    path('logout/', logout_view, name='logout'),
    #path('verify/<uidb64>/<token>/', verificar_correo, name='verificar_correo'),

    # URL para obtener el token (login)
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    
    # URL para refrescar el token
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # URL para restablecer la contraseña
    path('password-reset/', request_password_reset, name='password_reset'),
    path('password-reset-confirm/', confirm_password_reset, name='password_reset_confirm'),

    path('perfil/', ver_perfil_view, name='ver_perfil'),
    path('registrar_administrador/', registrar_administrador, name='registrar_administrador'),

    path('libros/crear/', crear_libro, name='crear_libro'),
    path('libros/<int:libro_id>/agregar_ejemplar/', agregar_ejemplar, name='agregar_ejemplar'),
    path('libros/disponibles/', libros_disponibles, name='libros_disponibles'),
    path('libros/<int:libro_id>/', obtener_libro, name='obtener_libro'),
    path('libros/<int:libro_id>/editar/', actualizar_libro, name='actualizar_libro'),
    path('libros/<int:libro_id>/eliminar/', eliminar_libro, name='eliminar_libro'),
    path("libros/admin/", listar_libros_admin, name="listar_libros_admin"),
    path("libros/<int:libro_id>/restaurar/", restaurar_libro, name="restaurar_libro"),
    path('ejemplares/agotados/', listar_ejemplares_agotados, name='listar_ejemplares_agotados'),

    # metodos de pago.
    path('metodos_pago/agregar/', agregar_metodo_pago, name='agregar_metodo_pago'),
    path('metodos_pago/', listar_metodos_pago, name='listar_metodos_pago'),
    path('metodos_pago/<int:metodo_id>/eliminar/', eliminar_metodo_pago, name='eliminar_metodo_pago'),

    # Admins
    path('administradores/', listar_administradores, name='listar_administradores'),
    path('administradores/registrar/', registrar_administrador, name='registrar_administrador'),

    # Direcciones
    path('direcciones/', listar_direcciones, name='listar_direcciones'),
    path('direcciones/agregar/', agregar_direccion, name='agregar_direccion'),
    path('direcciones/<int:direccion_id>/editar/', editar_direccion, name='editar_direccion'),
    path('direcciones/<int:direccion_id>/eliminar/', eliminar_direccion, name='eliminar_direccion'),

    # CARRITO DE COMPRAS
    path('carrito/agregar/', agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/', ver_carrito, name='ver_carrito'),
    path('carrito/item/<int:item_id>/eliminar/', eliminar_item_carrito, name='eliminar_item_carrito'),
    path('carrito/comprar/', comprar_carrito, name='comprar_carrito'),

    # PEDIDOS

    path('pedidos/', listar_mis_pedidos, name='listar_pedidos_cliente'),

    # RESERVAS DE LIBROS
    path('reservas/crear/', crear_reserva, name='crear_reserva'),
    path('reservas/activas/', listar_reservas_activas, name='listar_reservas_activas'),
    path('reservas/<int:reserva_id>/cancelar/', cancelar_reserva, name='cancelar_reserva'),
    path('reservas/verificar-expiradas/', verificar_reservas_expiradas, name='verificar_reservas_expiradas'),
    path('reservas/inactivas/', listar_reservas_inactivas, name='listar_reservas_inactivas'),

    # DEVOLUCIONES
    path('devoluciones/solicitar/', solicitar_devolucion, name='solicitar_devolucion'),
    path('devoluciones/mis/', listar_mis_devoluciones, name='listar_mis_devoluciones'),

    # NOTICIAS
    path('noticias/', listar_noticias, name='listar_noticias'),

    # MENSAJERÍA
    path('mensajes/crear/', crear_mensaje, name='crear_mensaje'),
    path("mensajes/", foro_mensajes, name="foro_mensajes"),         # GET
    path("mensajes/crear/", crear_mensaje, name="crear_mensaje"),   # POST
    path('mensajes/<int:mensaje_id>/', ver_mensaje_detalle, name='ver_mensaje_detalle'),
    path('mensajes/<int:mensaje_id>/responder/', responder_mensaje, name='responder_mensaje'),

    path('catalogo/', catalogo_view, name='catalogo'),
    path('pedidos/avanzar-estado/', avanzar_estado_pedidos, name='avanzar_estado_pedidos'),
]
