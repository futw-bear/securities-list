from __future__ import annotations

import argparse
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

DEFAULT_URL = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=1"
DEFAULT_OUTPUT_DIR = Path("raw")
STR_MODES = range(1, 13)


class TwseTitleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._tag_stack: list[str] = []
        self._capturing = False
        self._captured_title = False
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.lower()
        self._tag_stack.append(normalized)
        if not self._captured_title and self._is_title_font():
            self._capturing = True

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if self._capturing and normalized == "font":
            self._capturing = False
            self._captured_title = True
        for index in range(len(self._tag_stack) - 1, -1, -1):
            if self._tag_stack[index] == normalized:
                del self._tag_stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if self._capturing:
            self._parts.append(data)

    def _is_title_font(self) -> bool:
        if len(self._tag_stack) < 4 or self._tag_stack[-1] != "font":
            return False
        if self._tag_stack[-2] not in {"string", "strong"}:
            return False
        h2_index = _last_index(self._tag_stack[:-2], "h2")
        if h2_index is None:
            return False
        return "body" in self._tag_stack[:h2_index]

    @property
    def title(self) -> str | None:
        title = " ".join(part.strip() for part in self._parts if part.strip())
        return title or None


def _last_index(values: list[str], needle: str) -> int | None:
    for index in range(len(values) - 1, -1, -1):
        if values[index] == needle:
            return index
    return None


def extract_title(html: str) -> str:
    parser = TwseTitleParser()
    parser.feed(html)
    parser.close()
    if parser.title is None:
        raise ValueError("Could not find title at body > h2 > string > font")
    return parser.title


def sanitize_filename_stem(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value).strip()
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", normalized)
    sanitized = sanitized.strip(" .")
    if not sanitized:
        raise ValueError("Extracted title is empty after filename sanitization")
    return sanitized


def extract_str_mode(url: str) -> str | None:
    values = parse_qs(urlparse(url).query).get("strMode")
    if not values or not values[0]:
        return None
    return sanitize_filename_stem(values[0])


def url_for_str_mode(url: str, mode: int) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    query["strMode"] = [str(mode)]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def fetch_html(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "securities-list/0.1 (+https://github.com/futw-bear/securities-list)",
        },
    )
    with urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "big5"
        return response.read().decode(charset, errors="replace")


def save_raw_html(html: str, output_dir: Path, url: str) -> Path:
    title = extract_title(html)
    filename_stem = sanitize_filename_stem(title)
    str_mode = extract_str_mode(url)
    if str_mode is not None:
        filename_stem = f"{str_mode}-{filename_stem}"
    filename = f"{filename_stem}.html"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    output_path.write_text(html, encoding="utf-8")
    return output_path


def download_raw_html(url: str, output_dir: Path) -> Path:
    html = fetch_html(url)
    return save_raw_html(html, output_dir, url)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download the TWSE ISIN source page into the raw directory.",
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="source URL to download")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="directory for the downloaded raw HTML file",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=len(STR_MODES),
        help="number of parallel downloads",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.workers < 1:
        print("download-twse-isin: --workers must be greater than 0", file=sys.stderr)
        return 1

    urls = [url_for_str_mode(args.url, mode) for mode in STR_MODES]
    output_paths: dict[int, Path] = {}
    errors: list[tuple[int, Exception]] = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(download_raw_html, url, args.output_dir): mode
            for mode, url in zip(STR_MODES, urls, strict=True)
        }
        for future in as_completed(futures):
            mode = futures[future]
            try:
                output_paths[mode] = future.result()
            except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
                errors.append((mode, exc))

    for mode in sorted(output_paths):
        print(output_paths[mode])

    if errors:
        for mode, exc in sorted(errors):
            print(f"download-twse-isin: strMode={mode}: {exc}", file=sys.stderr)
        return 1

    return 0
