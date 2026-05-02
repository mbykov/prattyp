"""
Узлы AST для Prattyp.
"""

from dataclasses import dataclass
from typing import Union


@dataclass
class NumNode:
    value: str  # "123", "3.14"

@dataclass
class VarNode:
    name: str  # "x", "alpha"

@dataclass
class FuncNode:
    name: str      # "sin", "cos"
    argument: 'ASTNode'

@dataclass
class BinOpNode:
    left: 'ASTNode'
    op: str        # "+", "-", "*", "/"
    right: 'ASTNode'

@dataclass
class UnaryOpNode:
    op: str        # "-"
    operand: 'ASTNode'

@dataclass
class AllNode:
    """Маркер 'всё' — закрывает текущую область видимости."""
    inner: 'ASTNode'

@dataclass
class FracNode:
    """Дробь: \frac{числитель}{знаменатель} → frac(num, den)"""
    numerator: 'ASTNode'
    denominator: 'ASTNode'

@dataclass
class ParenNode:
    """Скобки: (выражение) — для явного указания границ."""
    inner: 'ASTNode'


ASTNode = Union[
    NumNode, VarNode, FuncNode,
    BinOpNode, UnaryOpNode, AllNode,
    FracNode, ParenNode,
]
