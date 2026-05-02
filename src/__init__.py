"""
Prattyp — голосовой ввод математики в Typst.
"""

from .registry import load_registry
from .tokenizer import find_islands, tokenize_island
from .parser import parse
from .generator_typst import generate


def process(text: str, lang: str = "ru") -> str:
    """
    Полный pipeline: текст → строка Typst.
    Находит все математические острова и заменяет их на Typst-код.
    """
    reg = load_registry(lang)
    islands = find_islands(text, reg)

    if not islands:
        return text

    result = text.lower()
    for island in islands:
        original = " ".join(island)
        tokens = tokenize_island(island, reg)
        ast = parse(tokens)
        typst = generate(ast)
        result = result.replace(original, typst, 1)

    return result
