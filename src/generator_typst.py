"""
Генератор Typst из AST.
"""

from .ast_nodes import (
    ASTNode, NumNode, VarNode, FuncNode,
    BinOpNode, UnaryOpNode, AllNode,
    FracNode, ParenNode,
    PowNode, SqrtNode, RootNode,
    LimNode,
)


def generate(node: ASTNode) -> str:
    return _generate(node)


def _generate(node: ASTNode) -> str:
    if isinstance(node, NumNode):
        return node.value

    if isinstance(node, VarNode):
        name = node.name
        if " " in name or not name.isascii():
            return f'"{name}"'
        return name

    if isinstance(node, FuncNode):
        name = node.name
        if name == "lim_func":
            arg = node.argument
            while isinstance(arg, ParenNode):
                arg = arg.inner
            return f"lim({_generate(arg)})"
        if name == "lim_seq":
            arg = node.argument
            while isinstance(arg, ParenNode):
                arg = arg.inner
            return f"lim({_generate(arg)})"
        # остальные функции как обычно
        arg = node.argument
        while isinstance(arg, ParenNode):
            arg = arg.inner
        return f"{name}({_generate(arg)})"


    if isinstance(node, BinOpNode):
        left = _generate(node.left)
        right = _generate(node.right)
        return f"{left} {node.op} {right}"

    if isinstance(node, UnaryOpNode):
        operand = _generate(node.operand)
        return f"-{operand}"

    if isinstance(node, AllNode):
        return _generate(node.inner)

    if isinstance(node, FracNode):
        num = _generate(node.numerator)
        den = _generate(node.denominator)
        return f"frac({num}, {den})"

    if isinstance(node, ParenNode):
        inner = node.inner
        while isinstance(inner, ParenNode):
            inner = inner.inner
        inner_str = _generate(inner)
        return f"({inner_str})"

    if isinstance(node, PowNode):
        base = _generate(node.base)
        exp = _generate(node.exponent)
        if isinstance(node.base, (BinOpNode, UnaryOpNode)):
            base = f"({base})"
        if isinstance(node.exponent, (BinOpNode, UnaryOpNode)):
            exp = f"({exp})"
        return f"{base}^{exp}"

    if isinstance(node, SqrtNode):
        rad = node.radicand
        while isinstance(rad, ParenNode):
            rad = rad.inner
        rad_str = _generate(rad)
        return f"sqrt({rad_str})"

    if isinstance(node, RootNode):
        deg = node.degree
        rad = node.radicand
        while isinstance(rad, ParenNode):
            rad = rad.inner
        deg_str = _generate(deg)
        rad_str = _generate(rad)
        return f"root({deg_str}, {rad_str})"

    if isinstance(node, LimNode):
        func = _generate(node.function)
        var = _generate(node.variable)
        target = _generate(node.target)
        return f"lim_({var} -> {target}) {func}"

    raise ValueError(f"Неизвестный узел AST: {type(node)}")
