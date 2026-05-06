"""Разрешение PREP токенов по контексту."""

def resolve_prepositions(tokens: list, prep_rules: dict) -> list:
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t.type != "PREP":
            i += 1
            continue

        context = _find_context(tokens, i)
        rule = prep_rules.get(context, {})
        preps = rule.get("preps", [])
        action = rule.get("action", "ignore")

        if t.value in preps:
            if action == "of":
                tokens[i] = type(t)("OF", t.value)
            elif action == "sep":
                tokens[i] = type(t)("SEP", t.value)
            elif action == "power":
                tokens[i] = type(t)("KEYWORD", "pow")
            elif action == "ignore":
                tokens[i] = type(t)("IGNORE", t.value)
            elif action == "stop":
                tokens[i] = type(t)("STOP", t.value)
        else:
            # Общие правила
            if t.value == "на" and _has_operand_before(tokens, i):
                tokens[i] = type(t)("SEP", t.value)
            elif t.value in ("в", "во") and _has_pow_ahead(tokens, i):
                tokens[i] = type(t)("KEYWORD", "pow")
            else:
                tokens[i] = type(t)("IGNORE", t.value)

        i += 1

    return [t for t in tokens if t.type != "IGNORE"]


def _find_context(tokens, pos):
    for j in range(pos - 1, -1, -1):
        t = tokens[j]
        if t.type == "KEYWORD":
            return t.value
        elif t.type == "FUNC":
            return t.value  # "lim", "sin", "cos"...
        elif t.type == "OP" and t.value == "/":
            return "divide"
        # NUM, VAR, OF, PREP — пропускаем, ищем дальше
        elif t.type in ("PAREN_CLOSE", "ALL"):
          continue  # пропускаем, ищем дальше
    # return "expr"


def _has_operand_before(tokens, pos):
    for j in range(pos - 1, -1, -1):
        if tokens[j].type in ("VAR", "NUM", "PAREN_CLOSE", "ALL", "FUNC", "KEYWORD", "OP"):
            return True
    return False


def _has_pow_ahead(tokens, pos):
    for j in range(pos + 1, len(tokens)):
        t = tokens[j]
        if t.type == "KEYWORD" and t.value in ("cube", "square", "degree"):
            return True
        if t.type in ("NUM", "VAR", "PREP", "KEYWORD"):
            continue
        break
    return False
