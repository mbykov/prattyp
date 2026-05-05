#!/usr/bin/env python3
"""Сохраняет токены для всех пройденных тестов."""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import process
from src.registry import load_registry
from src.tokenizer import find_islands, tokenize_island

def main():
    reg = load_registry("ru")
    tests_dir = Path(__file__).parent

    # Собираем все тесты из всех .jsonl
    all_inputs = set()
    for f in sorted(tests_dir.glob("*.jsonl")):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or not line.startswith("{"):
                    break
                try:
                    test = json.loads(line)
                    if "input" in test and "expected" in test and test["input"] and test["expected"]:
                        all_inputs.add(test["input"])
                except json.JSONDecodeError:
                    pass

    results = []
    for inp in sorted(all_inputs):
        try:
            actual = process(inp)
            actual_clean = " ".join(actual.split())
        except:
            actual_clean = None

        # Токенизируем
        islands = find_islands(inp, reg)
        tokens_list = []
        for isl in islands:
            tokens = tokenize_island(isl, reg)
            tokens_list.append([(t.type, t.value) for t in tokens])

        results.append({
            "input": inp,
            "islands": [isl for isl in islands],
            "tokens": tokens_list,
        })

    output = PROJECT_ROOT / "tests" / "tokens_expected.jsonl"
    with open(output, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Saved {len(results)} token sequences to {output}")

if __name__ == "__main__":
    main()
