FROM python:3.12

RUN apt-get update && apt-get install -y supervisor && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# NOTA DE LAYOUT (Arsenio):
#   - Este Dockerfile vive en la RAIZ del deploy: deploys/superset_pro/auth.Dockerfile
#   - El build context es la raiz del deploy (context: . en el compose).
#   - El codigo del microservicio se despliega como artifact "auth", que Arsenio
#     extrae en deploys/superset_pro/auth/  (en el repo la fuente esta en autenticacion/,
#     el script dev/tools/build_deploy.py la empaqueta hacia el artifact "auth").
COPY auth/requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

COPY auth /app

CMD ["/usr/bin/supervisord", "-c", "/app/supervisord.conf"]
