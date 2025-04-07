FROM python:3.12

RUN apt-get update && apt-get install -y supervisor

WORKDIR /app

COPY ./autenticacion/requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# Copia el código fuente de la API
COPY ./autenticacion /app

# Copia el archivo supervisord.conf desde la raíz del proyecto
COPY ./autenticacion/supervisord.conf /app/supervisord.conf

# Verifica que esté
RUN ls -la /app


CMD ["/usr/bin/supervisord", "-c", "/app/supervisord.conf"]


