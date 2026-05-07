"""
Prattyp Tokenizer v15 — PREP + контекстное разрешение, func_phrases для исключений.
"""

import re
from typing import List, Optional, Tuple
from .registry import LangRegistry

import logging
logger = logging.getLogger(__name__)


class Token:
    def __init__(self, type: str, value: str):
        self.type = type
        self.value = value

    def __repr__(self):
        return f"Token(type='{self.type}', value='{self.value}')"

    def __eq__(self, other):
        return self.type == other.type and self.value == other.value


def find_islands(text: str, reg: LangRegistry) -> List[List[str]]:
    words_lower = text.lower().split()
    words_original = text.split()
    islands: List[List[str]] = []
    current: Optional[List[str]] = None
    in_quote = False
    quote_words = {w for w in reg.keyword_map if reg.keyword_map[w] == "quote"}

    for i, word_lower in enumerate(words_lower):
        word_original = words_original[i]

        # Quote переключатель
        if word_lower in quote_words:
            in_quote = not in_quote
            if current is None:
                current = [word_original]
            else:
                current.append(word_original)
            continue

        # Внутри quote — всё продолжает остров
        if in_quote:
            current.append(word_original)
            continue

        is_math = (
            word_lower in reg.math_start
            or word_lower in reg.prepositions
            or word_lower.isdigit()
            or bool(re.match(r'^\d+\.\d+$', word_lower))
            or bool(re.match(r'^\d+\.\d+[a-zA-Z]+$', word_lower))
            or (word_lower.isascii() and word_lower.isalpha())
        )
        is_cont = (
            word_lower in reg.math_continue
            or word_lower in reg.prepositions
            or word_lower.isdigit()
            or bool(re.match(r'^\d+\.\d+$', word_lower))
            or bool(re.match(r'^\d+\.\d+[a-zA-Z]+$', word_lower))
            or (word_lower.isascii() and word_lower.isalpha())
        )

        if is_math and current is None:
            current = [word_original]
        elif is_cont and current is not None:
            current.append(word_original)
        else:
            if current is not None:
                islands.append(current)
                current = None

    if current is not None:
        islands.append(current)

    return islands


def tokenize_island(words: List[str], reg: LangRegistry) -> List[Token]:
    from .lib.prepositions import resolve_prepositions

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

        # ── многословная функция ──
        func_token, advance = _try_match_func(words, i, reg)
        if func_token is not None:
            tokens.append(func_token)
            i += advance
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
            elif kw_type == "quote":
                quote_parts = []
                i += 1
                while i < n:
                    if words[i] in reg.keyword_map and reg.keyword_map[words[i]] == "quote":
                        i += 1
                        break
                    quote_parts.append(words[i])
                    i += 1
                var_name = " ".join(quote_parts)
                tokens.append(Token("VAR", var_name))
                continue
            elif kw_type == "diff":
                tokens.append(Token("SEP", "дэ"))
            else:
                tokens.append(Token("KEYWORD", kw_type))

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
        # print(f"DEBUG tokenize: word='{word}' at {i}, calling _try_match_op")
        op_token, advance = _try_match_op(words, i, reg)
        if op_token is not None:
            # print(f"DEBUG tokenize: GOT {op_token}")
            tokens.append(op_token)
            i += advance
            continue

        # ── PREP (до connectors!) ──
        if word in reg.prepositions:
            tokens.append(Token("PREP", word))
            i += 1
            continue

        # ── слово-связка ──
        if word in reg.connector_words:
            i += 1
            continue

        # ── символы операторов ──
        if word in {"+", "-", "*", "/", "=", "<", ">", "<=", ">=", "==", "!="}:
            tokens.append(Token("OP", word))
            i += 1
            continue

        # ── скобки символами ──
        if word == "(":
            tokens.append(Token("PAREN_OPEN", "("))
            i += 1
            continue
        if word == ")":
            tokens.append(Token("PAREN_CLOSE", ")"))
            i += 1
            continue

        # ── float ──
        if re.match(r'^\d+\.\d+$', word):
            tokens.append(Token("NUM", word))
            i += 1
            continue

        # ── float + буква ──
        m = re.match(r'^(\d+\.\d+)([a-zA-Z]+)$', word)
        if m:
            tokens.append(Token("NUM", m.group(1)))
            tokens.append(Token("VAR", m.group(2).lower()))
            i += 1
            continue

        # ── цифры ──
        if word.isdigit():
            tokens.append(Token("NUM", word))
            i += 1
            continue

        # ── латиница ──
        if word.isascii() and word.isalpha():
            tokens.append(Token("VAR", word.lower()))
            i += 1
            continue

        logger.warning("Неизвестное слово в острове: %s", word)
        tokens.append(Token("TEXT", word))
        i += 1
        continue

    tokens.append(Token("END", ""))
    tokens = resolve_prepositions(tokens, reg.prep_rules)
    return tokens


def _try_match_func(words, i, reg):
    candidates = sorted(reg.func_phrases.keys(), key=len, reverse=True)
    for phrase in candidates:
        phrase_words = phrase.split()
        if words[i : i + len(phrase_words)] == phrase_words:
            return Token("FUNC", reg.func_phrases[phrase]), len(phrase_words)
    return None, 0


def _try_match_op(words, i, reg):
    candidates = sorted(reg.op_map.keys(), key=len, reverse=True)
    for phrase in candidates:
        phrase_words = phrase.split()
        if words[i : i + len(phrase_words)] == phrase_words:
            return Token("OP", reg.op_map[phrase]), len(phrase_words)
    # print(f"DEBUG _try_match_op: no match for '{words[i]}' at {i}, candidates: {list(candidates)[:5]}")
    return None, 0


def _parse_number(words, start, reg):
    i = start
    integer_part = 0
    decimal_value = 0
    decimal_digits = 0
    in_decimal = False

    while i < len(words):
        word = words[i]

        if word in reg.decimal_markers and reg.decimal_markers[word] is None:
            in_decimal = True
            i += 1
            continue

        if word in reg.decimal_markers and reg.decimal_markers[word] is not None:
            divisor = reg.decimal_markers[word]
            i += 1
            decimal_digits = len(str(divisor)) - 1
            result = integer_part + decimal_value / divisor
            result_str = f"{result:.{decimal_digits}f}" if decimal_digits > 0 else str(int(result))
            return [Token("NUM", result_str)], i - start

        if word not in reg.number_map:
            break

        value = reg.number_map[word]

        if in_decimal:
            decimal_value = decimal_value * 10 + value
            decimal_digits += 1
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

    if in_decimal and decimal_digits > 0:
        result_str = f"{integer_part}.{str(decimal_value).zfill(decimal_digits)}"
    else:
        result_str = str(integer_part)

    return [Token("NUM", result_str)], i - start
