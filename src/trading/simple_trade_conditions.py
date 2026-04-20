from __future__ import annotations

import re

try:
    from .simple_trade_market import IndicatorSnapshot
except ImportError:
    from simple_trade_market import IndicatorSnapshot


def indicator_value(indicators: IndicatorSnapshot, name: str) -> float | None:
    normalized = name.strip().upper()
    lookup = {
        "PRICE": indicators.price,
        "CLOSE": indicators.price,
        "RSI": indicators.rsi,
        "EMA20": indicators.ema20,
        "EMA50": indicators.ema50,
        "MACD": indicators.macd,
        "MACDSIGNAL": indicators.macd_signal,
        "SIGNAL": indicators.macd_signal,
        "MACD_SIGNAL": indicators.macd_signal,
        "BBUPPER": indicators.bollinger_upper,
        "BBMIDDLE": indicators.bollinger_middle,
        "BBLOWER": indicators.bollinger_lower,
        "BOLLINGERUPPER": indicators.bollinger_upper,
        "BOLLINGERMIDDLE": indicators.bollinger_middle,
        "BOLLINGERLOWER": indicators.bollinger_lower,
    }
    if normalized not in lookup:
        raise ValueError(f"unsupported indicator: {name}")
    return lookup[normalized]


def resolve_operand(indicators: IndicatorSnapshot, operand: str) -> float | None:
    text = operand.strip()
    try:
        return float(text)
    except ValueError:
        return indicator_value(indicators, text)


def evaluate_comparison(indicators: IndicatorSnapshot, comparison: str) -> bool:
    match = re.fullmatch(
        r"\s*([A-Za-z][A-Za-z0-9_]*)\s*(>=|<=|==|!=|>|<)\s*([A-Za-z][A-Za-z0-9_]*|[-+]?\d+(?:\.\d+)?)\s*",
        comparison,
    )
    if not match:
        raise ValueError(f"invalid comparison expression: {comparison}")

    left_operand, operator, right_operand = match.groups()
    left_value = resolve_operand(indicators, left_operand)
    right_value = resolve_operand(indicators, right_operand)
    if left_value is None or right_value is None:
        return False

    if operator == ">":
        return left_value > right_value
    if operator == ">=":
        return left_value >= right_value
    if operator == "<":
        return left_value < right_value
    if operator == "<=":
        return left_value <= right_value
    if operator == "==":
        return left_value == right_value
    if operator == "!=":
        return left_value != right_value
    raise ValueError(f"unsupported operator: {operator}")


def comparison_details(indicators: IndicatorSnapshot, comparison: str) -> tuple[bool, str]:
    match = re.fullmatch(
        r"\s*([A-Za-z][A-Za-z0-9_]*)\s*(>=|<=|==|!=|>|<)\s*([A-Za-z][A-Za-z0-9_]*|[-+]?\d+(?:\.\d+)?)\s*",
        comparison,
    )
    if not match:
        raise ValueError(f"invalid comparison expression: {comparison}")

    left_operand, operator, right_operand = match.groups()
    left_value = resolve_operand(indicators, left_operand)
    right_value = resolve_operand(indicators, right_operand)

    if left_value is None or right_value is None:
        return False, f"{comparison} unavailable"

    result = evaluate_comparison(indicators, comparison)
    detail = f"{left_operand}({left_value:.4f}) {operator} {right_operand}({right_value:.4f})"
    return result, detail


