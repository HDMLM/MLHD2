from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd


CANONICAL_COLUMNS = [
	"Super Destroyer",
	"Helldivers",
	"Level",
	"Title",
	"Sector",
	"Planet",
	"Mega Structure",
	"Enemy Type",
	"Enemy Subfaction",
	"Enemy HVT",
	"Major Order",
	"DSS Active",
	"DSS Modifier",
	"Mission Category",
	"Mission Type",
	"Difficulty",
	"Kills",
	"Deaths",
	"Rating",
	"Time",
	"Streak",
	"Note",
]

# Canonical column -> compatible aliases seen in previous versions.
COLUMN_ALIASES = {
	"Mega Structure": ("Mega City",),
}


def _normalize_header_name(value: str) -> str:
	normalized = str(value or "").strip().lower().replace("_", " ")
	return " ".join(normalized.split())


def _get_column_lookup(df: pd.DataFrame) -> dict[str, str]:
	lookup: dict[str, str] = {}
	for original in df.columns:
		key = _normalize_header_name(original)
		if key and key not in lookup:
			lookup[key] = str(original)
	return lookup


def _is_missing_value(value: object) -> bool:
	if value is None:
		return True
	if pd.isna(value):
		return True
	if isinstance(value, str) and not value.strip():
		return True
	return False


def _merge_columns(primary: pd.Series, fallback: pd.Series) -> pd.Series:
	merged = primary.copy()
	mask = merged.map(_is_missing_value)
	merged.loc[mask] = fallback.loc[mask]
	return merged


def normalize_dataframe(df: pd.DataFrame, drop_extra_columns: bool = False) -> tuple[pd.DataFrame, dict[str, str], list[str]]:
	lookup = _get_column_lookup(df)
	data: dict[str, pd.Series] = {}
	source_map: dict[str, str] = {}
	missing_columns: list[str] = []

	for canonical in CANONICAL_COLUMNS:
		canonical_match = lookup.get(_normalize_header_name(canonical))
		alias_match = None
		for alias in COLUMN_ALIASES.get(canonical, ()):  # pragma: no branch
			matched = lookup.get(_normalize_header_name(alias))
			if matched:
				alias_match = matched
				break

		if canonical_match and alias_match and canonical_match != alias_match:
			data[canonical] = _merge_columns(df[canonical_match], df[alias_match])
			source_map[canonical] = f"{canonical_match} + {alias_match}"
		elif canonical_match:
			data[canonical] = df[canonical_match]
			source_map[canonical] = canonical_match
		elif alias_match:
			data[canonical] = df[alias_match]
			source_map[canonical] = alias_match
		else:
			data[canonical] = pd.Series([""] * len(df), index=df.index)
			source_map[canonical] = "<created-empty>"
			missing_columns.append(canonical)

	normalized = pd.DataFrame(data)

	if not drop_extra_columns:
		consumed = set()
		for source in source_map.values():
			if source == "<created-empty>":
				continue
			for part in source.split("+"):
				consumed.add(part.strip())

		extras = [column for column in df.columns if column not in consumed and column not in normalized.columns]
		for column in extras:
			normalized[column] = df[column]

	return normalized, source_map, missing_columns


def normalize_excel_layout(
	input_path: Path,
	output_path: Path,
	target_sheet: str | None,
	drop_extra_columns: bool,
	create_backup: bool,
) -> tuple[str, dict[str, str], list[str], int]:
	if not input_path.exists() or not input_path.is_file():
		raise FileNotFoundError(f"Input Excel file not found: {input_path}")

	workbook = pd.read_excel(input_path, sheet_name=None)
	if not workbook:
		raise ValueError("Input workbook has no sheets")

	available_sheets = list(workbook.keys())
	sheet_name = target_sheet or available_sheets[0]
	if sheet_name not in workbook:
		raise ValueError(f"Sheet '{sheet_name}' not found. Available sheets: {available_sheets}")

	target_df = workbook[sheet_name]
	normalized_df, source_map, missing_columns = normalize_dataframe(target_df, drop_extra_columns=drop_extra_columns)
	workbook[sheet_name] = normalized_df

	output_path.parent.mkdir(parents=True, exist_ok=True)

	same_destination = input_path.resolve() == output_path.resolve()
	if same_destination and create_backup:
		stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		backup_path = input_path.with_name(f"{input_path.stem}.backup_{stamp}{input_path.suffix}")
		shutil.copy2(input_path, backup_path)

	with pd.ExcelWriter(output_path) as writer:
		for current_sheet_name, sheet_df in workbook.items():
			sheet_df.to_excel(writer, sheet_name=current_sheet_name, index=False)

	return sheet_name, source_map, missing_columns, len(target_df)


def _build_arg_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		description="Normalize an MLHD2 mission log workbook to the current column layout.",
	)
	parser.add_argument("input", type=Path, help="Path to source .xlsx file")
	parser.add_argument(
		"-o",
		"--output",
		type=Path,
		default=None,
		help="Path to write normalized workbook (default: overwrite input)",
	)
	parser.add_argument(
		"--sheet",
		default=None,
		help="Sheet name to normalize (default: first sheet)",
	)
	parser.add_argument(
		"--drop-extra-columns",
		action="store_true",
		help="Drop non-standard columns instead of preserving them at the end",
	)
	parser.add_argument(
		"--no-backup",
		action="store_true",
		help="Disable automatic backup when overwriting input file",
	)
	return parser


def main() -> int:
	args = _build_arg_parser().parse_args()
	input_path = args.input
	output_path = args.output or input_path

	try:
		sheet_name, source_map, missing_columns, row_count = normalize_excel_layout(
			input_path=input_path,
			output_path=output_path,
			target_sheet=args.sheet,
			drop_extra_columns=args.drop_extra_columns,
			create_backup=not args.no_backup,
		)
	except Exception as exc:
		print(f"❌ Failed to normalize workbook: {exc}")
		return 1

	print(f"✅ Normalized sheet: {sheet_name}")
	print(f"Rows processed: {row_count}")
	print(f"Output file: {output_path}")
	if missing_columns:
		print(f"Columns created empty ({len(missing_columns)}): {', '.join(missing_columns)}")
	else:
		print("No missing canonical columns were created.")

	print("Column mapping:")
	for canonical in CANONICAL_COLUMNS:
		print(f"  - {canonical} <= {source_map.get(canonical, '<unknown>')}")

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
