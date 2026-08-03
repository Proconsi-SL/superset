# dev/tools — tooling de despliegue Arsenio

Utilidades para desplegar en el servidor Arsenio (`smart.proconsi.com`, proyecto
`superset_pro`). **Esta carpeta SÍ se versiona.** El resto de `dev/` no
(`dev/docs/`, `dev/deployments/`, `dev/secrets/` están en `.gitignore`).

## build_deploy.py

Empaqueta el microservicio de autenticación (`autenticacion/` en el repo) como el
artifact `auth` de Arsenio y, opcionalmente, lo sube. **Nunca despliega solo.**

### Antes de nada: keys.json real

El `autenticacion/keys.json` del repo es un **placeholder**. El real (credenciales
del usuario de servicio de Superset que emite los guest tokens) debe estar en:

```
dev/secrets/keys.json      (gitignorado, nunca se commitea)
```

con la forma de `keys.json.example`.

### Construir (offline)

```bash
python dev/tools/build_deploy.py --version 1.0.0
```

Genera `dev/deployments/auth/auth-1.0.0.zip` + `auth-1.0.0.manifest.json`
(sha256 por fichero, commit de git, timestamp). El zip:

- lleva los ficheros en la raíz (sin carpeta envolvente), como exige Arsenio;
- normaliza `requirements.txt` a UTF-8 (en el repo está en UTF-16 y rompe `pip`);
- usa rutas POSIX (`/`) para evitar el bug de backslashes de Windows.

### Subir (no despliega)

```bash
# bash
export ARSENIO_API_KEY=pk_xxxxxxxx
python dev/tools/build_deploy.py --version 1.0.0 --upload
```
```powershell
# PowerShell
$env:ARSENIO_API_KEY = "pk_xxxxxxxx"
python dev/tools/build_deploy.py --version 1.0.0 --upload
```

La deploy key (`pk_...`) se lee **solo** de la variable de entorno
`ARSENIO_API_KEY`; nunca se escribe a disco ni se pasa en claro por argumentos.

### Desplegar (paso aparte, acotado)

El script **no** despliega. El despliegue se hace acotado a `auth` para no tocar
el contenedor `app` (Superset en uso), vía MCP:

```
compose_up(services=["auth"])
```

Ver el runbook completo en `dev/docs/RUNBOOK-deploy-auth.md`.
