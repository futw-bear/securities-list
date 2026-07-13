from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from securities_list.parse_raw import (
    convert_raw_dir_by_str_mode,
    main,
    output_path_for_str_mode,
)


def raw_html(*rows: str) -> str:
    rendered_rows = "".join(f"<tr>{row}</tr>" for row in rows)
    return f"<html><body><table>{rendered_rows}</table></body></html>"


class ConvertRawDirTests(unittest.TestCase):
    def test_groups_records_by_str_mode_and_keeps_empty_modes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            raw_dir = Path(temporary_directory)
            (raw_dir / "1-first.html").write_text(
                raw_html(
                    "<th>有價證券代號及名稱</th><th>市場別</th>",
                    "<td>上市股票</td>",
                    "<td>1111　測試一</td><td>上市</td>",
                ),
                encoding="utf-8",
            )
            (raw_dir / "2-empty.html").write_text(
                raw_html("<th>有價證券代號及名稱</th><th>市場別</th>"),
                encoding="utf-8",
            )

            records, records_by_str_mode = convert_raw_dir_by_str_mode(raw_dir)

        self.assertEqual([record["code"] for record in records], ["1111"])
        self.assertEqual(list(records_by_str_mode), [1, 2])
        self.assertEqual(records_by_str_mode[1], records)
        self.assertEqual(records_by_str_mode[2], [])

    def test_output_path_inserts_str_mode_before_suffix(self) -> None:
        self.assertEqual(
            output_path_for_str_mode(Path("data/parsed/securities-full.json"), 12),
            Path("data/parsed/securities-full-12.json"),
        )

    def test_main_writes_combined_and_per_mode_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            raw_dir = root / "raw"
            output_dir = root / "parsed"
            raw_dir.mkdir()
            (raw_dir / "1-first.html").write_text(
                raw_html(
                    "<th>有價證券代號及名稱</th><th>市場別</th>",
                    "<td>1111　測試一</td><td>上市</td>",
                ),
                encoding="utf-8",
            )
            (raw_dir / "2-second.html").write_text(
                raw_html(
                    "<th>有價證券代號及名稱</th><th>市場別</th>",
                    "<td>2222　測試二</td><td>上櫃</td>",
                ),
                encoding="utf-8",
            )

            result = main(
                [
                    "--raw-dir",
                    str(raw_dir),
                    "--compact-output",
                    str(output_dir / "securities.json"),
                    "--full-output",
                    str(output_dir / "securities-full.json"),
                ]
            )

            self.assertEqual(result, 0)
            self.assertEqual(
                json.loads((output_dir / "securities.json").read_text()),
                [
                    {"code": "1111", "name": "測試一"},
                    {"code": "2222", "name": "測試二"},
                ],
            )
            self.assertEqual(
                json.loads((output_dir / "securities-1.json").read_text()),
                [{"code": "1111", "name": "測試一"}],
            )
            self.assertEqual(
                json.loads((output_dir / "securities-2.json").read_text()),
                [{"code": "2222", "name": "測試二"}],
            )
            self.assertEqual(
                len(json.loads((output_dir / "securities-full.json").read_text())),
                2,
            )
            self.assertEqual(
                len(json.loads((output_dir / "securities-full-1.json").read_text())),
                1,
            )
            self.assertEqual(
                len(json.loads((output_dir / "securities-full-2.json").read_text())),
                1,
            )


if __name__ == "__main__":
    unittest.main()
