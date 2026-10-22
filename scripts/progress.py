"""Print task completion per section of TASKS.md."""

import re
import sys
from pathlib import Path

TASKS = Path(__file__).resolve().parent.parent / "TASKS.md"
CHECKBOX = re.compile(r"^\s*- \[( |x|X)\] ")


def main() -> None:
    sections: dict[str, list[int]] = {}
    current = None
    for line in TASKS.read_text(encoding="utf-8").splitlines():
        if line.startswith("### ") or line.startswith("## "):
            current = line.lstrip("# ").strip()
        match = CHECKBOX.match(line)
        if match and current:
            done, total = sections.setdefault(current, [0, 0])
            sections[current] = [done + (match.group(1) != " "), total + 1]

    sys.stdout.reconfigure(encoding="utf-8")
    all_done = sum(d for d, _ in sections.values())
    all_total = sum(t for _, t in sections.values())
    width = max(len(name) for name in sections)
    for name, (done, total) in sections.items():
        bar = "#" * round(20 * done / total)
        print(f"{name:<{width}}  {done:>3}/{total:<3} [{bar:<20}]")
    print(f"\n{'Total':<{width}}  {all_done:>3}/{all_total:<3} ({100 * all_done / all_total:.0f}%)")


if __name__ == "__main__":
    main()