def explain_comparison(detail: str) -> str:
    match = re.fullmatch(
        r"([A-Za-z][A-Za-z0-9_]*?)\(([-+]?\d+(?:\.\d+)?)\)\s*(>=|<=|==|!=|>|<)\s*([A-Za-z][A-Za-z0-9_]*?|[-+]?\d+(?:\.\d+)?)\(([-+]?\d+(?:\.\d+)?)\)",
        detail,
    )
    if not match:
        return detail

    left_name, left_value, operator, right_name, right_value = match.groups()
    left_number = float(left_value)
    right_number = float(right_value)
    comparison_result = {
        ">": left_number > right_number,
        ">=": left_number >= right_number,
        "<": left_number < right_number,
        "<=": left_number <= right_number,
        "==": left_number == right_number,
        "!=": left_number != right_number,
    }[operator]
    operator_text = {
        ">": "greater than",
        ">=": "greater than or equal to",
        "<": "less than",
        "<=": "less than or equal to",
        "==": "equal to",
        "!=": "not equal to",
    }[operator]
    status_text = "true" if comparison_result else "false"
    return (
        f"{left_name.upper()} is {left_value} and {right_name.upper()} is {right_value}, "
        f"so `{left_name.upper()} {operator} {right_name.upper()}` is {status_text} "
        f"because {left_name.upper()} is not {operator_text} {right_name.upper()}." if not comparison_result
        else f"so `{left_name.upper()} {operator} {right_name.upper()}` is {status_text} "
        f"because {left_name.upper()} is {operator_text} {right_name.upper()}."
    )


def explain_condition_result(expression: str, matched: bool, reason: str) -> str:
    readable_reason = reason
    pattern = (
        r"[A-Za-z][A-Za-z0-9_]*\([-+]?\d+(?:\.\d+)?\)\s*"
        r"(?:>=|<=|==|!=|>|<)\s*"
        r"(?:[A-Za-z][A-Za-z0-9_]*|[-+]?\d+(?:\.\d+)?)\([-+]?\d+(?:\.\d+)?\)"
    )
    for detail in sorted(set(re.findall(pattern, reason)), key=len, reverse=True):
        readable_reason = readable_reason.replace(detail, explain_comparison(detail))

    if matched:
        return f"Condition met for `{expression}`. {readable_reason}"
    return f"Condition not met for `{expression}`. {readable_reason}"


def tokenize_expression(expression: str) -> list[str]:
    token_pattern = re.compile(
        r"\s*(>=|<=|==|!=|>|<|\(|\)|AND\b|OR\b|[A-Za-z][A-Za-z0-9_]*|[-+]?\d+(?:\.\d+)?)\s*",
        re.IGNORECASE,
    )
    tokens: list[str] = []
    position = 0
    while position < len(expression):
        match = token_pattern.match(expression, position)
        if not match:
            raise ValueError(f"invalid token near: {expression[position:]}")
        tokens.append(match.group(1))
        position = match.end()
    return tokens


def evaluate_condition_expression(indicators: IndicatorSnapshot, expression: str) -> tuple[bool, str]:
    tokens = tokenize_expression(expression)
    index = 0

    def parse_expression() -> tuple[bool, str]:
        return parse_or()

    def parse_or() -> tuple[bool, str]:
        nonlocal index
        result, reason = parse_and()
        while index < len(tokens) and tokens[index].upper() == "OR":
            index += 1
            right_result, right_reason = parse_and()
            result = result or right_result
            reason = f"{reason} OR {right_reason}"
        return result, reason

    def parse_and() -> tuple[bool, str]:
        nonlocal index
        result, reason = parse_primary()
        while index < len(tokens) and tokens[index].upper() == "AND":
            index += 1
            right_result, right_reason = parse_primary()
            result = result and right_result
            reason = f"{reason} AND {right_reason}"
        return result, reason

    def parse_primary() -> tuple[bool, str]:
        nonlocal index
        if index >= len(tokens):
            raise ValueError("unexpected end of condition expression")

        if tokens[index] == "(":
            index += 1
            result, reason = parse_or()
            if index >= len(tokens) or tokens[index] != ")":
                raise ValueError("missing closing parenthesis in condition expression")
            index += 1
            return result, f"({reason})"

        if index + 2 >= len(tokens):
            raise ValueError("incomplete comparison in condition expression")

        comparison = " ".join(tokens[index:index + 3])
        index += 3
        return comparison_details(indicators, comparison)

    matched, reason = parse_expression()
    if index != len(tokens):
        raise ValueError(f"unexpected token in condition expression: {tokens[index]}")
    return matched, reason
