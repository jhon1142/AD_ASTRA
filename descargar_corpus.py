"""
Script de descarga del corpus CODEFEST AD ASTRA 2026 desde SharePoint.

Usa las cookies de sesión FedAuth + rtFa para autenticarse sin OAuth.
Las cookies duran ~5 días desde que las copiaste.

Uso:
    python descargar_corpus.py
"""
import json
import os
import time
from pathlib import Path

import requests

# ── Configuración ─────────────────────────────────────────────────────────────
SITE_URL    = "https://fuerzaaereacolombia-my.sharepoint.com"
USER_PATH   = "/personal/codefest_adastra_fac_mil_co1"
FOLDER_PATH = "/Documents/Repositorio/CORPUS CODEFEST AD ASTRA 2026"
DEST_DIR    = Path(r"c:\Documentos\AD_ASTRA\AD_ASTRA\data\raw")

# Pega aquí los valores exactos de las cookies (ya incluidos del header)
FED_AUTH = "77u/PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz48U1A+VjE1LDBoLmZ8bWVtYmVyc2hpcHwxMDAzMjAwNjIyYjUzODlhQGxpdmUuY29tLDAjLmZ8bWVtYmVyc2hpcHxqcy5yaW9zZzEyX3VuaWFuZGVzLmVkdS5jbyNleHQjQGZ1ZXJ6YWFlcmVhY29sb21iaWEub25taWNyb3NvZnQuY29tLDEzNDI5NzY1NTMyMDAwMDAwMCwwLDEzNDMwNzYwMTc1MDY3MTczNywxNjEuMTAuMjE0LjE3MiwyMTE1LGUzYTQxMjQ4LTM2ZjktNDFiNy04ZmI3LTUzZDc2ODQ5NzNlMiwsMDA2Y2ZhOGEtNDc1YS03ZDBhLTU0MGItYzM4MGUzYWIzZjgzLDgyNmYyZGEyLWMwOWQtZTAwMC1iY2ZiLWQ5M2M1YWNlN2U5OCw3MWY2MmRhMi03MDlkLWUwMDAtZDgzNi01MmU2ZWJmNGMwMGIsLDAsMTM0MzAzMzE3NzUwNTYxNDYyLDEzNDMwNTg3Mzc1MDU2MTQ2MiwsLGV5SjRiWE5mWTJNaU9pSmJYQ0pEVURGY0lsMGlMQ0p3Y21WbVpYSnlaV1JmZFhObGNtNWhiV1VpT2lKcWN5NXlhVzl6WnpFeVFIVnVhV0Z1WkdWekxtVmtkUzVqYnlJc0luVjBhU0k2SWtGdVVtbGFaR3g2UVRCeGQxaExhbnB6ZW1kSFFVRWlMQ0poZFhSb1gzUnBiV1VpT2lJeE16UXlPVGMyTlRVek1qQXdNREF3TURBaWZRPT0sMjY1MDQ2Nzc0Mzk5OTk5OTk5OSwxMzQzMDE4NjY4NjAwMDAwMDAsZGQ0Y2FmM2MtZTZmZi00ZTU4LTg3MDktZTQ5NWUyMGFmOGFkLCwsLCwsLTkyMjMzNzIwMzY4NTQ3NzU4MDgsaHR0cHM6Ly9zdHMud2luZG93cy5uZXQvZmFiZDA0N2MtZmY0OC00OTJhLThiYmItOGY5OGI5ZmI5Y2NhLywxOTMyODksVlV1VUJ0S2ZmcVRDSGRzM1YxRGtxN1FDMUZFLCwxOTMyODksVlV1VUJ0S2ZmcVRDSGRzM1YxRGtxN1FDMUZFLDQxa0xIS2tlbmFPaldhWXVoVU03aDIzVWdzbXI1VjhYUDVreE5sSGJZL3ZtcFRIZ3ZzSFIxRnZHdlR3S2JtekhsVlROUVNUei9WZDdQM3YySlMxSGdLN1FVNk5vaHpTRjM2aDkvdHEwYWNIK0xhRVBIMEZhS0ZvcWZ2UWZCRVJHenp6L0hzMGZVL0VIalFQV3lpL0QwT2dObU5TRjFwT1RTbTlsR0phOXVqYnQyUFdFb3M1djR5ZkNRSnZ2Mm84RmIzdmFGcVZKMEp1a3ZGNHNWTGJ5eUc0aVZlcVpkeEZvMWw2djA0VEJoZ1RNVmNqWitXRy9UUjJhSUhsNk9odmFoZ1lnSldOaXpOYUVzZnFqb01mazg4NG0yUytKNUJkcXl5REtKZnkvZDY2YUJDMS9XSDB0Ty9kdnBFb3VYb1lZd2xIbHBxOXVIOVMySG1CbFp1Z0NoQT09PC9TUD4="
RT_FA    = "kljjflEkh1DSDeCursXWoSxTgJYONSB3k3321P9AHI4mZTNhNDEyNDgtMzZmOS00MWI3LThmYjctNTNkNzY4NDk3M2UyIzEzNDMwMTg2Njg3MDYyNTM3NiM4MjZmMmRhMi1iMDkzLWUwMDAtYmNmYi1kYzBlOGE2N2QwYzkjanMucmlvc2cxMiU0MHVuaWFuZGVzLmVkdS5jbyMxOTMyODkjU1ZmOWt6ZGFBWmpGTHF1Q0FtWkFVSGpDZUFJI1NWZjlremRhQVpqRkxxdUNBbVpBVUhqQ2VBSQSYtORHUdIWGwifrUbgv2WJ57YZZNyA3uRWVl4q02h3FqyjRG9lEBbJmHA7ZPdKzg+tBffdWizs9Cp0EBWW+OrBNR8HKs2vAOs03miefcAUVWXdlnyE8k/TPOPrcdbpcZTuF7/ObLa8Qf6111XH6S53YV6wkjPYazrUVhyP3pcrEAwt75RRl37kcNithP5e9iu6/AC8YZPrzpwkgSr37vYJshz36eFJp/knw0u7IS0JYx9ek/Go6P5lIyPgy5uD+98ZBL85CYY8aHFTHfEBQGQlJ6pqphWsY4PqlPp6EnRZfNor+E7pRXeFQgxQKX1fydHeJZVLttp+ZTD0uGLYrCLZAAAA"

