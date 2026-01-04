#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para gerar mapa de rotas do Flask

Gera docs/routes.md e docs/routes.json com todas as rotas registradas.
"""
import json
import sys
from pathlib import Path

# Adicionar backend ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app import create_app  # noqa: E402


def get_blueprint_name(rule):
    """Extrai o nome do blueprint da regra"""
    if "." in rule.endpoint:
        return rule.endpoint.split(".")[0]
    return "main"


def get_auth_type(view_func):
    """Obtém o tipo de autenticação requerida (se houver)"""
    return getattr(view_func, "_auth", "")


def dump_routes():
    """Gera mapa de rotas"""
    app = create_app()

    routes = []

    with app.app_context():
        for rule in app.url_map.iter_rules():
            # Ignorar rotas estáticas e rotas de debug se não habilitadas
            if rule.endpoint == "static":
                continue

            # Obter view function
            view_func = app.view_functions.get(rule.endpoint)
            if not view_func:
                continue

            # Obter métodos HTTP
            methods = sorted(rule.methods - {"HEAD", "OPTIONS"})
            if not methods:
                continue

            # Obter blueprint
            blueprint = get_blueprint_name(rule)

            # Obter autenticação
            auth_type = get_auth_type(view_func)
            auth_display = {
                "basic": "Basic Auth",
                "edit": "Edit Auth",
                "": "Nenhuma",
            }.get(auth_type, "Nenhuma")

            # Obter nome da função
            func_name = view_func.__name__ if view_func else "N/A"

            # Adicionar rota para cada método
            for method in methods:
                routes.append(
                    {
                        "method": method,
                        "path": rule.rule,
                        "endpoint": rule.endpoint,
                        "blueprint": blueprint,
                        "function": func_name,
                        "auth": auth_display,
                        "auth_type": auth_type,
                    }
                )

    # Ordenar por path + method para diffs estáveis
    routes.sort(key=lambda r: (r["path"], r["method"]))

    # Gerar markdown
    generate_markdown(routes)

    # Gerar JSON (opcional)
    generate_json(routes)

    print(f"[OK] Gerado mapa de {len(routes)} rotas")
    print("  - docs/routes.md")
    print("  - docs/routes.json")


def generate_markdown(routes):
    """Gera arquivo markdown"""
    docs_dir = backend_dir.parent / "docs"
    docs_dir.mkdir(exist_ok=True)

    output_file = docs_dir / "routes.md"

    lines = [
        "<!-- AUTO-GENERATED: do not edit -->",
        "",
        "# Mapa de Rotas",
        "",
        "Este arquivo é gerado automaticamente pelo script `backend/scripts/dump_routes.py`.",
        "",
        "**Última atualização:** Gerado automaticamente",
        "",
        "---",
        "",
        "## Tabela de Rotas",
        "",
        "| Método | Path | Endpoint | Blueprint | Função | Autenticação |",
        "|--------|------|----------|-----------|--------|--------------|",
    ]

    for route in routes:
        method = route["method"]
        path = route["path"]
        endpoint = route["endpoint"]
        blueprint = route["blueprint"]
        func = route["function"]
        auth = route["auth"]

        lines.append(f"| {method} | `{path}` | `{endpoint}` | `{blueprint}` | `{func}` | {auth} |")

    lines.extend(
        [
            "",
            "---",
            "",
            "## Legenda",
            "",
            "- **Basic Auth**: Requer autenticação HTTP Basic",
            "- **Edit Auth**: Requer autenticação para operações de edição",
            "- **Nenhuma**: Rota pública (sem autenticação)",
            "",
            "## Como Atualizar",
            "",
            "Execute o script:",
            "",
            "```bash",
            "python backend/scripts/dump_routes.py",
            "```",
            "",
            "Ou use o comando:",
            "",
            "```bash",
            "cd backend",
            "python scripts/dump_routes.py",
            "```",
        ]
    )

    output_file.write_text("\n".join(lines), encoding="utf-8")


def generate_json(routes):
    """Gera arquivo JSON"""
    docs_dir = backend_dir.parent / "docs"
    docs_dir.mkdir(exist_ok=True)

    output_file = docs_dir / "routes.json"

    data = {
        "generated_by": "backend/scripts/dump_routes.py",
        "total_routes": len(routes),
        "routes": routes,
    }

    output_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    try:
        dump_routes()
    except Exception as e:
        print(f"Erro ao gerar mapa de rotas: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
