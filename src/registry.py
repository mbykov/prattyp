"""
Загружает словари из i18n/*.json, строит обратные индексы.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Optional, Set


@dataclass
class LangRegistry:
    lang: str
    number_map: Dict[str, int] = field(default_factory=dict)
    var_map: Dict[str, str] = field(default_factory=dict)
    func_map: Dict[str, str] = field(default_factory=dict)
    func_phrases: Dict[str, str] = field(default_factory=dict)
    op_map: Dict[str, str] = field(default_factory=dict)
    keyword_map: Dict[str, str] = field(default_factory=dict)
    all_set: Set[str] = field(default_factory=set)
    math_start: Set[str] = field(default_factory=set)
    math_continue: Set[str] = field(default_factory=set)
    decimal_markers: Dict[str, Optional[int]] = field(default_factory=dict)
    connector_words: Set[str] = field(default_factory=set)
    prep_rules: dict = field(default_factory=dict)


def load_registry(lang: str = "ru") -> LangRegistry:
    i18n_dir = Path(__file__).parent.parent / "i18n"
    path = i18n_dir / f"{lang}.json"

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    reg = LangRegistry(lang=data["lang"])

    numbers = data.get("numbers", {})
    for key, words in numbers.items():
        if key.startswith("decimal_") or key == "decimal_marker":
            continue
        for w in words:
            reg.number_map[w] = int(key)

    for w in numbers.get("decimal_marker", []):
        reg.decimal_markers[w] = None
    for key, divisor in [("decimal_10", 10), ("decimal_100", 100), ("decimal_1000", 1000)]:
        for w in numbers.get(key, []):
            reg.decimal_markers[w] = divisor

    for var, words in data.get("variables", {}).items():
        for w in words:
            reg.var_map[w] = var

    for func, words in data.get("functions", {}).items():
        for w in words:
            reg.func_map[w] = func

    for func_name, phrases in data.get("func_phrases", {}).items():
        for phrase in phrases:
            reg.func_phrases[phrase] = func_name

    for symbol, phrases in data.get("operators", {}).get("binary", {}).items():
        for phrase in phrases:
            reg.op_map[phrase] = symbol

    for kw_type, words in data.get("keywords", {}).items():
        for w in words:
            reg.keyword_map[w] = kw_type

    reg.all_set = set(data.get("all", []))
    reg.prep_rules = data.get("prep_resolution", {})

    connector_words = set(data.get("connectors", []))

    for phrase in reg.op_map.keys():
        for word in phrase.split():
            if word not in reg.number_map and word not in reg.var_map and word not in reg.func_map and word not in reg.keyword_map:
                connector_words.add(word)

    for phrase in reg.func_phrases:
        for word in phrase.split():
            connector_words.add(word)

    reg.connector_words = connector_words

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

    for phrase in reg.func_phrases:
        for word in phrase.split():
            reg.math_start.add(word)
            reg.math_continue.add(word)

    reg.math_start |= {"функция", "извлечь", "деление", "частное", "отношение"}
    reg.math_continue |= {"функция", "извлечь", "деление", "частное", "отношение"}

    math_symbols = {"+", "-", "*", "/", "=", "<", ">", "(", ")"}
    reg.math_start |= math_symbols
    reg.math_continue |= math_symbols

    return reg
