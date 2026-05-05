"""
Генератор Typst из AST.
"""

from .ast_nodes import (
    ASTNode, NumNode, VarNode, FuncNode,
    BinOpNode, UnaryOpNode, AllNode,
    FracNode, ParenNode,
    PowNode, SqrtNode, RootNode,
)


def generate(node: ASTNode) -> str:
    return _generate(node)


def _generate(node: ASTNode) -> str:
    if isinstance(node, NumNode):
        return node.value

    if isinstance(node, VarNode):
        return node.name

    if isinstance(node, FuncNode):
        arg = node.argument
        while isinstance(arg, ParenNode):
            arg = arg.inner
        arg_str = _generate(arg)
        return f"{node.name}({arg_str})"

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


    raise ValueError(f"Неизвестный узел AST: {type(node)}")
