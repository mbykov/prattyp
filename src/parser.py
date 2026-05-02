"""
Парсер потока токенов → AST.
Pratt parser с приоритетами операторов.
"""

from typing import List, Callable, Dict
from .tokenizer import Token
from .ast_nodes import (
    ASTNode, NumNode, VarNode, FuncNode,
    BinOpNode, UnaryOpNode, AllNode,
    FracNode, ParenNode,
)


# Приоритеты (binding power) для бинарных операторов
# (left_bp, right_bp)
BINARY_BP: Dict[str, tuple] = {
    "=":  (1, 2),
    "==": (2, 3),
    "!=": (2, 3),
    "<":  (3, 4),
    "<=": (3, 4),
    ">":  (3, 4),
    ">=": (3, 4),
    "+":  (4, 5),
    "-":  (4, 5),
    "*":  (5, 6),
    "/":  (5, 6),
}

UNARY_BP = 7  # унарный минус, функции


def parse(tokens: List[Token]) -> ASTNode:
    parser = _Parser(tokens)
    ast = parser.parse_expression(0)
    return ast


class _Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token("END", "")

    def advance(self) -> Token:
        t = self.peek()
        self.pos += 1
        return t

    # ─── Pratt: главный метод ───────────────────────────

    def parse_expression(self, min_bp: int) -> ASTNode:
        """Разбирает выражение с учётом минимальной силы связывания."""
        left = self._parse_prefix()

        while True:
            t = self.peek()

            # ALL: закрывает левый операнд
            if t.type == "ALL":
                self.advance()
                left = AllNode(inner=left)
                continue

            # divide в середине: как оператор / с приоритетом
            if t.type == "KEYWORD" and t.value == "divide":
                left_bp, right_bp = BINARY_BP["/"]
                if left_bp < min_bp:
                    break
                self.advance()
                # пропускаем "на"
                if self.peek().type == "SEP":
                    self.advance()
                right = self.parse_expression(right_bp)
                if isinstance(right, BinOpNode):
                    right = ParenNode(inner=right)
                left = BinOpNode(left=left, op="/", right=right)
                continue

            # Обычный бинарный оператор
            if t.type == "OP":
                op = t.value
                entry = BINARY_BP.get(op)
                if entry is None:
                    break
                left_bp, right_bp = entry
                if left_bp < min_bp:
                    break
                self.advance()
                right = self.parse_expression(right_bp)
                left = BinOpNode(left=left, op=op, right=right)
                continue

            break

        return left

    # ─── Префиксные атомы ───────────────────────────────

    def _parse_prefix(self) -> ASTNode:
        t = self.peek()

        # frac: KEYWORD:frac <числитель> SEP:на <знаменатель>
        if t.type == "KEYWORD" and t.value == "frac":
            return self._parse_frac()

        # divide в начале: KEYWORD:divide <левый> SEP:на <правый>
        if t.type == "KEYWORD" and t.value == "divide":
            return self._parse_divide()

        self.advance()

        # Унарный минус
        if t.type == "OP" and t.value == "-":
            operand = self.parse_expression(UNARY_BP)
            return UnaryOpNode(op="-", operand=operand)

        # Число
        if t.type == "NUM":
            return NumNode(value=t.value)

        # Переменная
        if t.type == "VAR":
            return VarNode(name=t.value)

        # Функция
        if t.type == "FUNC":
            arg = self.parse_expression(UNARY_BP)
            return FuncNode(name=t.value, argument=arg)

        raise ValueError(f"Неожиданный токен в префиксе: {t}")

    # ─── Frac ───────────────────────────────────────────

    def _parse_frac(self) -> ASTNode:
        """KEYWORD:frac <числитель> SEP:на <знаменатель>"""
        self.advance()  # KEYWORD:frac
        numerator = self._parse_frac_operand()

        if self.peek().type == "SEP":
            self.advance()  # "на"

        denominator = self._parse_frac_operand()
        return FracNode(numerator=numerator, denominator=denominator)

    def _parse_frac_operand(self) -> ASTNode:
        """Парсит операнд дроби до SEP, END или ALL."""
        left = self.parse_expression(0)
        # ALL после операнда — закрываем
        if self.peek().type == "ALL":
            self.advance()
            left = AllNode(inner=left)
        return left

    # ─── Divide ─────────────────────────────────────────

    def _parse_divide(self) -> ASTNode:
        self.advance()
        left = self.parse_expression(0)

        if self.peek().type == "SEP":
            self.advance()

        right = self.parse_expression(0)

        # Скобки для сложных операндов
        if isinstance(left, BinOpNode):
            left = ParenNode(inner=left)
        if isinstance(right, BinOpNode):
            right = ParenNode(inner=right)

        if self.peek().type == "ALL":
            self.advance()

        return BinOpNode(left=left, op="/", right=right)
