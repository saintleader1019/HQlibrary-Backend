# Usa una imagen base de Python
FROM python:3.12-slim

# Instalar dependencias del sistema necesarias para mysqlclient
RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config

# Evita la creación de archivos .pyc y permite logs visibles
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Establece el directorio de trabajo
WORKDIR /app

# Copia el archivo de requisitos e instala dependencias
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copia el resto del proyecto
COPY . /app/

# Expone el puerto por defecto de Django
EXPOSE 8000

# Comando para ejecutar el servidor de desarrollo
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
