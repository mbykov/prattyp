"""
Парсер потока токенов → AST.
Pratt parser с поддержкой ALL, явных/неявных функций, скобок.
"""

from typing import List, Dict, Optional
from .tokenizer import Token
from .ast_nodes import (
    ASTNode, NumNode, VarNode, FuncNode,
    BinOpNode, UnaryOpNode, AllNode,
    FracNode, ParenNode,
)


# Приоритеты: (left_bp, right_bp)
# right_bp=0 для сравнений — правая часть как независимый островок (ALL работает)
BINARY_BP: Dict[str, tuple] = {
    "=":  (1, 0),
    "==": (2, 0),
    "!=": (2, 0),
    "<":  (3, 0),
    "<=": (3, 0),
    ">":  (3, 0),
    ">=": (3, 0),
    "+":  (4, 5),
    "-":  (4, 5),
    "*":  (5, 6),
    "/":  (5, 6),
}

UNARY_BP = 7          # унарный минус
FUNC_BP = 3           # жадность неявной функции (захватывает +, -, *, /)


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
        """Разбирает выражение. min_bp — минимальная сила связывания."""
        left = self._parse_prefix()

        while True:
            t = self.peek()

            # ALL — стоп-кран или группировка
            if t.type == "ALL":
                if min_bp > 0:
                    # внутри контекста — прерываем, ALL вернётся наверх
                    break
                # верхний уровень — группируем всё слева и продолжаем
                self.advance()
                left = ParenNode(inner=left)
                continue

            # Бинарный оператор
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

            # KEYWORD divide в середине
            if t.type == "KEYWORD" and t.value == "divide":
                left_bp, right_bp = BINARY_BP["/"]
                if left_bp < min_bp:
                    break
                self.advance()
                if self.peek().type == "SEP":
                    self.advance()
                right = self.parse_expression(right_bp)
                if isinstance(right, BinOpNode):
                    right = ParenNode(inner=right)
                left = BinOpNode(left=left, op="/", right=right)
                continue

            break

        return left

    # ─── Префиксы ───────────────────────────────────────

    def _parse_prefix(self) -> ASTNode:
        t = self.peek()

        # Скобка — явный контекст
        if t.type == "PAREN_OPEN":
            return self._parse_paren()

        # ALL в начале — возвращаем как ключевое слово
        if t.type == "ALL":
            self.advance()
            return VarNode(name="all")

        # frac
        if t.type == "KEYWORD" and t.value == "frac":
            return self._parse_frac()

        # divide в начале
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
            return self._parse_func(t.value)

        raise ValueError(f"Неожиданный токен в префиксе: {t}")

    # ─── Функция: явный и неявный режим ─────────────────

    def _parse_func(self, name: str) -> ASTNode:
        """FUNC уже съеден. Определяем режим и парсим аргумент."""
        if self.peek().type == "PAREN_OPEN":
            # Явный режим: sin ( ... )
            arg = self._parse_paren()
        else:
            # Неявный режим: sin ... all
            arg = self.parse_expression(FUNC_BP)
            # Съедаем all, если есть
            if self.peek().type == "ALL":
                self.advance()
        return FuncNode(name=name, argument=arg)

    # ─── Скобки ─────────────────────────────────────────

    def _parse_paren(self) -> ASTNode:
        """Съедает PAREN_OPEN, парсит до PAREN_CLOSE, возвращает inner."""
        self.advance()  # PAREN_OPEN
        inner = self.parse_expression(0)
        if self.peek().type == "PAREN_CLOSE":
            self.advance()
        return inner

    # ─── Frac ───────────────────────────────────────────

    def _parse_frac(self) -> ASTNode:
        self.advance()  # KEYWORD:frac
        numerator = self.parse_expression(0)
        if self.peek().type == "ALL":
            self.advance()
        if self.peek().type == "SEP":
            self.advance()  # "на"
        denominator = self.parse_expression(0)
        if self.peek().type == "ALL":
            self.advance()
        return FracNode(numerator=numerator, denominator=denominator)

    # ─── Divide ─────────────────────────────────────────

    def _parse_divide(self) -> ASTNode:
        self.advance()  # KEYWORD:divide
        left = self.parse_expression(0)
        if self.peek().type == "SEP":
            self.advance()  # "на"
        right = self.parse_expression(0)
        if isinstance(left, BinOpNode):
            left = ParenNode(inner=left)
        if isinstance(right, BinOpNode):
            right = ParenNode(inner=right)
        if self.peek().type == "ALL":
            self.advance()
        return BinOpNode(left=left, op="/", right=right)
