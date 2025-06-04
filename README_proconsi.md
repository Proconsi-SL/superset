# Readme para la instalación de Proconsi

Para que funcione, tras instalar la aplicación deben copiarse en la carpeta superset/static/assets/images los archivos de proconsi-assets/images

Es posible que debas copiarlos también en superset/superset-frontend/src/assets/images.

Si no funciona el login al instalarlo la primera vez, cambiar el valor por defecto de SESSION_COOKIE_SAMESITE a None según indica el comentario y volver a cambiarlo después de la instalación a su valor por defecto.


## Importante
Antes de desplegar cambiar la clave SECRET_KEY en docker/pythonpath_dev/superset_config.py por una clave nueva, y cambiar en autenticacion/keys.json la clave de user_conexion por otra nueva clave.
