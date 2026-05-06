"""
Prattyp — голосовой ввод математики в Typst.
"""

import logging
from .registry import load_registry
from .tokenizer import find_islands, tokenize_island
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
        island_lower = " ".join(island).lower()
        items.append({
            "input": " ".join(island),       # оригинальный регистр
            "math": island[0].lower() in reg.math_start
        })

    # Шаг 2: обрабатываем математические острова
    for item in items:
        if item["math"]:
            try:
                # Токенизация по нижнему регистру для matching'а
                tokens = tokenize_island(item["input"].lower().split(), reg)
                ast = parse(tokens)
                item["output"] = generate(ast)
            except Exception as e:
                logger.warning("Ошибка в острове «%s»: %s", item["input"], e)
                item["output"] = item["input"]
        else:
            item["output"] = item["input"]

    # Шаг 3: склеиваем — используем только item["input"] и item["output"]
    result = text
    for item in items:
        if item["output"] != item["input"]:
            result = result.replace(item["input"], item["output"], 1)

    return result
