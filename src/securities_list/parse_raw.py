from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

DEFAULT_RAW_DIR = Path("raw")
DEFAULT_OUTPUT_DIR = Path("data/generated")
DEFAULT_FULL_OUTPUT = DEFAULT_OUTPUT_DIR / "securities-full.json"
DEFAULT_COMPACT_OUTPUT = DEFAULT_OUTPUT_DIR / "securities.json"

HEADER_KEYS = {
    "國際證券辨識號碼(ISIN Code)": "isin_code",
    "公開發行日": "public_offering_date",
    "上市日": "listing_date",
    "發行日": "issue_date",
    "到期日": "maturity_date",
    "利率值": "interest_rate",
    "市場別": "market",
    "產業別": "industry",
    "CFICode": "cfi_code",
    "備註": "remarks",
    "發布日": "publish_date",
    "登錄日": "registration_date",
    "掛牌日": "listing_date",
}

CODE_NAME_HEADERS = {
    "有價證券代號及名稱",
    "指數代號及名稱",
    "STO代號及名稱",
}

NAME_HEADERS = {
    "有價證券名稱",
}


class TableRowsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._in_row = False
        self._in_cell = False
        self._current_row: list[str] = []
        self._current_cell: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.lower()
        if normalized == "tr":
            self._in_row = True
            self._current_row = []
        elif self._in_row and normalized in {"td", "th"}:
            self._in_cell = True
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if self._in_cell and normalized in {"td", "th"}:
            self._current_row.append(normalize_text("".join(self._current_cell)))
            self._in_cell = False
        elif self._in_row and normalized == "tr":
            self.rows.append(self._current_row)
            self._in_row = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell.append(data)


def normalize_text(value: str) -> str:
    return re.sub(r"[ \t\r\n]+", " ", value).strip()


def nullable(value: str) -> str | None:
    return value if value else None


def extract_str_mode_from_path(path: Path) -> int | None:
    match = re.match(r"^(\d+)-", path.name)
    if match is None:
        return None
    return int(match.group(1))


def split_code_name(value: str) -> tuple[str | None, str | None]:
    normalized = normalize_text(value.replace("\u3000", " "))
    if not normalized:
        return None, None
    match = re.match(r"^(\S+)\s+(.+)$", normalized)
    if match is None:
        return None, normalized
    return match.group(1), match.group(2)


def parse_rows(html: str) -> list[list[str]]:
    parser = TableRowsParser()
    parser.feed(html)
    parser.close()
    return parser.rows


def parse_raw_file(path: Path) -> list[dict[str, object]]:
    html = path.read_text(encoding="utf-8")
    rows = [row for row in parse_rows(html) if row]
    if not rows:
        return []

    headers = rows[0]
    str_mode = extract_str_mode_from_path(path)
    category: str | None = None
    records: list[dict[str, object]] = []

    for row in rows[1:]:
        if len(row) == 1 and row[0]:
            category = row[0]
            continue
        if len(row) != len(headers):
            raise ValueError(
                f"{path}: expected {len(headers)} columns, got {len(row)}: {row}"
            )

        raw_fields = dict(zip(headers, row, strict=True))
        record: dict[str, object] = {
            "str_mode": str_mode,
            "category": category,
            "code": None,
            "name": None,
            "raw_fields": raw_fields,
        }

        for header, value in raw_fields.items():
            if header in CODE_NAME_HEADERS:
                code, name = split_code_name(value)
                record["code"] = code
                record["name"] = name
            elif header in NAME_HEADERS:
                record["name"] = nullable(value)
            elif header in HEADER_KEYS:
                record[HEADER_KEYS[header]] = nullable(value)

        records.append(record)

    return records


def raw_file_sort_key(path: Path) -> tuple[int, str]:
    str_mode = extract_str_mode_from_path(path)
    return (str_mode if str_mode is not None else 9999, path.name)


def convert_raw_dir(raw_dir: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in sorted(raw_dir.glob("*.html"), key=raw_file_sort_key):
        records.extend(parse_raw_file(path))
    return records


def compact_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "code": record["code"],
            "name": record["name"],
        }
        for record in records
    ]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert TWSE raw HTML files into a JSON securities list.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=DEFAULT_RAW_DIR,
        help="directory containing raw HTML files",
    )
    parser.add_argument(
        "--full-output",
        type=Path,
        default=DEFAULT_FULL_OUTPUT,
        help="full JSON output path",
    )
    parser.add_argument(
        "--compact-output",
        type=Path,
        default=DEFAULT_COMPACT_OUTPUT,
        help="compact code/name JSON output path",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        records = convert_raw_dir(args.raw_dir)
        write_json(args.full_output, records)
        compact = compact_records(records)
        write_json(args.compact_output, compact)
    except (OSError, ValueError) as exc:
        print(f"convert-raw-json: {exc}", file=sys.stderr)
        return 1

    print(f"{args.full_output} ({len(records)} records)")
    print(f"{args.compact_output} ({len(compact)} records)")
    return 0
