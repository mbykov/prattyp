"""
Генератор Typst из AST.
"""

from .ast_nodes import (
    ASTNode, NumNode, VarNode, FuncNode,
    BinOpNode, UnaryOpNode, AllNode,
    FracNode, ParenNode,
)


def generate(node: ASTNode) -> str:
    return _generate(node)


def _generate(node: ASTNode) -> str:
    if isinstance(node, NumNode):
        return node.value

    if isinstance(node, VarNode):
        return node.name

    if isinstance(node, FuncNode):
        arg = _generate(node.argument)
        return f"{node.name}({arg})"

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
        inner = _generate(node.inner)
        return f"({inner})"

    raise ValueError(f"Неизвестный узел AST: {type(node)}")
