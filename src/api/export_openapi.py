"""
Sprint 6, Day 40: Export OpenAPI spec + Postman collection.
Run with: python -m src.api.export_openapi
"""

import json
from pathlib import Path

from src.api.main import app

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = BASE_DIR / "docs"


def export_openapi_spec():
    """Export openapi spec."""
    schema = app.openapi()
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DOCS_DIR / "openapi.json"
    with open(out_path, "w") as f:
        json.dump(schema, f, indent=2)
    return out_path, schema


def build_postman_collection(openapi_schema):
    """
    Minimal-but-valid Postman v2.1 collection derived directly from the OpenAPI paths
    -- one request per (path, method), grouped flat (not folder-per-tag) to keep this a straightforward,
    dependency-free converter rather than pulling in a full openapi-to-postman package for a one-off export.
    """
    items = []
    base_url = "http://127.0.0.1:8000"

    for path, methods in openapi_schema.get("paths", {}).items():
        for method, details in methods.items():
            # Convert OpenAPI {param} style to Postman :param style for path variables
            postman_path = path
            path_variables = []
            for param in details.get("parameters", []):
                if param.get("in") == "path":
                    name = param["name"]
                    postman_path = postman_path.replace(f"{{{name}}}", f":{name}")
                    path_variables.append({"key": name, "value": ""})

            query_params = [
                {"key": p["name"], "value": "", "disabled": True}
                for p in details.get("parameters", [])
                if p.get("in") == "query"
            ]

            items.append(
                {
                    "name": details.get("summary") or f"{method.upper()} {path}",
                    "request": {
                        "method": method.upper(),
                        "header": [],
                        "url": {
                            "raw": f"{base_url}{postman_path}",
                            "host": [base_url],
                            "path": [p for p in postman_path.strip("/").split("/")],
                            "variable": path_variables,
                            "query": query_params,
                        },
                        "description": details.get("description", ""),
                    },
                }
            )

    return {
        "info": {
            "name": "N100 Financial Intelligence API",
            "description": "Auto-generated from openapi.json",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": items,
    }


def export_postman_collection(openapi_schema):
    """Export postman collection for the given openapi_schema."""
    collection = build_postman_collection(openapi_schema)
    out_path = DOCS_DIR / "postman_collection.json"
    with open(out_path, "w") as f:
        json.dump(collection, f, indent=2)
    return out_path, len(collection["item"])


if __name__ == "__main__":
    openapi_path, schema = export_openapi_spec()
    print(f"OpenAPI spec: {openapi_path} ({len(schema['paths'])} paths)")

    postman_path, request_count = export_postman_collection(schema)
    print(f"Postman collection: {postman_path} ({request_count} requests)")

    print("\nAll endpoints:")
    for path, methods in schema["paths"].items():
        for method in methods:
            print(f"  {method.upper():6} {path}")
