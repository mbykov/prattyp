import json
import random
import argparse
import os

class TestGenerator:
    def __init__(self, lang, templates_path):
        with open(templates_path, 'r', encoding='utf-8') as f:
            raw_templates = json.load(f)

        self.templates = []
        for tmpl in raw_templates:
            tmpl['patterns'] = [p for p in tmpl.get('patterns', []) if not p.startswith('_')]
            if 'special_cases' in tmpl:
                filtered_cases = []
                for case in tmpl['special_cases']:
                    case['patterns'] = [p for p in case.get('patterns', []) if not p.startswith('_')]
                    if case['patterns']:
                        filtered_cases.append(case)
                tmpl['special_cases'] = filtered_cases
            if tmpl['patterns'] or tmpl.get('special_cases'):
                self.templates.append(tmpl)

        self.lang = lang
        self.arithm_ops = [
            {"in": " плюс ", "exp": " + "},
            {"in": " минус ", "exp": " - "},
            {"in": " умножить на ", "exp": " * "}
        ]

        self.num_map = {"0": "ноль", "1": "один", "2": "два", "3": "три", "4": "четыре",
                        "5": "пять", "6": "шесть", "7": "семь", "8": "восемь", "9": "девять"}

    def generate_verbal_number(self):
        int_part = str(random.randint(0, 9))
        frac_part = "".join([str(random.randint(0, 9)) for _ in range(random.randint(1, 2))])

        int_word = self.num_map[int_part]
        frac_words = " ".join([self.num_map[d] for d in frac_part])

        style = random.random()
        if style < 0.3:
            inp = f"{int_word} точка {frac_words}"
        elif style < 0.6:
            inp = f"{int_word} целых {frac_words}"
        else:
            suffix = "десятых" if len(frac_part) == 1 else "сотых"
            inp = f"{int_word} целых {frac_words} {suffix}"

        return {"input": inp, "expected": f"{int_part}.{frac_part}"}

    def get_simple_var(self):
        v_names = ['a', 'b', 'c', 'x', 'y', 'z', 't', 'n']
        name = random.choice(v_names)
        roll = random.random()

        if roll < 0.3:
            return self.generate_verbal_number()
        if roll < 0.6:
            num = self.generate_verbal_number()
            return {"input": f"{num['input']} {name}", "expected": f"{num['expected']} * {name}"}
        if roll < 0.8:
            name2 = random.choice([v for v in v_names if v != name])
            return {"input": f"{name} {name2}", "expected": f"{name} * {name2}"}

        return {"input": name, "expected": name}

    def generate_expr(self, depth=0, simple=False):
        if simple or depth > 2 or (random.random() < 0.2):
            return self.get_simple_var()
        tmpl = random.choice(self.templates)
        return self.fill_template(tmpl, depth, simple)

    def _needs_parens(self, expr):
        """Проверяет, нужно ли оборачивать выражение в скобки."""
        return any(op in expr for op in [" + ", " - ", " * ", " / "])

    def fill_template(self, tmpl, depth, simple):
        sym = tmpl["sym"]

        # Обработка special_cases
        if "special_cases" in tmpl and tmpl["special_cases"] and random.random() < 0.5:
            case = random.choice(tmpl["special_cases"])
            pattern = random.choice(case["patterns"])
            val_const = case.get("deg") or case.get("pow")
            arg = self.generate_expr(depth + 1, simple)

            inp = pattern.replace("VAR", arg["input"])
            arg_exp = arg["expected"]

            if self._needs_parens(arg_exp):
                inp = inp.replace(arg["input"], f"скобка {arg['input']} скобка")
                arg_exp = f"({arg_exp})"

            if sym == "^":
                exp = f"{arg_exp}^{val_const}"
            elif sym == "root":
                exp = f"root({val_const}, {arg['expected']})"
            elif sym == "/":
                # special case для деления — просто аргумент (второго нет)
                exp = arg_exp
            else:
                exp = f"{sym}({arg['expected']})"

            return {"input": inp, "expected": exp}

        pattern = random.choice(tmpl["patterns"])
        res_input = pattern
        args_expected = []
        args_input = []

        while "VAR" in res_input:
            arg = self.generate_expr(depth + 1, simple)
            args_input.append(arg["input"])
            args_expected.append(arg["expected"])
            res_input = res_input.replace("VAR", arg["input"], 1)

        const_val = None
        for label in ["DEG", "POW"]:
            if label in res_input:
                const_val = random.choice(["2", "3", "n", "k", "5"])
                res_input = res_input.replace(label, const_val)

        # Вычисление expected
        if sym == "sqrt" and any(word in pattern for word in ["степен", "одна вторая", "ноль"]):
            base = args_expected[0] if args_expected else "x"
            if self._needs_parens(base):
                base_str = f"({base})"
                var_input = args_input[0] if args_input else ""
                if var_input:
                    res_input = res_input.replace(var_input, f"скобка {var_input} скобка", 1)
            else:
                base_str = base
            exp = f"{base_str}^(0.5)"
        elif sym == "frac":
            a, b = (args_expected + ["a", "b"])[:2]
            exp = f"frac({a}, {b})"
        elif sym == "/":
            a, b = (args_expected + ["a", "b"])[:2]
            a_str = f"({a})" if self._needs_parens(a) else a
            b_str = f"({b})" if self._needs_parens(b) else b
            exp = f"{a_str} / {b_str}"
        elif sym == "^":
            base = args_expected[0] if args_expected else "x"
            if self._needs_parens(base):
                base_str = f"({base})"
                var_input = args_input[0] if args_input else ""
                if var_input:
                    res_input = res_input.replace(var_input, f"скобка {var_input} скобка", 1)
            else:
                base_str = base
            p = const_val if const_val else (args_expected[1] if len(args_expected) > 1 else "2")
            p_str = f"({p})" if self._needs_parens(p) else p
            exp = f"{base_str}^{p_str}"
        elif sym == "root":
            d = const_val if const_val else "n"
            base = args_expected[0] if args_expected else "x"
            exp = f"root({d}, {base})"
        else:
            arg = args_expected[0] if args_expected else "x"
            exp = f"{sym}({arg})"

        return {"input": res_input, "expected": exp}

    def generate_target(self, term_sym, simple=False):
        tmpl = next((t for t in self.templates if t['sym'] == term_sym), None)
        if not tmpl:
            raise ValueError(f"Term {term_sym} not found")

        expr = self.fill_template(tmpl, 0, simple)

        if not simple and random.random() > 0.3:
            op = random.choice(self.arithm_ops)
            noise = self.get_simple_var()
            if random.random() > 0.5:
                return {
                    "input": f"{expr['input']}{op['in']}{noise['input']}",
                    "expected": f"{expr['expected']}{op['exp']}{noise['expected']}"
                }
            else:
                return {
                    "input": f"{noise['input']}{op['in']}{expr['input']}",
                    "expected": f"{noise['expected']}{op['exp']}{expr['expected']}"
                }
        return expr


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--term', default='sin')
    parser.add_argument('--lang', default='ru')
    parser.add_argument('--size', type=int, default=5)
    parser.add_argument('--simple', action='store_true')
    args = parser.parse_args()

    template_file = f"i18n/templates_{args.lang}.json"
    gen = TestGenerator(args.lang, template_file)
    output_file = f"tests/{args.term}.jsonl"
    os.makedirs('tests', exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        for _ in range(args.size):
            test = gen.generate_target(args.term, args.simple)
            f.write(json.dumps(test, ensure_ascii=False) + '\n')

    print(f"Generated {args.size} tests in {output_file}")


if __name__ == "__main__":
    main()
