import json
import random
import re
import argparse
import os

class TestGenerator:
    def __init__(self, templates_path):
        with open(templates_path, 'r', encoding='utf-8') as f:
            raw_templates = json.load(f)

        self.templates = []
        for tmpl in raw_templates:
            tmpl['patterns'] = [p for p in tmpl.get('patterns', []) if not p.strip().startswith('_')]
            if 'special_cases' in tmpl:
                filtered_cases = []
                for case in tmpl['special_cases']:
                    case['patterns'] = [p for p in case.get('patterns', []) if not p.strip().startswith('_')]
                    if case['patterns']:
                        filtered_cases.append(case)
                tmpl['special_cases'] = filtered_cases
            self.templates.append(tmpl)

        self.phonetic_map = {
            'a': 'а', 'b': 'бэ', 'c': 'цэ',  'f': 'эф', 'g': 'же', 'h': 'аш',
            'i': 'и', 'j': 'жи', 'k': 'ка', 'l': 'эль', 'm': 'эм', 'n': 'эн',
            'p': 'пэ', 'q': 'ку', 'r': 'эр', 's': 'эс', 't': 'тэ',
            'u': 'у', 'v': 'вэ', 'w': 'дубль-вэ', 'x': 'икс', 'y': 'игрек', 'z': 'зет'
        }

    def get_phonetic(self, letter):
        return self.phonetic_map.get(letter, letter)

    def fill_pattern(self, pattern, sym):
        n_pool = ['n', 'm', 'i', 'j', 'k', 'l']
        var_pool = ['x', 'y', 'z', 't']
        rand_pool = [l for l in self.phonetic_map.keys() if l not in n_pool and l not in var_pool]

        v_let = random.choice(var_pool)
        n_let = random.choice(n_pool)

        res_input = pattern
        selected_rands = []

        def replace_token(match):
            token = match.group(0)
            if token == "VAR": return self.get_phonetic(v_let)
            if token == "N": return self.get_phonetic(n_let)
            if token == "RAND":
                exclude = [v_let, n_let] + selected_rands
                available = [l for l in rand_pool if l not in exclude]
                new_r = random.choice(available) if available else 'a'
                selected_rands.append(new_r)
                return self.get_phonetic(new_r)
            return token

        if "N-того" in res_input:
            res_input = res_input.replace("N-того", f"{self.get_phonetic(n_let)}-того")

        res_input = re.sub(r"RAND|VAR|N", replace_token, res_input)
        res_input = res_input.replace("(", " скобка ").replace(")", " скобка ")
        res_input = res_input.replace(",", "")

        f_name = selected_rands[0] if len(selected_rands) > 0 else "f"

        if "seq" in sym:
            var_latin = n_let
        else:
            var_latin = v_let

        # Цель — берём из RAND перед "равен" или из последнего RAND
        target = "a"

        # Находим индекс "равен" и "к"
        idx_equals = res_input.find("равен") if "равен" in res_input else -1
        idx_k = res_input.rfind(" к ")  # последнее "к"

        if "бесконечности" in res_input:
            if "минус" in res_input:
                target = "-inf"
            else:
                target = "inf"
        elif "нулю" in res_input:
            target = "0"
        elif len(selected_rands) >= 2:
            # Если "равен" ДО "к" — цель = selected_rands[1]
            # Если "к" ДО "равен" — цель = selected_rands[1]
            # В общем случае цель = selected_rands[1] (не последний)
            target = selected_rands[1] if len(selected_rands) > 1 else "a"

        result_val = None
        has_equals = "равен" in res_input

        # Для равенства: значение ПОСЛЕ "равен"
        if has_equals:
            # Если "равен" после "к", результат = последний RAND
            if idx_k >= 0 and idx_equals > idx_k:
                result_val = selected_rands[-1] if len(selected_rands) > 2 else None
            # Если "равен" до "к" (до condition), равенство теряется
            elif "при" in res_input and idx_equals < res_input.find("при"):
                result_val = None

        has_func_arg = any(word in res_input for word in [" от ", " скобка "])
        is_context = "в бесконечности" in res_input or "в точке" in res_input

        # Собираем expected
        if "seq" in sym:
            exp = f"lim_({var_latin} -> {target}) {f_name}_{var_latin}"
        else:
            if has_func_arg:
                exp = f"lim_({var_latin} -> {target}) {f_name}({var_latin})"
            else:
                if is_context:
                    exp = f"lim_({target} -> {target}) {f_name}"
                else:
                    exp = f"lim_({var_latin} -> {target}) {f_name}"

        # Равенство: только если "равен" ПОСЛЕ "к" и ПОСЛЕ "при"
        if has_equals and result_val:
            if "при" in res_input and res_input.find("равен") > res_input.find("при"):
                exp += f" = {result_val}"
            elif "сторон" in res_input and res_input.find("равен") > res_input.find("сторон"):
                exp += f" = {result_val}"

        return {"input": res_input, "expected": exp}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--term', default='sin')
    parser.add_argument('--size', type=int, default=1)
    parser.add_argument('--lang', default='ru')
    args = parser.parse_args()

    template_file = f"i18n/templates_{args.lang}.json"
    output_file = f"tests/data/{args.term}.jsonl"
    os.makedirs('tests/data', exist_ok=True)

    if not os.path.exists(template_file):
        print(f"File not found: {template_file}")
        return

    gen = TestGenerator(template_file)
    matched_templates = [t for t in gen.templates if t.get('sym', '').startswith(args.term)]

    with open(output_file, 'w', encoding='utf-8') as f:
        total_count = 0
        for tmpl in matched_templates:
            for pattern in tmpl.get("patterns", []):
                if pattern.strip().startswith("_"):
                    continue
                for _ in range(args.size):
                    test = gen.fill_pattern(pattern, tmpl["sym"])
                    f.write(json.dumps(test, ensure_ascii=False) + '\n')
                    total_count += 1

    print(f"Done. Processed {len(matched_templates)} templates. Total tests: {total_count}")


if __name__ == "__main__":
    main()