COOKIES = {"FedAuth": FED_AUTH, "rtFa": RT_FA}
HEADERS = {
    "Accept": "application/json;odata=verbose",
    "User-Agent": "Mozilla/5.0",
}

# ── Utilidades ────────────────────────────────────────────────────────────────

def get_folder_contents(server_relative_url: str) -> list[dict]:
    """Lista archivos y subcarpetas de una carpeta en SharePoint."""
    encoded = requests.utils.quote(server_relative_url)
    url = (
        f"{SITE_URL}{USER_PATH}/_api/web/"
        f"GetFolderByServerRelativeUrl('{encoded}')/Expand"
        f"?$expand=Files,Folders"
    )
    # Alternativa más robusta:
    url = (
        f"{SITE_URL}{USER_PATH}/_api/web/"
        f"GetFolderByServerRelativeUrl(@p)/Files?@p='{requests.utils.quote(server_relative_url)}'"
    )
    resp = requests.get(url, cookies=COOKIES, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("d", {}).get("results", [])


def list_folder(server_relative_url: str) -> tuple[list, list]:
    """Devuelve (archivos, subcarpetas) de una carpeta."""
    base = f"{SITE_URL}{USER_PATH}/_api/web/GetFolderByServerRelativeUrl"
    enc  = "'" + requests.utils.quote(server_relative_url, safe="/") + "'"

    files_url   = f"{base}({enc})/Files"
    folders_url = f"{base}({enc})/Folders"

    files   = requests.get(files_url,   cookies=COOKIES, headers=HEADERS, timeout=30)
    folders = requests.get(folders_url, cookies=COOKIES, headers=HEADERS, timeout=30)

    files.raise_for_status()
    folders.raise_for_status()

    return (
        files.json().get("d", {}).get("results", []),
        folders.json().get("d", {}).get("results", []),
    )


def download_file(server_relative_url: str, dest_path: Path) -> None:
    """Descarga un archivo desde SharePoint a dest_path."""
    enc = requests.utils.quote(server_relative_url, safe="/")
    url = f"{SITE_URL}{USER_PATH}/_api/web/GetFileByServerRelativeUrl('{enc}')/$value"

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    with requests.get(url, cookies=COOKIES, headers=HEADERS,
                      stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 256):
                f.write(chunk)


def sync_folder(server_relative_url: str, local_dir: Path, depth: int = 0) -> None:
    """Descarga recursivamente todos los archivos de una carpeta SharePoint."""
    indent = "  " * depth
    print(f"{indent}📁 {server_relative_url}")

    try:
        files, folders = list_folder(server_relative_url)
    except Exception as e:
        print(f"{indent}  ⚠️  Error listando carpeta: {e}")
        return

    for file in files:
        name = file["Name"]
        src  = file["ServerRelativeUrl"]
        dest = local_dir / name

        if dest.exists():
            print(f"{indent}  ✓ ya existe: {name}")
            continue

        print(f"{indent}  ↓ descargando: {name}", end=" ... ", flush=True)
        try:
            download_file(src, dest)
            size_kb = dest.stat().st_size // 1024
            print(f"OK ({size_kb} KB)")
        except Exception as e:
            print(f"ERROR: {e}")
        time.sleep(0.2)  # pausa para no saturar la API

    for folder in folders:
        if folder["Name"] in ("Forms", "_vti_cnf"):
            continue
        sub_src   = folder["ServerRelativeUrl"]
        sub_local = local_dir / folder["Name"]
        sync_folder(sub_src, sub_local, depth + 1)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root_url = USER_PATH + FOLDER_PATH
    print(f"Descargando corpus desde:\n  {SITE_URL}{root_url}")
    print(f"Destino local:\n  {DEST_DIR}\n")
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    sync_folder(root_url, DEST_DIR)
    print("\n✓ Descarga completa.")
