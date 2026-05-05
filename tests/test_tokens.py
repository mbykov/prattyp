#!/usr/bin/env python3
"""Сравнивает токены нового токенизатора с сохранёнными."""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.registry import load_registry
from src.tokenizer import find_islands, tokenize_island

def main():
    reg = load_registry("ru")

    with open(PROJECT_ROOT / "tests" / "tokens_expected.jsonl", encoding="utf-8") as f:
        expected_tests = [json.loads(line) for line in f]

    passed = 0
    failed = 0

    for test in expected_tests:
        inp = test["input"]
        expected_tokens = test["tokens"]  # список списков [тип, значение]

        islands = find_islands(inp, reg)
        actual_tokens = []
        for isl in islands:
            tokens = tokenize_island(isl, reg)
            actual_tokens.append([[t.type, t.value] for t in tokens])

        if actual_tokens == expected_tokens:
            passed += 1
            print(f"  ✅ {inp}")
        else:
            failed += 1
            print(f"  ❌ {inp}")
            print(f"     expected: {expected_tokens}")
            print(f"     actual:   {actual_tokens}")
            print()

    print(f"\n{'='*60}")
    print(f"✅ Пройдено: {passed}")
    print(f"❌ Упало:   {failed}")
    print(f"📊 Всего:    {len(expected_tests)}")

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
