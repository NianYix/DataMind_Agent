from __future__ import annotations

import ast


ALLOWED_IMPORTS = {
    "pandas",
    "numpy",
    "math",
    "json",
    "datetime",
    "statistics",
    "collections",
    "re",
    "typing",
}

FORBIDDEN_NAMES = {
    "eval",
    "exec",
    "compile",
    "open",
    "__import__",
    "input",
    "breakpoint",
    "exit",
    "quit",
}


class SecurityError(ValueError):
    pass


class _SecurityVisitor(ast.NodeVisitor):
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root = alias.name.split(".")[0]
            if root not in ALLOWED_IMPORTS:
                raise SecurityError(f"Import not allowed: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        root = (node.module or "").split(".")[0]
        if root not in ALLOWED_IMPORTS:
            raise SecurityError(f"Import not allowed: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_NAMES:
            raise SecurityError(f"Call not allowed: {node.func.id}")
        if isinstance(node.func, ast.Attribute) and node.func.attr in {"system", "popen", "remove", "rmtree"}:
            raise SecurityError(f"Attribute call not allowed: {node.func.attr}")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr.startswith("__"):
            raise SecurityError(f"Dunder attribute not allowed: {node.attr}")
        self.generic_visit(node)


def validate_code(code: str) -> None:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise SecurityError(f"Syntax error: {exc}") from exc
    _SecurityVisitor().visit(tree)
