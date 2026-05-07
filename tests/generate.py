import json
import random
import re
import argparse
import os

class TestGenerator:
    def __init__(self, templates_path):
        with open(templates_path, 'r', encoding='utf-8') as f:
            self.templates = json.load(f)

        self.phonetic_map = {
            'a': 'а', 'b': 'бэ', 'c': 'цэ', 'd': 'дэ', 'f': 'эф', 'g': 'же', 'h': 'аш',
            'i': 'и', 'j': 'жи', 'k': 'ка', 'l': 'эль', 'm': 'эм', 'n': 'эн',
            'p': 'пэ', 'q': 'ку', 'r': 'эр', 's': 'эс', 't': 'тэ',
            'u': 'у', 'v': 'вэ', 'w': 'дубль-вэ', 'x': 'икс', 'y': 'игрек', 'z': 'зет'
        }

    def get_phonetic(self, letter):
        return self.phonetic_map.get(letter, letter)

    def fill_pattern(self, pattern, sym):
        # Variable pools
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
                new_r = random.choice(available)
                selected_rands.append(new_r)
                return self.get_phonetic(new_r)
            return token

        if "N-того" in res_input:
            res_input = res_input.replace("N-того", f"{self.get_phonetic(n_let)}-того")

        res_input = re.sub(r"RAND|VAR|N", replace_token, res_input)
        res_input = res_input.replace("(", " скобка ").replace(")", " скобка ")

        # --- Expected Output Generation ---
        current_v = n_let if "seq" in sym else v_let
        f_name = selected_rands[0] if len(selected_rands) > 0 else "f"

        if "бесконечности" in res_input:
            sign = "-" if "минус" in res_input else "+" if "плюс" in res_input else ""
            target = f"{sign}infinity"
            result_val = selected_rands[1] if len(selected_rands) > 1 else None
        else:
            target = selected_rands[1] if len(selected_rands) > 1 else "a"
            if "слева" in res_input: target = f"{target}^-"
            elif "справа" in res_input: target = f"{target}^+"
            result_val = selected_rands[2] if len(selected_rands) > 2 else None

        if "seq" in sym:
            exp = f"lim_({current_v} -> {target}) {f_name}_{current_v}"
        else:
            exp = f"lim_({current_v} -> {target}) {f_name}({current_v})"

        if "равен" in res_input and result_val:
            exp += f" = {result_val}"

        return {"input": res_input, "expected": exp}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--term', default='sin')
    parser.add_argument('--size', type=int, default=1) # Default iterations per pattern
    parser.add_argument('--lang', default='ru')
    args = parser.parse_args()

    template_file = f"i18n/templates_{args.lang}.json"
    output_file = f"tests/data/{args.term}.jsonl"
    os.makedirs('tests', exist_ok=True)

    if not os.path.exists(template_file):
        print(f"File not found: {template_file}")
        return

    gen = TestGenerator(template_file)

    # Filter templates matching the term (e.g., 'lim_func', 'lim_seq')
    matched_templates = [t for t in gen.templates if t.get('sym', '').startswith(args.term)]

    with open(output_file, 'w', encoding='utf-8') as f:
        total_count = 0
        for tmpl in matched_templates:
            for pattern in tmpl.get("patterns", []):
                # Generate 'size' variations for EACH pattern in the list
                for _ in range(args.size):
                    test = gen.fill_pattern(pattern, tmpl["sym"])
                    f.write(json.dumps(test, ensure_ascii=False) + '\n')
                    total_count += 1

    print(f"Done. Processed {len(matched_templates)} templates. Total tests: {total_count}")

if __name__ == "__main__":
    main()
