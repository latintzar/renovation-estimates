import argparse
import json
import logging
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


def _replace_between_markers(text: str, *, start: str, end: str, replacement: str) -> str:
    start_idx = text.find(start)
    end_idx = text.find(end)
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        raise RuntimeError(f"Failed to find marker block | start={start!r} end={end!r}")
    before = text[: start_idx + len(start)]
    after = text[end_idx:]
    return before + "\n" + replacement + "\n" + after


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(args: argparse.Namespace) -> None:
    viewer_path = Path(args.viewer_template).resolve()
    pir_path = Path(args.pir_json).resolve()
    output_path = Path(args.output).resolve()

    if not viewer_path.exists():
        raise FileNotFoundError(f"Viewer template not found: {viewer_path}")
    if not pir_path.exists():
        raise FileNotFoundError(f"PIR JSON not found: {pir_path}")

    payload = _load_json(pir_path)
    html = viewer_path.read_text(encoding="utf-8")
    embedded = json.dumps(payload, indent=2, ensure_ascii=False)
    html2 = _replace_between_markers(
        html,
        start="<!-- PIR_EXPORT:BEGIN -->",
        end="<!-- PIR_EXPORT:END -->",
        replacement=embedded,
    )
    _write_text(output_path, html2)
    logger.info(f"Embedded PIR payload into viewer | path={output_path}")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Embed GLB PIR JSON into viewer HTML.")
    parser.add_argument(
        "--viewer-template",
        default=str(repo_root / "docs/demos/indoorgml_lite_glb_viewer.html"),
        help="Viewer template HTML path",
    )
    parser.add_argument("--pir-json", required=True, help="Path to glb_pir.json")
    parser.add_argument(
        "--output",
        default=str(repo_root / "docs/demos/generated/glb_pir_viewer.html"),
        help="Output HTML path",
    )
    args = parser.parse_args()

    try:
        _run(args)
    except Exception:
        logger.exception("Viewer embedding failed")
        raise


if __name__ == "__main__":
    main()
