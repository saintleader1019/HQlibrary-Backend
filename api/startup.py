from api.models import Root

from django.db import connection

def table_exists(table_name):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s",
            [table_name]
        )
        return cursor.fetchone()[0] == 1

def create_default_root():
    if not table_exists("api_root"):
        return  # Evita error si aún no existe la tabla Root
    from .models import Root
    if not Root.objects.filter(email="root1@admin.com").exists():
        Root.objects.create_superuser(
            email="root1@admin.com",
            nombre="Mega",
            apellido="Raiz",
            password="root1234",
            is_staff=True,
            is_superuser=True,
            # rol="root"
        )