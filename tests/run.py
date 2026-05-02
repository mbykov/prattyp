#!/usr/bin/env python3
"""
Prattyp Test Runner
Загружает все .jsonl файлы из tests/, прогоняет pipeline, выводит результат.

Использование:
  uv run tests/run.py                  # все .jsonl в tests/
  uv run tests/run.py --clip           # копировать упавшие + диагностику в буфер
  uv run tests/run.py --file frac.jsonl  # только указанный файл
"""

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src import process
from src.registry import load_registry
from src.tokenizer import find_islands, tokenize_island
from src.parser import parse
from src.generator_typst import generate as generate_typst


def copy_to_clipboard(text: str) -> bool:
    try:
        proc = subprocess.Popen(
            ["xclip", "-selection", "clipboard"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.communicate(input=text.encode("utf-8"), timeout=3)
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        try:
            proc.kill()
        except Exception:
            pass
        return False


def load_tests(path: Path) -> list[dict]:
    tests = []
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                test = json.loads(line)
                if "input" in test and "expected" in test:
                    tests.append(test)
            except json.JSONDecodeError:
                pass
    return tests


def load_all_tests(tests_dir: Path) -> list[tuple[str, list[dict]]]:
    """Загружает все .jsonl файлы из tests/ (без вложенных папок)."""
    all_tests = []
    for f in sorted(tests_dir.glob("*.jsonl")):
        file_tests = load_tests(f)
        if file_tests:
            all_tests.append((f.name, file_tests))
    return all_tests


def run_test(test: dict, test_num: int) -> tuple[bool, str, str, str]:
    voice_input = test["input"]
    expected = test["expected"]

    try:
        actual = process(voice_input)
        actual_clean = " ".join(actual.split())
        expected_clean = " ".join(expected.split())
    except Exception as e:
        return False, voice_input, expected, f"ОШИБКА: {e}"

    return (actual_clean == expected_clean), voice_input, expected, actual_clean


def diagnose(voice_input: str) -> str:
    reg = load_registry("ru")
    lines = []
    lines.append(f"🔍 Диагностика: «{voice_input}»")
    islands = find_islands(voice_input, reg)
    lines.append(f"Острова: {islands}")
    for idx, isl in enumerate(islands):
        lines.append(f"── Остров {idx}: {isl}")
        try:
            tokens = tokenize_island(isl, reg)
            lines.append(f"   Токены: {tokens}")
            ast = parse(tokens)
            lines.append(f"   AST: {ast}")
            result = generate_typst(ast)
            lines.append(f"   Результат: {result}")
        except Exception as e:
            lines.append(f"   ОШИБКА: {e}")
    return "\n".join(lines)


def main():
    use_clip = "--clip" in sys.argv

    # Обработка --file
    test_file_arg = None
    for i, arg in enumerate(sys.argv):
        if arg == "--file" and i + 1 < len(sys.argv):
            test_file_arg = sys.argv[i + 1]
            break

    tests_dir = Path(__file__).parent

    if test_file_arg:
        test_file = Path(test_file_arg)
        if not test_file.is_absolute():
            test_file = tests_dir / test_file
        test_suites = [(test_file.name, load_tests(test_file))]
    else:
        test_suites = load_all_tests(tests_dir)

    if not test_suites:
        print("❌ Нет тестов для запуска.")
        return 1

    total_passed = 0
    total_failed = 0
    total_count = 0
    all_failed_blocks = []

    for file_name, tests in test_suites:
        print("=" * 60)
        print(f"📂 {file_name}  ({len(tests)} тестов)")
        print("=" * 60)

        passed = 0
        failed = 0

        for i, test in enumerate(tests, 1):
            ok, voice, expected, actual = run_test(test, i)

            if ok:
                passed += 1
                print(f"  ✅ тест {i:02d}: {voice} → {expected}")
            else:
                failed += 1
                block = []
                block.append(f"❌ {file_name} тест {i:02d}: {voice}")
                block.append(f"   ожидал:  {expected}")
                block.append(f"   получил: {actual}")

                print(f"  ❌ тест {i:02d}: FAIL")
                print(f"     вход:    {voice}")
                print(f"     ожидал:  {expected}")
                print(f"     получил: {actual}")

                diag = diagnose(voice)
                print(diag)
                print()
                block.append(diag)

                all_failed_blocks.append("\n".join(block))

        total_passed += passed
        total_failed += failed
        total_count += len(tests)

        print(f"   ── {file_name}: ✅ {passed}  ❌ {failed}")
        print()

    print("=" * 60)
    print(f"✅ Пройдено: {total_passed}")
    print(f"❌ Упало:   {total_failed}")
    print(f"📊 Всего:    {total_count}")
    print("=" * 60)

    if use_clip and total_failed > 0:
        clip_text = "\n\n".join(all_failed_blocks) + "\n\n" + "=" * 60 + "\n" + f"✅ Пройдено: {total_passed}\n❌ Упало:   {total_failed}\n📊 Всего:    {total_count}\n" + "=" * 60
        if copy_to_clipboard(clip_text):
            print("\n📋 Упавшие тесты с диагностикой скопированы в буфер.")
        else:
            print("\n⚠ Не удалось скопировать в буфер.")

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
