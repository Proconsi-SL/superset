import httpx
from inputs import LoginRequest, GuestTokenRequest
import json

BASE_URL = "http://superset_app:8088"  # Cambia esto por la URL real

with open("keys.json") as f:
    keys = json.load(f)

async def get_guest_token(request: GuestTokenRequest):

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
                        response_token_autenticacion = await check_access(LoginRequest(username=keys["conexion_token"]["username"], password=keys["conexion_token"]["password"], provider="db", refresh=True), client)
                        supertoken_acceso = response_token_autenticacion["access_token"]
                        # ahora tenemos que comprobar que el id de dashboard embebido que han pasado se corresponde con un dashboard real
                        response_embedded = await check_embedded_dashboard_id(request.dashboard_id, supertoken_acceso, client)
                        if not "result" in response_embedded:
                            raise ValueError("El identificador de panel que has enviado no es válido")
                        else:
                            # hay que obtener la informacion del dashboard
                            internal_dashboard_id = response_embedded["result"]["dashboard_id"]
                            # hay que obtener la informacion del dashboard que contiene que usuarios y que roles tienen acceso
                            response_dashboard = await check_dashboard_info(internal_dashboard_id, supertoken_acceso, client)
                            if not "result" in response_dashboard != 200:
                                raise RuntimeError("Error al obtener la información del dashboard")
                            else:
                                # comprobamos que el usuario tiene acceso al dashboard
                                grant_guest_token = False
                                usuarios_dashboard = response_roles_usuario["result"]["owners"]
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
                                    response_guest_token = await obtain_guest_token(GuestTokenRequest.dashboard_id, supertoken_acceso, client)
                                    if response_guest_token.status_code != 200:
                                        raise RuntimeError("Error al obtener el token de invitado")
                                    else:
                                        return response_guest_token

async def get_cookie_from_login(username:str, password:str, token_csrf:str, client:httpx.AsyncClient):
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
    url = f"{BASE_URL}/api/v1/embedded_dashboard/{dashboard_id}"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "accept": "application/json"
    }

    response = await client.get(url, headers = headers)
    response.raise_for_status()
    print(response.json())
    return response.json()

async def check_user_info(client:httpx.AsyncClient):
    url = f"{BASE_URL}/api/v1/me/"
    headers = {
        "accept": "application/json",
    }

    response = await client.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


async def check_user_roles(client:httpx.AsyncClient):
    url = f"{BASE_URL}/api/v1/me/roles/"
    headers = {
        "accept": "application/json"
    }

    response = await client.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


async def check_dashboard_info(dashboard_id: str, access_token: str, client:httpx.AsyncClient):
    url = f"{BASE_URL}/api/v1/dashboard/{dashboard_id}/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "accept": "application/json"
    }

    response = await client.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

async def obtain_guest_token(embedded_dashboard_id, access_token, client:httpx.AsyncClient):
    url = f"{BASE_URL}/api/v1/guest_token"
    headers = {
        "Authorization": f"Bearer {access_token}"
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

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=json_data)
        response.raise_for_status()
        return response.json()

async def check_csrf(access_token: str, client:httpx.AsyncClient):
    url = f"{BASE_URL}/api/v1/security/csrf_token/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    response = await client.get(url, headers=headers)
    response.raise_for_status()
    return response.json(), response.headers


