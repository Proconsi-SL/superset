#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_deploy.py — Empaqueta el microservicio de autenticacion como artifact de
Arsenio y (opcionalmente) lo sube, sin desplegar nunca automaticamente.

CONTEXTO
--------
El despliegue de Superset se migro a Arsenio (proyecto `superset_pro`). El
codigo del microservicio de guest tokens (carpeta `autenticacion/` en el repo)
se despliega como artifact `auth`, que Arsenio extrae en
`deploys/superset_pro/auth/` y desde donde `auth.Dockerfile` construye la imagen.

Este script:
  1. Toma la fuente de `autenticacion/`.
  2. Sustituye `keys.json` por el REAL de `dev/secrets/keys.json` (gitignorado):
     el del repo es un placeholder y no sirve para produccion.
  3. Normaliza `requirements.txt` a UTF-8 (en el repo esta en UTF-16, rompe pip).
  4. Genera un .zip con rutas POSIX (evita el bug de backslashes de Windows que
     la propia guia de Arsenio advierte) en `dev/deployments/auth/`.
  5. Escribe un manifest.json con sha256 por fichero, commit de git y version.
  6. Con --upload, sube el zip al artifact via la API de Arsenio (X-API-Key pk_).
     NUNCA llama a /deploys: el despliegue (build+up) se hace aparte y acotado a
     `auth` para no tocar el contenedor `app` (Superset en uso).

El zip contiene los ficheros DIRECTAMENTE en su raiz (sin carpeta envolvente),
como exige Arsenio: al extraer, functions.py queda en deploys/superset_pro/auth/.

USO
---
  # Solo construir (offline):
  python dev/tools/build_deploy.py --version 1.0.0

  # Construir y subir (no despliega):
  set ARSENIO_API_KEY=pk_xxx   (o export en bash)
  python dev/tools/build_deploy.py --version 1.0.0 --upload

La API key NUNCA se pasa por linea de comandos en claro si se puede evitar:
usar la variable de entorno ARSENIO_API_KEY. Nunca se escribe a disco.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import NoReturn

# --- Rutas base -------------------------------------------------------------
# El script vive en dev/tools/, la raiz del repo esta dos niveles arriba.
REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "autenticacion"
SECRETS_KEYS = REPO_ROOT / "dev" / "secrets" / "keys.json"
OUT_DIR = REPO_ROOT / "dev" / "deployments" / "auth"

# Ficheros del microservicio que van dentro del artifact (raiz del zip).
# `keys.json` se inyecta desde dev/secrets (no desde el repo).
# `requirements.txt` se normaliza a UTF-8.
INCLUDE_FILES = [
    "functions.py",
    "main.py",
    "inputs.py",
    "supervisord.conf",
    "requirements.txt",
    "keys.json",
]

# Nunca deben acabar en el zip (defensa segun la guia de empaquetado Arsenio).
FORBIDDEN_IN_ZIP = {
    "Dockerfile", "docker-compose.yml", ".env",
    "README.md", ".gitignore",
}

# Solo valores de PASSWORD que delatan un placeholder (el username real del
# servicio es "user_conexion", asi que no se marca por el usuario).
PLACEHOLDER_HINTS = {"pw", "pw_segura", "password", "changeme", "cambiame"}


