"""Regression tests for desktop HUD widget construction order."""

import ast
from pathlib import Path


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def _find_method(tree: ast.AST, class_name: str, method_name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and member.name == method_name:
                    return member
    raise AssertionError(f"{class_name}.{method_name} was not found")


def _attribute_assignment_line(method: ast.FunctionDef, attribute_name: str) -> int | None:
    for node in ast.walk(method):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
                and target.attr == attribute_name
            ):
                return node.lineno
    return None


def _tooltip_binding_line(method: ast.FunctionDef, attribute_name: str) -> int | None:
    for node in ast.walk(method):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "_bind_floating_tooltip":
            continue
        for argument in node.args:
            if (
                isinstance(argument, ast.Attribute)
                and isinstance(argument.value, ast.Name)
                and argument.value.id == "self"
                and argument.attr == attribute_name
            ):
                return node.lineno
    return None


def test_floating_hud_controls_are_created_before_tooltips_are_bound():
    """Guard against startup crashes from binding tooltips to uninitialized widgets."""
    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
    method = _find_method(tree, "JarvisDesktop", "_build_floating_hud")

    for widget_name in ("_floating_mode_button", "_floating_resize_grip"):
        created_line = _attribute_assignment_line(method, widget_name)
        tooltip_line = _tooltip_binding_line(method, widget_name)
        assert created_line is not None, f"{widget_name} must be constructed"
        assert tooltip_line is not None, f"{widget_name} tooltip must be bound"
        assert created_line < tooltip_line, (
            f"{widget_name} must be constructed before its tooltip is bound "
            f"(constructor line {created_line}, tooltip line {tooltip_line})"
        )
