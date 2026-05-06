"""
Prattyp — голосовой ввод математики в Typst.
"""

import logging
import re
from .registry import load_registry
from .tokenizer import find_islands, tokenize_island, PREPOSITIONS
from .parser import parse
from .generator_typst import generate

logger = logging.getLogger(__name__)


def process(text: str, lang: str = "ru") -> str:
    reg = load_registry(lang)
    words_original = text.split()
    islands = find_islands(text, reg)

    if not islands:
        return text

    # Шаг 1: создаём структуры
    items = []
    for island in islands:
        word0 = island[0].lower()
        is_math = (
            word0 in reg.math_start
            or word0 in PREPOSITIONS
            or word0.isdigit()
            or bool(re.match(r'^\d+\.\d+$', word0))
            or bool(re.match(r'^\d+\.\d+[a-zA-Z]+$', word0))
            or (word0.isascii() and word0.isalpha())
        )
        items.append({
            "input": " ".join(island),
            "math": is_math
        })

    # Шаг 2: обрабатываем математические острова
    for item in items:
        if item["math"]:
            try:
                tokens = tokenize_island(item["input"].lower().split(), reg)
                ast = parse(tokens)
                item["output"] = generate(ast)
            except Exception as e:
                logger.warning("Ошибка в острове «%s»: %s", item["input"], e)
                item["output"] = item["input"]
        else:
            item["output"] = item["input"]

    # Шаг 3: склеиваем
    result = text
    for item in items:
        if item["output"] != item["input"]:
            result = result.replace(item["input"], item["output"], 1)

    return result
