"""
Prattyp Tokenizer v8
Не содержит кириллицы — все слова приходят из LangRegistry.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
from .registry import LangRegistry


@dataclass(frozen=True)
class Token:
    type: str      # NUM, VAR, FUNC, OP, ALL, KEYWORD, SEP, PAREN_OPEN, PAREN_CLOSE, END
    value: str     # нормализованное: "123", "x", "sin", "+", "all", "frac", "на", "(", ")"


def find_islands(text: str, reg: LangRegistry) -> List[List[str]]:
    words = text.lower().split()
    islands: List[List[str]] = []
    current: Optional[List[str]] = None

    for word in words:
        is_math_word = (
            word in reg.math_start
            or word.isdigit()
            or (word.isascii() and word.isalpha())
        )
        is_continue_word = (
            word in reg.math_continue
            or word.isdigit()
            or (word.isascii() and word.isalpha())
        )

        if is_math_word and current is None:
            current = [word]
        elif is_continue_word and current is not None:
            current.append(word)
        else:
            if current is not None:
                islands.append(current)
                current = None

    if current is not None:
        islands.append(current)

    return islands


def tokenize_island(words: List[str], reg: LangRegistry) -> List[Token]:
    tokens: List[Token] = []
    i = 0
    n = len(words)
    paren_counter = 0

    while i < n:
        word = words[i]

        # ── число из словаря ──
        if word in reg.number_map or word in reg.decimal_markers:
            num_tokens, advance = _parse_number(words, i, reg)
            tokens.extend(num_tokens)
            i += advance
            continue

        # ── all ──
        if word in reg.all_set:
            tokens.append(Token("ALL", "all"))
            i += 1
            continue

        # ── ключевое слово ──
        if word in reg.keyword_map:
            kw_type = reg.keyword_map[word]

            if kw_type == "paren_open":
                paren_counter += 1
                tokens.append(Token("PAREN_OPEN", "("))
            elif kw_type == "paren_close":
                tokens.append(Token("PAREN_CLOSE", ")"))
            elif kw_type == "paren_auto":
                paren_counter += 1
                if paren_counter % 2 == 1:
                    tokens.append(Token("PAREN_OPEN", "("))
                else:
                    tokens.append(Token("PAREN_CLOSE", ")"))
            else:
                tokens.append(Token("KEYWORD", kw_type))
            i += 1
            continue

        # ── разделитель frac ("на") ──
        if word in reg.frac_separator:
            tokens.append(Token("SEP", "на"))
            i += 1
            continue

        # ── функция ──
        if word in reg.func_map:
            tokens.append(Token("FUNC", reg.func_map[word]))
            i += 1
            continue

        # ── переменная ──
        if word in reg.var_map:
            tokens.append(Token("VAR", reg.var_map[word]))
            i += 1
            continue

        # ── оператор ──
        op_token, advance = _try_match_op(words, i, reg)
        if op_token is not None:
            tokens.append(op_token)
            i += advance
            continue

        # ── слово-связка ──
        if word in reg.connector_words:
            i += 1
            continue

        # ── символы операторов (fallback) ──
        if word in {"+", "-", "*", "/", "=", "<", ">", "<=", ">=", "==", "!="}:
            tokens.append(Token("OP", word))
            i += 1
            continue

        # ── скобки символами (fallback) ──
        if word == "(":
            tokens.append(Token("PAREN_OPEN", "("))
            i += 1
            continue
        if word == ")":
            tokens.append(Token("PAREN_CLOSE", ")"))
            i += 1
            continue

        # ── цифры (fallback) ──
        if word.isdigit():
            tokens.append(Token("NUM", word))
            i += 1
            continue

        # ── латиница (fallback) ──
        if word.isascii() and word.isalpha():
            tokens.append(Token("VAR", word.lower()))
            i += 1
            continue

        # ── неизвестное ──
        print(f"⚠ Неизвестное слово в острове: {word}")
        i += 1

    tokens.append(Token("END", ""))
    return tokens


def _try_match_op(words: List[str], i: int, reg: LangRegistry) -> Tuple[Optional[Token], int]:
    candidates = sorted(reg.op_map.keys(), key=len, reverse=True)
    for phrase in candidates:
        phrase_words = phrase.split()
        if words[i : i + len(phrase_words)] == phrase_words:
            return Token("OP", reg.op_map[phrase]), len(phrase_words)
    return None, 0


def _parse_number(words: List[str], start: int, reg: LangRegistry) -> Tuple[List[Token], int]:
    i = start
    integer_part = 0
    decimal_value = 0
    decimal_divisor = 1
    in_decimal = False

    while i < len(words):
        word = words[i]

        if word in reg.decimal_markers and reg.decimal_markers[word] is None:
            in_decimal = True
            i += 1
            continue

        if word in reg.decimal_markers and reg.decimal_markers[word] is not None:
            decimal_divisor = reg.decimal_markers[word]
            i += 1
            break

        if word not in reg.number_map:
            break

        value = reg.number_map[word]

        if in_decimal:
            if value >= 100:
                decimal_value += value
            elif value >= 20:
                decimal_value += value
            else:
                decimal_value = decimal_value * 10 + value
        else:
            if value >= 1000:
                integer_part = (integer_part or 1) * value
            elif value >= 100:
                integer_part += value
            elif value >= 20:
                integer_part += value
            else:
                integer_part += value
        i += 1

    if in_decimal and decimal_divisor > 1:
        result = integer_part + decimal_value / decimal_divisor
    elif in_decimal and decimal_value > 0:
        digits = len(str(decimal_value))
        result = integer_part + decimal_value / (10 ** digits)
    else:
        result = integer_part

    if result == int(result):
        result_str = str(int(result))
    else:
        result_str = f"{result}"

    return [Token("NUM", result_str)], i - start
