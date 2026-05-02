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

    # word → numeric value
    number_map: Dict[str, int] = field(default_factory=dict)

    # word → variable name
    var_map: Dict[str, str] = field(default_factory=dict)

    # word → function name
    func_map: Dict[str, str] = field(default_factory=dict)

    # multi-word phrase → operator symbol
    op_map: Dict[str, str] = field(default_factory=dict)

    # word → keyword type (frac, divide, sqrt, root, ...)
    keyword_map: Dict[str, str] = field(default_factory=dict)

    # set of "all" words
    all_set: Set[str] = field(default_factory=set)

    # set of math-starting words
    math_start: Set[str] = field(default_factory=set)

    # set of math-continuing words
    math_continue: Set[str] = field(default_factory=set)

    # decimal: "целых" → None, "десятых" → 10, "сотых" → 100, "тысячных" → 1000
    decimal_markers: Dict[str, Optional[int]] = field(default_factory=dict)

    # слова-связки из составных операторов и ключевых фраз
    connector_words: Set[str] = field(default_factory=set)

    # слова-разделители для frac/divide: "на" в "дробь ... на ..."
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

    # ── Ключевые слова (frac, divide, sqrt, root...) ───
    for kw_type, words in data.get("keywords", {}).items():
        for w in words:
            reg.keyword_map[w] = kw_type

    # ── All ────────────────────────────────────────────
    reg.all_set = set(data.get("all", []))

    # ── Разделитель для frac: "на" ─────────────────────
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
            ):
                connector_words.add(word)
    # Добавляем разделители frac
    connector_words |= reg.frac_separator
    reg.connector_words = connector_words

    # ── Множества для поиска островов ──────────────────
    reg.math_start = (
        set(reg.number_map.keys())
        | set(reg.var_map.keys())
        | set(reg.func_map.keys())
        | set(reg.decimal_markers.keys())
        | set(reg.keyword_map.keys())
        | {"минус"}
    )

    reg.math_continue = (
        reg.math_start
        | set(reg.op_map.keys())
        | reg.all_set
        | connector_words
    )

    return reg
