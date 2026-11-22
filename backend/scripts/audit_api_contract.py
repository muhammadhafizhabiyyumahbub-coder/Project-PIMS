import json
import re
from fastapi.openapi.utils import get_openapi
from app.main import app

def extract_spec_endpoints():
    endpoints = []
    # Regex to capture | Method | Endpoint | Description |
    # The spec uses a table with headers: Method, Endpoint, Description
    # We want to ignore the header/separator lines
    with open("../specifications/backend/api-spec.md", "r") as f:
        content = f.read()
    
    # Matches rows like: | GET | /health | Basic health status |
    pattern = re.compile(r"\|\s*(GET|POST|PUT|PATCH|DELETE)\s*\|\s*(\/[^\s|]+)\s*\|")
    for match in pattern.finditer(content):
        method = match.group(1).upper()
        path = match.group(2)
        # Clean path: the spec uses /api/v1 prefix conceptually, but endpoints are listed as /health
        # The app.openapi() routes are usually /api/v1/health or similar.
        # Let's collect them and compare.
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

def audit():
    spec_endpoints = extract_spec_endpoints()
    app_endpoints = get_app_endpoints()
    
    # Normalize paths: some specs might not have /api/v1 prefix explicitly for all, 
    # but the app has it. Let's compare carefully.
    # The spec says: GET | /portfolios |...
    # The app might have: /api/v1/portfolios
    
    normalized_spec = set()
    for m, p in spec_endpoints:
        if not p.startswith("/api/v1"):
            p = f"/api/v1{p}" if p != "/health" else p # health is special in spec
        normalized_spec.add((m, p))
        
    normalized_app = set()
    for m, p in app_endpoints:
        normalized_app.add((m, p))
        
    in_spec_not_app = normalized_spec - normalized_app
    in_app_not_spec = normalized_app - normalized_spec
    
    # Check method mismatches on paths
    spec_paths = {p for m, p in normalized_spec}
    app_paths = {p for m, p in normalized_app}
    
    common_paths = spec_paths.intersection(app_paths)
    method_mismatch = []
    for p in common_paths:
        methods_spec = {m for m, path in normalized_spec if path == p}
        methods_app = {m for m, path in normalized_app if path == p}
        if methods_spec != methods_app:
            method_mismatch.append((p, methods_spec, methods_app))
            
    print("--- (a) Endpoint di spec yang BELUM ada di aplikasi ---")
    for m, p in sorted(in_spec_not_app):
        print(f"{m} {p}")
        
    print("\n--- (b) Endpoint di aplikasi yang TIDAK ada di spec ---")
    for m, p in sorted(in_app_not_spec):
        print(f"{m} {p}")
        
    print("\n--- (c) Path sama tapi method berbeda ---")
    for p, spec, app in sorted(method_mismatch):
        print(f"Path: {p}, Spec Methods: {spec}, App Methods: {app}")

    print(f"\nRingkasan: Spec not in app: {len(in_spec_not_app)}, App not in spec: {len(in_app_not_spec)}, Mismatches: {len(method_mismatch)}")

if __name__ == "__main__":
    audit()