def die(msg: str) -> NoReturn:
    print(f"\nERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def read_text_normalized(path: Path) -> bytes:
    """Lee un fichero de texto y lo devuelve como UTF-8 (sin BOM), con saltos LF.

    Detecta BOM UTF-16/UTF-8. Es lo que arregla el requirements.txt en UTF-16
    del repo, que de otro modo rompe `pip install` dentro del contenedor.
    """
    raw = path.read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = raw.decode("utf-16")
    elif raw[:3] == b"\xef\xbb\xbf":
        text = raw.decode("utf-8-sig")
    else:
        text = raw.decode("utf-8")
    # Normaliza CRLF -> LF; el contenedor es Linux.
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def load_keys() -> bytes:
    if not SECRETS_KEYS.exists():
        die(
            f"No existe {SECRETS_KEYS}\n"
            "  Deja ahi el keys.json REAL (el del repo es un placeholder).\n"
            "  Formato:\n"
            '    {\n'
            '      \"conexion_token\": { \"username\": \"<user>\", \"password\": \"<pw>\" }\n'
            "    }\n"
            "  Esa carpeta esta en .gitignore: nunca se commitea."
        )
    data: dict = {}
    try:
        data = json.loads(SECRETS_KEYS.read_text(encoding="utf-8"))
    except Exception as e:
        die(f"{SECRETS_KEYS} no es JSON valido: {e}")
    ct = (data or {}).get("conexion_token") or {}
    user, pw = ct.get("username"), ct.get("password")
    if not user or not pw:
        die("keys.json debe tener conexion_token.username y conexion_token.password")
    if str(user).lower() in PLACEHOLDER_HINTS or str(pw).lower() in PLACEHOLDER_HINTS:
        print(
            "  AVISO: keys.json parece contener valores PLACEHOLDER "
            f"(username={user!r}). El guest_token fallara con 401 si no es el real."
        )
    # Reserializa canonicamente (UTF-8, LF).
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def build_members() -> "list[tuple[str, bytes]]":
    """Devuelve [(arcname_posix, bytes)] con el contenido final del artifact."""
    members: "list[tuple[str, bytes]]" = []
    for name in INCLUDE_FILES:
        if name in FORBIDDEN_IN_ZIP:
            die(f"Fichero prohibido en el zip: {name}")
        if name == "keys.json":
            content = load_keys()
        elif name == "requirements.txt":
            content = read_text_normalized(SRC_DIR / name)
        else:
            src = SRC_DIR / name
            if not src.exists():
                die(f"Falta el fichero fuente: {src}")
            # .py / .conf: normaliza a UTF-8/LF por consistencia.
            content = read_text_normalized(src)
        members.append((name, content))  # arcname en la raiz, con "/" implicito
    return members


def write_zip(members, version: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = OUT_DIR / f"auth-{version}.zip"
    # zipfile escribe arcnames tal cual: usamos nombres planos (sin separadores),
    # asi que no hay riesgo de "\". Si en el futuro se anidan carpetas, construir
    # el arcname siempre con "/".
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for arcname, content in members:
            assert "\\" not in arcname, "arcname debe usar '/'"
            zi = zipfile.ZipInfo(arcname)
            zi.external_attr = 0o644 << 16  # permisos de fichero regular
            zf.writestr(zi, content)
    return zip_path


def write_manifest(members, version: str, zip_path: Path) -> Path:
    manifest = {
        "artifact": "auth",
        "project": "superset_pro",
        "version": version,
        "git_commit": git_commit(),
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "zip": zip_path.name,
        "zip_sha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
        "files": [
            {"name": n, "bytes": len(c), "sha256": hashlib.sha256(c).hexdigest()}
            for n, c in members
        ],
    }
    mpath = OUT_DIR / f"auth-{version}.manifest.json"
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return mpath


def upload(zip_path: Path, version: str, project: str, artifact: str, base_url: str) -> None:
    api_key = os.environ.get("ARSENIO_API_KEY", "").strip()
    if not api_key:
        die("Falta ARSENIO_API_KEY (la deploy key pk_...) en el entorno para --upload.")
    if not api_key.startswith("pk_"):
        print("  AVISO: la API key no empieza por 'pk_'; ¿seguro que es la deploy key?")
    url = f"{base_url.rstrip('/')}/projects/{project}/artifacts/{artifact}/upload?clean=true&version={version}"
    body, content_type = _multipart(zip_path)
    import urllib.request
    import urllib.error
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("X-API-Key", api_key)
    req.add_header("Content-Type", content_type)
    print(f"\n  Subiendo {zip_path.name} -> {url.split('?')[0]} (version={version}) ...")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            print(f"  HTTP {resp.status} {resp.reason}")
            print("  " + resp.read().decode("utf-8", "replace")[:500])
    except urllib.error.HTTPError as e:
        die(f"Upload fallo: HTTP {e.code} {e.reason}\n{e.read().decode('utf-8', 'replace')[:800]}")
    except Exception as e:
        die(f"Upload fallo: {e}")
    print(
        "\n  Subida OK. El despliegue NO se ha ejecutado (por diseno).\n"
        "  Para desplegar SOLO auth sin tocar Superset, usar el MCP:\n"
        '    compose_up(services=["auth"])\n'
    )


def _multipart(zip_path: Path) -> "tuple[bytes, str]":
    """Codifica el zip como multipart/form-data campo 'file' (stdlib, sin deps)."""
    boundary = "----arsenioBuildDeploy" + hashlib.sha1(zip_path.name.encode()).hexdigest()[:16]
    buf = io.BytesIO()
    pre = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{zip_path.name}"\r\n'
        f"Content-Type: application/zip\r\n\r\n"
    ).encode("utf-8")
    buf.write(pre)
    buf.write(zip_path.read_bytes())
    buf.write(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    return buf.getvalue(), f"multipart/form-data; boundary={boundary}"


def main() -> None:
    ap = argparse.ArgumentParser(description="Empaqueta y (opcional) sube el artifact auth de Arsenio.")
    ap.add_argument("--version", default="0.1.0", help="Version del artifact (semver). Default 0.1.0")
    ap.add_argument("--upload", action="store_true", help="Sube el zip a Arsenio (no despliega).")
    ap.add_argument("--project", default="superset_pro")
    ap.add_argument("--artifact", default="auth")
    ap.add_argument("--base-url", default="https://smart.proconsi.com/arsenio/v3")
    args = ap.parse_args()

    print(f"Repo:      {REPO_ROOT}")
    print(f"Fuente:    {SRC_DIR}")
    print(f"Secretos:  {SECRETS_KEYS}")
    print(f"Version:   {args.version}  (git {git_commit()})")

    members = build_members()
    zip_path = write_zip(members, args.version)
    mpath = write_manifest(members, args.version, zip_path)

    total = sum(len(c) for _, c in members)
    print("\n  Contenido del artifact (raiz del zip):")
    for n, c in members:
        print(f"    - {n:20s} {len(c):>7d} B")
    print(f"\n  ZIP:      {zip_path}  ({zip_path.stat().st_size} B, {total} B sin comprimir)")
    print(f"  Manifest: {mpath}")

    if args.upload:
        upload(zip_path, args.version, args.project, args.artifact, args.base_url)
    else:
        print("\n  (offline) Para subir: re-ejecuta con --upload y ARSENIO_API_KEY en el entorno.")


if __name__ == "__main__":
    main()
