"""
Загружает словари из i18n/*.json, строит обратные индексы
слово → (тип, значение) для быстрого поиска при токенизации.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Optional, Set


@dataclass
class LangRegistry:
    """Словари одного языка, готовые к использованию токенизатором."""
    lang: str

    number_map: Dict[str, int] = field(default_factory=dict)
    var_map: Dict[str, str] = field(default_factory=dict)
    func_map: Dict[str, str] = field(default_factory=dict)
    op_map: Dict[str, str] = field(default_factory=dict)
    keyword_map: Dict[str, str] = field(default_factory=dict)
    all_set: Set[str] = field(default_factory=set)
    math_start: Set[str] = field(default_factory=set)
    math_continue: Set[str] = field(default_factory=set)
    decimal_markers: Dict[str, Optional[int]] = field(default_factory=dict)
    connector_words: Set[str] = field(default_factory=set)
    frac_separator: Set[str] = field(default_factory=set)


def load_registry(lang: str = "ru") -> LangRegistry:
    """Загружает языковой пакет из i18n/<lang>.json."""
    i18n_dir = Path(__file__).parent.parent / "i18n"
    path = i18n_dir / f"{lang}.json"

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    reg = LangRegistry(lang=data["lang"])

    # ── Числа ──────────────────────────────────────────
    numbers = data.get("numbers", {})
    for key, words in numbers.items():
        if key.startswith("decimal_"):
            continue
        if key == "decimal_marker":
            continue
        value = int(key)
        for w in words:
            reg.number_map[w] = value

    # ── Десятичные маркеры ─────────────────────────────
    for w in numbers.get("decimal_marker", []):
        reg.decimal_markers[w] = None
    for key, divisor in [("decimal_10", 10), ("decimal_100", 100), ("decimal_1000", 1000)]:
        for w in numbers.get(key, []):
            reg.decimal_markers[w] = divisor

    # ── Переменные ─────────────────────────────────────
    for var, words in data.get("variables", {}).items():
        for w in words:
            reg.var_map[w] = var

    # ── Функции ────────────────────────────────────────
    for func, words in data.get("functions", {}).items():
        for w in words:
            reg.func_map[w] = func

    # ── Операторы ──────────────────────────────────────
    for symbol, phrases in data.get("operators", {}).get("binary", {}).items():
        for phrase in phrases:
            reg.op_map[phrase] = symbol

    # ── Ключевые слова (frac, divide, paren_open, paren_close, paren_auto) ──
    for kw_type, words in data.get("keywords", {}).items():
        for w in words:
            reg.keyword_map[w] = kw_type

    # ── All ────────────────────────────────────────────
    reg.all_set = set(data.get("all", []))

    # ── Разделитель для frac ───────────────────────────
    reg.frac_separator = {"на"}

    # ── Слова-связки ───────────────────────────────────
    connector_words: Set[str] = set()
    for phrase in reg.op_map.keys():
        for word in phrase.split():
            if (
                word not in reg.number_map
                and word not in reg.var_map
                and word not in reg.func_map
                and word not in reg.decimal_markers
                and word not in reg.keyword_map
                and word not in reg.all_set
            ):
                connector_words.add(word)
    connector_words |= reg.frac_separator
    for w in data.get("connectors", []):
        connector_words.add(w)
    reg.connector_words = connector_words

    # ── Множества для поиска островов ──────────────────
    reg.math_start = (
        set(reg.number_map.keys())
        | set(reg.var_map.keys())
        | set(reg.func_map.keys())
        | set(reg.decimal_markers.keys())
        | set(reg.keyword_map.keys())
        | reg.all_set
        | {"минус"}
    )

    reg.math_continue = (
        reg.math_start
        | set(reg.op_map.keys())
        | reg.all_set
        | connector_words
    )

    # ── Символы операторов (fallback для внешнего препроцессора) ──
    math_symbols = {"+", "-", "*", "/", "=", "<", ">", "(", ")"}
    reg.math_start |= math_symbols
    reg.math_continue |= math_symbols

    return reg
