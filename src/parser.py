"""
Парсер потока токенов → AST.
Pratt parser с поддержкой ALL, явных/неявных функций, скобок, степеней, корней.
"""

from typing import List, Dict, Optional, Callable
from .tokenizer import Token
from .ast_nodes import (
    ASTNode, NumNode, VarNode, FuncNode,
    BinOpNode, UnaryOpNode, AllNode,
    FracNode, ParenNode,
    PowNode, SqrtNode, RootNode,
)


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
    "^":  (6, 5),
}

UNARY_BP = 7
FUNC_BP = 3


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

    def parse_expression(self, min_bp: int) -> ASTNode:
        left = self._parse_prefix()
        while True:
            t = self.peek()
            if t.type == "ALL":
                if min_bp > 0:
                    break
                self.advance()
                left = ParenNode(inner=left)
                continue
            if t.type == "SEP":
                left_bp, right_bp = BINARY_BP["/"]
                if left_bp < min_bp:
                    break
                self.advance()
                right = self.parse_expression(right_bp)
                if isinstance(left, BinOpNode):
                    left = ParenNode(inner=left)
                if isinstance(right, BinOpNode):
                    right = ParenNode(inner=right)
                left = BinOpNode(left=left, op="/", right=right)
                continue
            if t.type == "KEYWORD" and t.value == "pow":
                left_bp, right_bp = BINARY_BP["^"]
                if left_bp < min_bp:
                    break
                self.advance()
                if self.peek().type == "KEYWORD" and self.peek().value == "degree":
                    self.advance()
                if self.peek().type == "KEYWORD" and self.peek().value == "square":
                    self.advance()
                    exponent = NumNode(value="2")
                elif self.peek().type == "KEYWORD" and self.peek().value == "cube":
                    self.advance()
                    exponent = NumNode(value="3")
                else:
                    exponent = self.parse_expression(right_bp)
                left = PowNode(base=left, exponent=exponent)
                continue
            if t.type == "KEYWORD" and t.value == "sqrt_postfix":
                if min_bp > 0:
                    break
                self.advance()
                left = SqrtNode(radicand=left)
                continue
            if t.type == "KEYWORD" and t.value == "square":
                if self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].value == "sqrt_postfix":
                    if min_bp > 0:
                        break
                    self.advance()
                    self.advance()
                    left = SqrtNode(radicand=left)
                    continue
                if min_bp > 0:
                    break
                self.advance()
                left = PowNode(base=left, exponent=NumNode(value="2"))
                continue
            if t.type == "KEYWORD" and t.value == "cube":
                if self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].value == "sqrt_postfix":
                    if min_bp > 0:
                        break
                    self.advance()
                    self.advance()
                    left = RootNode(degree=NumNode(value="3"), radicand=left)
                    continue
                if min_bp > 0:
                    break
                self.advance()
                left = PowNode(base=left, exponent=NumNode(value="3"))
                continue
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
            if t.type == "KEYWORD" and t.value == "divide":
                left_bp, right_bp = BINARY_BP["/"]
                if left_bp < min_bp:
                    break
                self.advance()
                if self.peek().type == "SEP":
                    self.advance()
                right = self.parse_expression(right_bp)
                if isinstance(left, BinOpNode):
                    left = ParenNode(inner=left)
                if isinstance(right, BinOpNode):
                    right = ParenNode(inner=right)
                left = BinOpNode(left=left, op="/", right=right)
                continue
            if self._is_atom(t):
                left_bp, right_bp = BINARY_BP["*"]
                if left_bp < min_bp:
                    break
                right = self.parse_expression(right_bp)
                left = BinOpNode(left=left, op="*", right=right)
                continue
            break
        return left

    def _is_atom(self, t: Token) -> bool:
        return t.type in ("VAR", "NUM", "FUNC", "PAREN_OPEN") or \
               (t.type == "KEYWORD" and t.value in ("frac", "divide", "sqrt", "pow"))

    def _parse_prefix(self) -> ASTNode:
        t = self.peek()
        if t.type == "PAREN_OPEN":
            return self._parse_paren()
        if t.type == "ALL":
            self.advance()
            return VarNode(name="all")
        if t.type == "OF":
            self.advance()
            return self.parse_expression(0)
        if t.type == "KEYWORD" and t.value == "frac":
            return self._parse_frac()
        if t.type == "KEYWORD" and t.value == "divide":
            return self._parse_divide()
        if t.type == "KEYWORD" and t.value == "sqrt":
            return self._parse_sqrt()
        if t.type == "KEYWORD" and t.value == "square":
            self.advance()
            if self.peek().type == "KEYWORD" and self.peek().value == "sqrt":
                return self._parse_sqrt()
            base = self.parse_expression(UNARY_BP)
            return PowNode(base=base, exponent=NumNode(value="2"))
        if t.type == "KEYWORD" and t.value == "cube":
            self.advance()
            if self.peek().type == "KEYWORD" and self.peek().value == "sqrt":
                return self._parse_sqrt()
            base = self.parse_expression(UNARY_BP)
            return PowNode(base=base, exponent=NumNode(value="3"))
        self.advance()
        if t.type == "OP" and t.value == "-":
            operand = self.parse_expression(UNARY_BP)
            return UnaryOpNode(op="-", operand=operand)
        if t.type == "NUM":
            return NumNode(value=t.value)
        if t.type == "VAR":
            return VarNode(name=t.value)
        if t.type == "TEXT":
            return VarNode(name=t.value)
        if t.type == "FUNC":
            return self._parse_func(t.value)
        raise ValueError(f"Неожиданный токен в префиксе: {t}")

    def _parse_func(self, name: str) -> ASTNode:
        if self.peek().type == "PAREN_OPEN":
            arg = self._parse_paren()
        else:
            arg = self.parse_expression(FUNC_BP)
            if self.peek().type == "ALL":
                self.advance()
        return FuncNode(name=name, argument=arg)

    def _parse_paren(self) -> ASTNode:
        self.advance()
        inner = self.parse_expression(0)
        if self.peek().type == "PAREN_CLOSE":
            self.advance()
        return inner

    def _parse_frac(self) -> ASTNode:
        self.advance()
        numerator = None
        denominator = None
        if self.peek().type == "KEYWORD" and self.peek().value == "numerator":
            self.advance()
            numerator = self.parse_expression(0)
        if self.peek().type == "KEYWORD" and self.peek().value == "denominator":
            self.advance()
            denominator = self.parse_expression(0)
        if numerator is None:
            numerator = self._parse_until(
                lambda t: t.type in ("SEP", "END", "ALL") or
                         (t.type == "KEYWORD" and t.value == "divide")
            )
        if denominator is None:
            if self.peek().type == "SEP":
                self.advance()
            elif self.peek().type == "KEYWORD" and self.peek().value == "divide":
                self.advance()
                if self.peek().type == "SEP":
                    self.advance()
            denominator = self._parse_until(lambda t: t.type in ("END", "ALL"))
        return FracNode(numerator=numerator, denominator=denominator)

    def _parse_divide(self) -> ASTNode:
        self.advance()
        left = self._parse_until(lambda t: t.type in ("SEP", "END", "ALL"))
        if self.peek().type == "SEP":
            self.advance()
        right = self._parse_until(lambda t: t.type in ("END", "ALL"))
        if isinstance(left, BinOpNode):
            left = ParenNode(inner=left)
        if isinstance(right, BinOpNode):
            right = ParenNode(inner=right)
        if self.peek().type == "ALL":
            self.advance()
        return BinOpNode(left=left, op="/", right=right)

    def _parse_sqrt(self) -> ASTNode:
        self.advance()

        if self.peek().type == "KEYWORD" and self.peek().value == "degree":
            self.advance()
            degree = self._parse_until(lambda t: t.type in ("END", "ALL", "OF"))
            if self.peek().type == "OF":
                self.advance()
            radicand = self.parse_expression(0)
            return RootNode(degree=degree, radicand=radicand)

        if self.peek().type in ("NUM", "VAR"):
            saved_pos = self.pos
            first = self.parse_expression(0)
            if self.peek().type == "KEYWORD" and self.peek().value == "degree":
                self.advance()
                if self.peek().type == "OF":
                    self.advance()
                radicand = self.parse_expression(0)
                return RootNode(degree=first, radicand=radicand)
            self.pos = saved_pos

        if self.peek().type == "KEYWORD" and self.peek().value == "square":
            self.advance()
            if self.peek().type == "OF":
                self.advance()
            radicand = self.parse_expression(0)
            return SqrtNode(radicand=radicand)

        if self.peek().type == "KEYWORD" and self.peek().value == "cube":
            self.advance()
            if self.peek().type == "OF":
                self.advance()
            degree = NumNode(value="3")
            radicand = self.parse_expression(0)
            return RootNode(degree=degree, radicand=radicand)

        if self.peek().type == "KEYWORD" and self.peek().value == "pow":
            self.advance()
            if self.peek().type == "KEYWORD" and self.peek().value == "degree":
                self.advance()
            if self.peek().type == "KEYWORD" and self.peek().value == "square":
                self.advance()
                degree = NumNode(value="2")
            elif self.peek().type == "KEYWORD" and self.peek().value == "cube":
                self.advance()
                degree = NumNode(value="3")
            else:
                degree = self._parse_until(lambda t: t.type in ("END", "ALL", "OF"))
                if self.peek().type == "KEYWORD" and self.peek().value == "degree":
                    self.advance()
            if self.peek().type == "OF":
                self.advance()
            radicand = self.parse_expression(0)
            return RootNode(degree=degree, radicand=radicand)

        if self.peek().type == "OF":
            self.advance()
        radicand = self.parse_expression(0)
        return SqrtNode(radicand=radicand)

    def _parse_until(self, stop_fn: Callable[[Token], bool]) -> ASTNode:
        left = self._parse_atom_for_until()
        while True:
            t = self.peek()
            if stop_fn(t):
                break
            if t.type == "ALL":
                self.advance()
                left = ParenNode(inner=left)
                continue
            if t.type == "OP":
                op = t.value
                entry = BINARY_BP.get(op)
                if entry is None:
                    break
                self.advance()
                right = self._parse_atom_for_until()
                while True:
                    t2 = self.peek()
                    if stop_fn(t2) or t2.type == "END":
                        break
                    if t2.type == "ALL":
                        self.advance()
                        right = ParenNode(inner=right)
                        continue
                    if t2.type == "OP":
                        op2 = t2.value
                        entry2 = BINARY_BP.get(op2)
                        if entry2 is None:
                            break
                        self.advance()
                        right2 = self._parse_atom_for_until()
                        right = BinOpNode(left=right, op=op2, right=right2)
                        continue
                    if self._is_atom(t2):
                        right2 = self._parse_atom_for_until()
                        right = BinOpNode(left=right, op="*", right=right2)
                        continue
                    break
                left = BinOpNode(left=left, op=op, right=right)
                continue
            if t.type == "KEYWORD" and t.value == "divide":
                self.advance()
                if self.peek().type == "SEP":
                    self.advance()
                right = self._parse_atom_for_until()
                if isinstance(right, BinOpNode):
                    right = ParenNode(inner=right)
                left = BinOpNode(left=left, op="/", right=right)
                continue
            if self._is_atom(t):
                right = self._parse_atom_for_until()
                left = BinOpNode(left=left, op="*", right=right)
                continue
            break
        return left

    def _parse_atom_for_until(self) -> ASTNode:
        t = self.peek()
        if t.type == "PAREN_OPEN":
            return self._parse_paren()
        if t.type == "ALL":
            self.advance()
            return VarNode(name="all")
        if t.type == "OF":
            self.advance()
            return self.parse_expression(0)
        if t.type == "KEYWORD" and t.value == "sqrt":
            return self._parse_sqrt()
        if t.type == "KEYWORD" and t.value == "square":
            self.advance()
            if self.peek().type == "KEYWORD" and self.peek().value == "sqrt":
                return self._parse_sqrt()
            base = self.parse_expression(UNARY_BP)
            return PowNode(base=base, exponent=NumNode(value="2"))
        if t.type == "KEYWORD" and t.value == "cube":
            self.advance()
            if self.peek().type == "KEYWORD" and self.peek().value == "sqrt":
                return self._parse_sqrt()
            base = self.parse_expression(UNARY_BP)
            return PowNode(base=base, exponent=NumNode(value="3"))
        if t.type == "KEYWORD" and t.value == "divide":
            return self._parse_divide()
        self.advance()
        if t.type == "OP" and t.value == "-":
            operand = self.parse_expression(UNARY_BP)
            return UnaryOpNode(op="-", operand=operand)

        if t.type == "NUM":
            return NumNode(value=t.value)
        if t.type == "VAR":
            return VarNode(name=t.value)
        if t.type == "TEXT":
            return VarNode(name=t.value)
        if t.type == "FUNC":
            return self._parse_func(t.value)
        raise ValueError(f"Неожиданный токен в _parse_atom_for_until: {t}")
