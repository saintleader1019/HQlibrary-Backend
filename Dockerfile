# Usa una imagen base de Python
FROM python:3.12-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y netcat-openbsd
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config


# Establece el directorio de trabajo
WORKDIR /app

# Copia el archivo de requisitos (si lo tienes)
COPY requirements.txt /app/

# Instala las dependencias
RUN pip install -r requirements.txt

# Copia el resto del código de la aplicación
COPY . /app/

# Expone el puerto 8000
EXPOSE 8000

# Comando para correr la aplicación
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
