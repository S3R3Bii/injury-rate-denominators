"""Exact reported-rate sensitivities with explicitly authored prior exposures."""

from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from fractions import Fraction

STRENGTHS = [Fraction(1, 10), Fraction(1), Fraction(10)]


def rate(cases, hours):
    if isinstance(cases, bool) or isinstance(hours, bool):
        raise ValueError("numeric counts and exposure required")
    k = Fraction(cases)
    h = Fraction(hours)
    if k < 0 or k.denominator != 1 or h <= 0:
        raise ValueError("known nonnegative count and positive exposure required")
    return k * 200000 / h


def posterior(cases, hours, mean, strength):
    if isinstance(strength, bool) or isinstance(mean, bool):
        raise ValueError("explicit numeric assumptions required")
    b = Fraction(strength)
    mu = Fraction(mean)
    if b not in STRENGTHS or mu <= 0:
        raise ValueError(
            "proper positive-mean working prior and declared strength required"
        )
    rate(cases, hours)
    return (Fraction(cases) + b * mu) / (Fraction(hours) / 200000 + b)


def fixed12(value):
    f = Fraction(value)
    with localcontext() as context:
        context.prec = 60
        return format(
            (Decimal(f.numerator) / Decimal(f.denominator)).quantize(
                Decimal("0.000000000001"), rounding=ROUND_HALF_EVEN
            ),
            "f",
        )


def zero_upper(hours):
    h = Fraction(hours)
    if h <= 0:
        raise ValueError("positive exposure required")
    with localcontext() as context:
        context.prec = 60
        x = (
            -Decimal("0.05").ln()
            * Decimal(200000)
            * Decimal(h.denominator)
            / Decimal(h.numerator)
        )
        return format(
            x.quantize(Decimal("0.000000000001"), rounding=ROUND_HALF_EVEN), "f"
        )
