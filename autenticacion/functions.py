# -*- coding: utf-8 -*-
"""
Fichero

Descripción

@Empresa			: Proconsi S.L.
@Programador        : Alicia Merayo
@Fecha			    : 07/04/2025
@Fecha ult.modif.   : 07/04/2025 - Alicia Merayo
@Aplicación		    : superset
"""

import os
import httpx
from inputs import LoginRequest, GuestTokenRequest
import json
import requests

# Host interno de Superset dentro de la red Docker de Arsenio.
# Parametrizable por entorno (SUPERSET_BASE_URL en el docker-compose) para no
# depender del nombre del contenedor. Debe empezar por "http://" (mas abajo se
# usa BASE_URL[7:] para construir la cabecera Host).
BASE_URL = os.environ.get("SUPERSET_BASE_URL", "http://superset_pro-app:8088")

with open("keys.json") as f:
    keys = json.load(f)

async def get_guest_token(request: GuestTokenRequest):

    """
    Función para obtener el token de invitado para un dashboard embebido en Superset. Se
    comprueba primero que el usuario y contraseña son correctos, y luego se obtiene el
    token CSRF del usuario.

    Se obtiene el id interno del usuario y sus roles: para esto es necesario pasar el
    cliente de httpx con el que se obtuvo el csrf token porque es necesaria la cookie
    de sesión.

    Después se comprueba que el dashboard embebido existe y que
    el usuario tiene acceso a él. Para obtener el dashboard con su id interno hay que
    usar requests en vez de httpx porque no se puede pasar la cookie de sesión para
    esa petición.

    Finalmente, se obtiene el token de invitado. Para ello es necesaria la cookie de
    sesión del superusuario y el token CSRF del supertoken, por lo que es necesario usar
    de nuevo httpx.
    """
    # primero hay que comprobar que el usuario y contraseña son correctos
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response_login = await check_access(LoginRequest(username=request.username, password=request.password, provider="db", refresh=True), client)
        if not "access_token" in response_login:
            raise ValueError("Usuario o contraseña incorrectos")
        else:
            # se recoge el token del usuario que quiere embeber el panel
            token_acceso_usuario = response_login["access_token"]
            # se obtiene el token csrf para el usuario
            (response_csrf_usuario, headers_csrf_usuario) = await check_csrf(token_acceso_usuario, client)
            if not "result" in response_csrf_usuario:
                raise RuntimeError("Error al obtener el token CSRF del usuario")
            else:
                # obtenemos la cookie cifrada del usuario
                cookie_cifrada_usuario_aux = await get_cookie_from_login(request.username, request.password, response_csrf_usuario["result"], client)
                if not cookie_cifrada_usuario_aux:
                    raise RuntimeError("Error al obtener la cookie de sesión")

                # se obtiene la informacion del usuario
                response_info_usuario = await check_user_info(client)
                if not "result" in response_info_usuario:
                    raise RuntimeError("Error al obtener la información del usuario")
                else:
                    # obtenemos los roles del usuario
                    response_roles_usuario = await check_user_roles(client)
                    if not "result" in response_roles_usuario:
                        raise RuntimeError("Error al obtener los roles del usuario")
                    else:
                        async with httpx.AsyncClient(follow_redirects=True) as client2:
                            response_token_autenticacion = await check_access(LoginRequest(username=keys["conexion_token"]["username"], password=keys["conexion_token"]["password"], provider="db", refresh=True), client2)
                            supertoken_acceso = response_token_autenticacion["access_token"]
                            # ahora tenemos que comprobar que el id de dashboard embebido que han pasado se corresponde con un dashboard real
                            response_embedded = await check_embedded_dashboard_id(request.dashboard_id, supertoken_acceso, client2)
                            if not "result" in response_embedded:
                                raise ValueError("El identificador de panel enviado no es válido")
                            else:
                                # hay que obtener la informacion del dashboard
                                internal_dashboard_id = response_embedded["result"]["dashboard_id"]
                                # hay que obtener la informacion del dashboard que contiene que usuarios y que roles tienen acceso
                                response_dashboard = await check_dashboard_info(internal_dashboard_id, supertoken_acceso, client2)
                                if not "result" in response_dashboard:
                                    raise RuntimeError("Error al obtener la información del panel")
                                else:
                                    # comprobamos que el usuario tiene acceso al dashboard
                                    grant_guest_token = False
                                    usuarios_dashboard = response_dashboard["result"]["owners"]
                                    for usuario in usuarios_dashboard:
                                        if usuario["id"] == response_info_usuario["result"]["id"]:
                                            grant_guest_token = True
                                            break
                                    if not grant_guest_token:
                                        # si el usuario no tiene acceso al dashboard, comprobamos si algun rol del usuario tiene acceso
                                        roles_dashboard = response_dashboard["result"]["roles"]
                                        for rol in roles_dashboard:
                                            for rol_usuario in response_roles_usuario["result"]["roles"]:
                                                if rol["name"] == rol_usuario:
                                                    grant_guest_token = True
                                                    break
                                            if grant_guest_token:
                                                break
                                    if not grant_guest_token:
                                        raise ValueError("El usuario no tiene permiso de acceso al panel ni por usuario ni por rol")
                                    else:
                                        csrf_token_supertoken, headers = await check_csrf(supertoken_acceso, client2)
                                        if not "result" in csrf_token_supertoken:
                                            raise RuntimeError("Error al obtener el token CSRF del administrador")
                                        response_guest_token = await obtain_guest_token(request.dashboard_id, supertoken_acceso, csrf_token_supertoken["result"], client2)
                                        if "result" in response_guest_token:
                                            raise RuntimeError("Error al obtener el token de invitado")
                                        else:
                                            return response_guest_token

