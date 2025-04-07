# API de autenticación para superset

Gestiona la autenticación de usuarios para obtener tokens de acceso para embeber paneles.

## Endpoint
### /guest_token
- **Método**: `POST`
- **Descripción**: Genera un token de acceso para un usuario, si este usuario tiene acceso al panel o bien por su usuario o bien por algún rol de ese usuario.
- **Parámetros del request**:
  - `username`: Nombre de usuario del usuario que se quiere autenticar.
  - `password`: Contraseña del usuario que se quiere autenticar.
  - `dashboard_id`: ID del dashboard embebido al que se quiere acceder.
  
  Es un body de tipo json. Ejemplo:
    ```json
    {
  "username":"user",
  "password":"pw",
  "dashboard_id":"dc93e198-b1ce-45dd-83fe-93ec2c7e7afe"
    }
    ```
- **Respuesta**:
  - `token`: Token de acceso generado para el usuario, si tenía permisos suficientes.
