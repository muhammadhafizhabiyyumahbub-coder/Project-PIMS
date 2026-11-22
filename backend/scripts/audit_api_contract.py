import re
import sys
from pathlib import Path
from fastapi.openapi.utils import get_openapi
from app.main import app

def extract_spec_endpoints():
    endpoints = []
    spec_path = Path(__file__).resolve().parents[2] / "specifications" / "backend" / "api-spec.md"
    
    if not spec_path.exists():
        print(f"Error: Spec file not found at {spec_path}")
        return []
        
    with open(spec_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    pattern = re.compile(r"\|\s*(GET|POST|PUT|PATCH|DELETE)\s*\|\s*`?(/[^`|\s]+)`?\s*\|")
    for match in pattern.finditer(content):
        method = match.group(1).upper()
        path = match.group(2)
        endpoints.append((method, path))
    return endpoints

def get_app_endpoints():
    openapi = get_openapi(title=app.title, version=app.version, routes=app.routes)
    endpoints = []
    paths = openapi.get("paths", {})
    for path, methods in paths.items():
        for method in methods.keys():
            endpoints.append((method.upper(), path))
    return endpoints

def normalize_path(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", path)

def normalize(m, p):
    if p == "/health" or p == "/health/ready":
        return (m, p)
    if not p.startswith("/api/v1"):
        p = f"/api/v1{p}"
    return (m, normalize_path(p))

def audit():
    spec_raw = extract_spec_endpoints()
    app_raw = get_app_endpoints()
    
    spec_endpoints = {normalize(m, p) for m, p in spec_raw}
    app_endpoints = {normalize(m, p) for m, p in app_raw}
    
    in_spec_not_app = sorted(list(spec_endpoints - app_endpoints))
    in_app_not_spec = sorted(list(app_endpoints - spec_endpoints))
    
    print(f"--- Audit Report ---")
    print(f"Endpoints spec terbaca: {len(spec_raw)}")
    if len(spec_raw) < 40:
        print("WARNING: Parser mungkin gagal membaca tabel! Harap periksa regex.")
    print(f"Endpoints app terbaca: {len(app_raw)}")
    print(f"Gap (a) Spec not in app: {len(in_spec_not_app)}")
    print(f"Gap (b) App not in spec: {len(in_app_not_spec)}")

    print("\n--- (a) Endpoint di spec yang BELUM ada di aplikasi ---")
    for m, p in in_spec_not_app:
        print(f"{m} {p}")
        
    print("\n--- (b) Endpoint di aplikasi yang TIDAK ada di spec ---")
    for m, p in in_app_not_spec[:10]:
        print(f"{m} {p}")
    if len(in_app_not_spec) > 10:
        print("... (truncated)")

if __name__ == "__main__":
    audit()
