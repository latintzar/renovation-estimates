"""
V4 Deterministic Quantity Formulas
=================================

The Quantification Planner outputs `formula_ast`, a restricted expression tree.
This module validates and evaluates that AST deterministically.

WHY THIS MATTERS:
- Prevents “bit-reduction”: the planner must not output raw quantities.
- Makes quantity computation auditable and unit-consistent.
- Fails loud and early on invalid plans (missing signals, unsupported ops, NaN/inf, etc).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Literal, Set, Tuple

from pricing.measurement_catalog_v4 import get_measurement_signal_spec


UnitFamily = Literal["m2", "ml", "ud", "m3"]


@dataclass(frozen=True)
class FormulaEvaluationContext:
    work_item_id: str
    room_id: str
    dimension: str
    unit_family: UnitFamily


class FormulaValidationError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if condition:
        return
    raise FormulaValidationError(message)


def extract_signal_ids(formula_ast: Dict[str, Any]) -> Set[str]:
    """
    Collect all referenced signal_ids from an AST.
    """
    if not isinstance(formula_ast, dict):
        raise FormulaValidationError("quantity_formula_v4: formula_ast must be an object")
    op = formula_ast.get("op")
    if op == "SIGNAL":
        sid = formula_ast.get("signal_id")
        if not isinstance(sid, str) or not sid.strip():
            raise FormulaValidationError("quantity_formula_v4: SIGNAL node missing signal_id")
        return {sid}
    if op == "CONST_UNIT":
        return set()
    if op == "CONST":
        return set()
    if op in ("ADD", "SUB", "MUL", "DIV", "MIN", "MAX"):
        args = formula_ast.get("args")
        if not isinstance(args, list) or not args:
            raise FormulaValidationError(f"quantity_formula_v4: {op} node requires non-empty args[]")
        out: Set[str] = set()
        for a in args:
            if not isinstance(a, dict):
                raise FormulaValidationError(f"quantity_formula_v4: {op} args must be objects")
            out |= extract_signal_ids(a)
        return out
    if op in ("CEIL", "FLOOR"):
        arg = formula_ast.get("arg")
        if not isinstance(arg, dict):
            raise FormulaValidationError(f"quantity_formula_v4: {op} node requires arg object")
        return extract_signal_ids(arg)
    raise FormulaValidationError(f"quantity_formula_v4: unsupported op={op}")


def validate_formula_ast(
    *,
    formula_ast: Dict[str, Any],
    unit_family: UnitFamily,
    signal_units: Dict[str, UnitFamily] | None = None,
) -> None:
    """
    Validate that the AST:
    - Uses only supported operations
    - References known signals
    - References signals whose unit families are compatible with the intended output unit family

    NOTE: Compatibility checks are conservative:
    - We allow formulas that combine m2 signals into m2 outputs, ml into ml, ud into ud, etc.
    - We allow multiplication/division by constants for coverage factors or wastage.
    - We do NOT allow combining mismatched families (e.g., adding m2 and ud).
      If needed, the planner should output separate work items with correct units.
    """
    if unit_family not in ("m2", "ml", "ud", "m3"):
        raise FormulaValidationError(f"quantity_formula_v4: invalid unit_family={unit_family}")
    # Dimensional analysis:
    # - Signals have unit families; CONST is unitless; CONST_UNIT carries unit family.
    # - ADD/SUB/MIN/MAX require same dimension.
    # - MUL/DIV combine dimensions; `ud` acts like a scalar multiplier (count).
    def dim_of_family(u: str) -> str:
        if u == "ud":
            return "count"
        if u == "ml":
            return "m1"
        if u == "m2":
            return "m2"
        if u == "m3":
            return "m3"
        raise FormulaValidationError(f"quantity_formula_v4: invalid unit_family={u}")

    def pow_of(dim: str) -> int | None:
        if dim == "count":
            return None
        if dim == "m1":
            return 1
        if dim == "m2":
            return 2
        if dim == "m3":
            return 3
        if dim == "unitless":
            return 0
        raise FormulaValidationError(f"quantity_formula_v4: invalid dim={dim}")

    def family_of_dim(dim: str) -> UnitFamily:
        if dim == "count":
            return "ud"
        if dim == "m1":
            return "ml"
        if dim == "m2":
            return "m2"
        if dim == "m3":
            return "m3"
        if dim == "unitless":
            return "ud"
        raise FormulaValidationError(f"quantity_formula_v4: invalid dim={dim}")

    def infer_dim(node: Dict[str, Any]) -> str:
        op = node.get("op")
        if op == "CONST":
            return "unitless"
        if op == "CONST_UNIT":
            uf = node.get("unit_family")
            if not isinstance(uf, str):
                raise FormulaValidationError("quantity_formula_v4: CONST_UNIT missing unit_family")
            return dim_of_family(uf)
        if op == "SIGNAL":
            sid = node.get("signal_id")
            if not isinstance(sid, str) or not sid.strip():
                raise FormulaValidationError("quantity_formula_v4: SIGNAL missing signal_id")
            if signal_units and sid in signal_units:
                return dim_of_family(signal_units[sid])
            spec = get_measurement_signal_spec(sid)
            return dim_of_family(spec.unit_family)
        if op in ("ADD", "SUB", "MIN", "MAX"):
            args = node.get("args")
            if not isinstance(args, list) or not args:
                raise FormulaValidationError(f"quantity_formula_v4: {op} requires non-empty args[]")
            dims = [infer_dim(a) for a in args]
            base = dims[0]
            if any(d != base for d in dims[1:]):
                raise FormulaValidationError(f"quantity_formula_v4: {op} dimension mismatch | dims={dims}")
            return base
        if op in ("MUL", "DIV"):
            args = node.get("args")
            if not isinstance(args, list) or len(args) < 2:
                raise FormulaValidationError(f"quantity_formula_v4: {op} requires at least 2 args")
            dims = [infer_dim(a) for a in args]

            # Reduce left-to-right with scalar rules
            cur = dims[0]
            for nxt in dims[1:]:
                if op == "MUL":
                    if cur in ("unitless", "count"):
                        cur = nxt
                        continue
                    if nxt in ("unitless", "count"):
                        continue
                    # both meter-based
                    p = pow_of(cur)
                    q = pow_of(nxt)
                    if p is None or q is None:
                        raise FormulaValidationError(f"quantity_formula_v4: MUL invalid dims | {cur} * {nxt}")
                    s = p + q
                    if s not in (1, 2, 3):
                        raise FormulaValidationError(f"quantity_formula_v4: MUL produces unsupported dim | {p}+{q}={s}")
                    cur = {1: "m1", 2: "m2", 3: "m3"}[s]
                else:
                    # DIV
                    if nxt in ("unitless", "count"):
                        continue
                    if cur in ("unitless", "count"):
                        raise FormulaValidationError(f"quantity_formula_v4: DIV invalid dims | {cur} / {nxt}")
                    p = pow_of(cur)
                    q = pow_of(nxt)
                    if p is None or q is None:
                        raise FormulaValidationError(f"quantity_formula_v4: DIV invalid dims | {cur} / {nxt}")
                    s = p - q
                    if s < 0 or s not in (0, 1, 2, 3):
                        raise FormulaValidationError(f"quantity_formula_v4: DIV produces unsupported dim | {p}-{q}={s}")
                    cur = "unitless" if s == 0 else {1: "m1", 2: "m2", 3: "m3"}[s]
            return cur
        if op in ("CEIL", "FLOOR"):
            arg = node.get("arg")
            if not isinstance(arg, dict):
                raise FormulaValidationError(f"quantity_formula_v4: {op} requires arg object")
            return infer_dim(arg)
        raise FormulaValidationError(f"quantity_formula_v4: unsupported op={op}")

    inferred = infer_dim(formula_ast)
    expected = dim_of_family(unit_family)
    if inferred != expected:
        inferred_family = "unitless" if inferred == "unitless" else family_of_dim(inferred)
        raise FormulaValidationError(
            "quantity_formula_v4: output unit mismatch "
            f"| expected_family={unit_family} expected_dim={expected} "
            f"| inferred_family={inferred_family} inferred_dim={inferred}"
        )


def _eval_node(node: Dict[str, Any], signals: Dict[str, float]) -> float:
    op = node.get("op")
    if op == "CONST":
        v = node.get("value")
        if not isinstance(v, (int, float)):
            raise FormulaValidationError("quantity_formula_v4: CONST value must be number")
        return float(v)
    if op == "CONST_UNIT":
        v = node.get("value")
        if not isinstance(v, (int, float)):
            raise FormulaValidationError("quantity_formula_v4: CONST_UNIT value must be number")
        # unit_family is validated in validate_formula_ast() during evaluation
        return float(v)
    if op == "SIGNAL":
        sid = node.get("signal_id")
        if not isinstance(sid, str) or not sid.strip():
            raise FormulaValidationError("quantity_formula_v4: SIGNAL node missing signal_id")
        if sid not in signals:
            raise FormulaValidationError(f"quantity_formula_v4: missing signal | signal_id={sid}")
        return float(signals[sid])
    if op in ("ADD", "SUB", "MUL", "DIV", "MIN", "MAX"):
        args = node.get("args")
        if not isinstance(args, list) or not args:
            raise FormulaValidationError(f"quantity_formula_v4: {op} requires non-empty args[]")
        vals = [_eval_node(a, signals) for a in args]
        if op == "ADD":
            return float(sum(vals))
        if op == "SUB":
            _require(len(vals) >= 2, "quantity_formula_v4: SUB requires at least 2 args")
            out = vals[0]
            for v in vals[1:]:
                out -= v
            return float(out)
        if op == "MUL":
            out = 1.0
            for v in vals:
                out *= v
            return float(out)
        if op == "DIV":
            _require(len(vals) >= 2, "quantity_formula_v4: DIV requires at least 2 args")
            out = vals[0]
            for v in vals[1:]:
                _require(v != 0, "quantity_formula_v4: division by zero")
                out /= v
            return float(out)
        if op == "MIN":
            return float(min(vals))
        if op == "MAX":
            return float(max(vals))
    if op in ("CEIL", "FLOOR"):
        arg = node.get("arg")
        if not isinstance(arg, dict):
            raise FormulaValidationError(f"quantity_formula_v4: {op} requires arg object")
        v = _eval_node(arg, signals)
        return float(math.ceil(v) if op == "CEIL" else math.floor(v))
    raise FormulaValidationError(f"quantity_formula_v4: unsupported op={op}")


def evaluate_formula(
    *,
    ctx: FormulaEvaluationContext,
    formula_ast: Dict[str, Any],
    signals: Dict[str, Any],
    signal_units: Dict[str, UnitFamily] | None = None,
) -> Tuple[float, List[str]]:
    """
    Evaluate a validated AST against provided signals.

    Returns:
      (quantity, signals_used)
    """
    if not isinstance(signals, dict):
        raise FormulaValidationError("quantity_formula_v4: signals must be dict")

    # Normalize signals → numeric values
    numeric_signals: Dict[str, float] = {}
    for k, v in signals.items():
        if v is None:
            continue
        if isinstance(v, (int, float)):
            numeric_signals[str(k)] = float(v)
            continue
        if isinstance(v, dict) and "value" in v:
            vv = v.get("value")
            if isinstance(vv, (int, float)):
                numeric_signals[str(k)] = float(vv)
                continue
        raise FormulaValidationError(
            f"quantity_formula_v4: signal value not numeric | key={k} type={type(v).__name__}"
        )

    validate_formula_ast(formula_ast=formula_ast, unit_family=ctx.unit_family, signal_units=signal_units)
    qty = _eval_node(formula_ast, numeric_signals)

    if not math.isfinite(qty):
        raise FormulaValidationError(
            "quantity_formula_v4: non-finite quantity "
            f"| work_item_id={ctx.work_item_id} room_id={ctx.room_id} dimension={ctx.dimension} qty={qty}"
        )
    if qty < 0:
        raise FormulaValidationError(
            "quantity_formula_v4: negative quantity "
            f"| work_item_id={ctx.work_item_id} room_id={ctx.room_id} dimension={ctx.dimension} qty={qty}"
        )

    used = sorted(extract_signal_ids(formula_ast))
    return float(qty), used

