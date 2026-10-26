import json
from pathlib import Path

from data_extraction import StructuredDataExtractor


def main() -> None:
    source_dir = Path("kiro-steering")
    output_file = Path("structured_data.json")

    if not source_dir.exists():
        raise SystemExit(f"Source directory not found: {source_dir}")

    extractor = StructuredDataExtractor()
    structured_data = extractor.extract_from_directory(str(source_dir))

    output_file.write_text(json.dumps(structured_data, ensure_ascii=False, indent=2), encoding="utf-8")

    counts = {key: len(value) for key, value in structured_data.get("items", {}).items()}
    print(f"Wrote {output_file}.")
    print("Item counts:")
    for item_type, count in counts.items():
        print(f"- {item_type}: {count}")


if __name__ == "__main__":
    main()
