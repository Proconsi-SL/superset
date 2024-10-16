# Uso de las peticiones 
Primero hay que hacer la petición html de login_request.bru. Devolverá un json con dos tokens, hay que copiar el que viene en "access_token" y ponerlo en "auth" en la petición html de guest_token_login.bru. Cuidado, que en esta segunda petición también hay que poner el dashboard id que se corresponda con el que se quiere embeber.

Al realizar la segunda petición obtendremos el guest token que hay que usar en el html, según las instrucciones del Readme de la carpeta superset/integracion_transparente.
