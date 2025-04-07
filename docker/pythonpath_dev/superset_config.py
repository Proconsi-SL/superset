# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
# This file is included in the final Docker image and SHOULD be overridden when
# deploying the image to prod. Settings configured here are intended for use in local
# development environments. Also note that superset_config_docker.py is imported
# as a final step as a means to override "defaults" configured here
#
import logging
import os

from celery.schedules import crontab
from flask_caching.backends.filesystemcache import FileSystemCache

logger = logging.getLogger()

DATABASE_DIALECT = os.getenv("DATABASE_DIALECT")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_PORT = os.getenv("DATABASE_PORT")
DATABASE_DB = os.getenv("DATABASE_DB")

EXAMPLES_USER = os.getenv("EXAMPLES_USER")
EXAMPLES_PASSWORD = os.getenv("EXAMPLES_PASSWORD")
EXAMPLES_HOST = os.getenv("EXAMPLES_HOST")
EXAMPLES_PORT = os.getenv("EXAMPLES_PORT")
EXAMPLES_DB = os.getenv("EXAMPLES_DB")

# The SQLAlchemy connection string.
SQLALCHEMY_DATABASE_URI = (
    f"{DATABASE_DIALECT}://"
    f"{DATABASE_USER}:{DATABASE_PASSWORD}@"
    f"{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_DB}"
)

SQLALCHEMY_EXAMPLES_URI = (
    f"{DATABASE_DIALECT}://"
    f"{EXAMPLES_USER}:{EXAMPLES_PASSWORD}@"
    f"{EXAMPLES_HOST}:{EXAMPLES_PORT}/{EXAMPLES_DB}"
)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_CELERY_DB = os.getenv("REDIS_CELERY_DB", "0")
REDIS_RESULTS_DB = os.getenv("REDIS_RESULTS_DB", "1")

RESULTS_BACKEND = FileSystemCache("/app/superset_home/sqllab")

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_DB": REDIS_RESULTS_DB,
}
DATA_CACHE_CONFIG = CACHE_CONFIG


class CeleryConfig:
    broker_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CELERY_DB}"
    imports = (
        "superset.sql_lab",
        "superset.tasks.scheduler",
        "superset.tasks.thumbnails",
        "superset.tasks.cache",
    )
    result_backend = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_RESULTS_DB}"
    worker_prefetch_multiplier = 1
    task_acks_late = False
    beat_schedule = {
        "reports.scheduler": {
            "task": "reports.scheduler",
            "schedule": crontab(minute="*", hour="*"),
        },
        "reports.prune_log": {
            "task": "reports.prune_log",
            "schedule": crontab(minute=10, hour=0),
        },
    }


CELERY_CONFIG = CeleryConfig

FEATURE_FLAGS = { "ALERT_REPORTS": True,}

ALERT_REPORTS_NOTIFICATION_DRY_RUN = True
WEBDRIVER_BASEURL = "http://superset_app:8088/"  # When using docker compose baseurl should be http://superset_app:8088/
# The base URL for the email report hyperlinks.
WEBDRIVER_BASEURL_USER_FRIENDLY = WEBDRIVER_BASEURL
SQLLAB_CTAS_NO_LIMIT = True

#
# Optionally import superset_config_docker.py (which will have been included on
# the PYTHONPATH) in order to allow for local settings to be overridden
#
try:
    import superset_config_docker
    from superset_config_docker import *  # noqa

    logger.info(
        f"Loaded your Docker configuration at " f"[{superset_config_docker.__file__}]"
    )
except ImportError:
    logger.info("Using default Docker config...")
    
    

#### Cambios necesarios para embeber paneles
WTF_CSRF_ENABLED = True

GUEST_ROLE_NAME = "conexion_token"
GUEST_TOKEN_JWT_SECRET = "80iyQjAC1f"
GUEST_TOKEN_JWT_ALGO = "HS256"
GUEST_TOKEN_HEADER_NAME = "X-GuestToken"
GUEST_TOKEN_JWT_EXP_SECONDS = 300  # 5 minutes

OVERRIDE_HTTP_HEADERS = {'X-Frame-Options': 'ALLOWALL'}
TALISMAN_ENABLED = False

FEATURE_FLAGS = {"ALERT_REPORTS": True, "EMBEDDED_SUPERSET": True, "ENABLE_TEMPLATE_PROCESSING": True,}


SESSION_COOKIE_SECURE = True

ENABLE_CORS = True
CORS_OPTIONS = {
'supports_credentials': True
#'origins': ['"https://localhost:8088"']
}

FAB_ADD_SECURITY_API = True
##### Fin de cambios necesarios para embeber paneles

# produccion
SECRET_KEY="80iyQjAC1f"


"""
class LoginPrefixMiddleware(object):


    def __init__(self, app):
        self.app = app


    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")

        if path.startswith("/superset/login"):
            environ["PATH_INFO"] = path.replace("/superset", "", 1)
        return self.app(environ, start_response)


ADDITIONAL_MIDDLEWARE = [LoginPrefixMiddleware]



ROW_LEVEL_SECURITY= True
RLS_IN_SQLLAB = True
"""

# autenticacion api

# import jwt  # PyJWT
# from flask import request
# from superset.security.manager import SupersetSecurityManager
# from werkzeug.exceptions import Unauthorized
#
# AUTH_TYPE = 'jwt'
# AUTH_JWT_EXPIRATION_TIME = 3600
# ENABLE_JWT_AUTH = True
# JWT_SECRET_KEY = "80iyQjAC1f"  # Reemplazalo por el usado en Superset
# JWT_ALGORITHM = "HS256"
#
# class CustomJWTAuthSecurityManager(SupersetSecurityManager):
#     def get_user(self):
#         auth_header = request.headers.get("Authorization", "")
#         print(auth_header)
#         if not auth_header or not auth_header.startswith("Bearer "):
#             return super().get_user()
#
#         token = auth_header.split(" ")[1].strip()
#         print(token)
#
#         try:
#             decoded = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
#             print(decoded)
#             user_id = decoded.get("sub")
#             print(user_id)
#             if not user_id:
#                 raise Unauthorized("El token no contiene 'sub'")
#
#             user = self.get_user_by_id(user_id)
#             print(user)
#             if not user:
#                 raise Unauthorized(f"Usuario con ID {user_id} no encontrado")
#
#             # Esta función es lo que Flask AppBuilder espera internamente
#             self._set_user(user)
#
#             return user
#
#         except Exception as ex:
#             raise Unauthorized(f"Token inválido: {ex}")
#
# CUSTOM_SECURITY_MANAGER = CustomJWTAuthSecurityManager
# # #FAB_SECURITY_MANAGER_CLASS = CustomJWTAuthSecurityManager

#For logging
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False