async def get_cookie_from_login(username:str, password:str, token_csrf:str, client:httpx.AsyncClient):
    """
    Función para obtener la cookie cifrada del usuario a partir del nombre de usuario y
    contraseña. Se usa para obtener la cookie de sesión del usuario que se ha logueado.
    Emula un navegador web para obtener pleno acceso al crud a través de la api.
    """
    url = f"{BASE_URL}/login/"

    headers = {
        "Host": BASE_URL[7:],
        "Origin": BASE_URL,
        "Referer": BASE_URL+ "/login/?next="+ BASE_URL+"/swagger/v1",
        "User-Agent": "Mozilla/5.0(Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "X-CSRFToken": token_csrf
    }
    data = {
        "username": username,
        "password": password,
        "csrf_token": token_csrf
    }

    response = await client.post(url, headers=headers, data=data)
    response.raise_for_status()
    return response.headers["set-cookie"]

async def check_access(request: LoginRequest, client:httpx.AsyncClient):
    """
    Función para comprobar el acceso a la API de Superset. Se usa para obtener el token
    de acceso del usuario que se ha logueado.
    """
    url = f"{BASE_URL}/api/v1/security/login"
    headers = {
        "Content-Type": "application/json",
        "accept": "application/json"
    }
    json_data = {
        "username": request.username,
        "password": request.password,
        "provider": "db",
        "refresh": True
    }
    response = await client.post(url, headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()

async def check_embedded_dashboard_id(dashboard_id: str, access_token: str, client:httpx.AsyncClient):
    """
    Función para comprobar la información del dashboard embebido
    """
    url = f"{BASE_URL}/api/v1/embedded_dashboard/{dashboard_id}"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "accept": "application/json"
    }

    response = await client.get(url, headers = headers)
    response.raise_for_status()
    return response.json()

async def check_user_info(client:httpx.AsyncClient):
    """ Función para obtener la información interna del usuario logueado"""
    url = f"{BASE_URL}/api/v1/me/"
    headers = {
        "accept": "application/json",
    }

    response = await client.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


async def check_user_roles(client:httpx.AsyncClient):
    """ Función para obtener los roles del usuario logueado"""
    url = f"{BASE_URL}/api/v1/me/roles/"
    headers = {
        "accept": "application/json"
    }

    response = await client.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


async def check_dashboard_info(dashboard_id: str, access_token: str, client:httpx.AsyncClient):
    """ Función para obtener la información del dashboard mediante su id interno"""
    url = f"{BASE_URL}/api/v1/dashboard/{dashboard_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "accept": "application/json"
    }
    # se usa requests porque httpx da conflicto con las cookies almacenadas para obtener el dashboard
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

async def obtain_guest_token(embedded_dashboard_id, access_token, csrf_token:str,  client:httpx.AsyncClient):
    """ Función para obtener el token de invitado para un dashboard embebido"""
    url = f"{BASE_URL}/api/v1/security/guest_token"
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "X-CSRFToken": csrf_token
    }
    json_data = {
      "resources": [
        {
          "type": "dashboard",
          "id": embedded_dashboard_id
        }
      ],
      "rls": [],
      "user": {
        "username": "",
        "first_name": "",
        "last_name": ""
      }
    }

    response = await client.post(url, headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()

async def check_csrf(access_token: str, client:httpx.AsyncClient):
    """ Función para obtener el token CSRF del usuario logueado"""
    url = f"{BASE_URL}/api/v1/security/csrf_token/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    response = await client.get(url, headers=headers)
    response.raise_for_status()
    return response.json(), response.headers


