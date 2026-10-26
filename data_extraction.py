import hashlib
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SourceReference:
    tool: str
    file: str
    anchor: str
    line_range: List[int]


class StructuredDataExtractor:
    SCHEMA_VERSION = "1.0"
    TOOL_NAME = "md-structured-extractor"

    def extract_from_directory(self, source_dir: str) -> Dict[str, Any]:
        source_dir = os.path.abspath(source_dir)
        markdown_files = self._collect_markdown_files(source_dir)
        sources = [self._build_source_entry(path, source_dir) for path in markdown_files]

        items = {
            "decisions": [],
            "rules": [],
            "warnings": [],
        }

        for path in markdown_files:
            lines = self._read_lines(path)
            sections = self._parse_sections(lines)
            for section in sections:
                category = self._classify_section(section["heading"], section["content"])
                extracted = self._extract_items_from_section(path, section, category)
                for item in extracted:
                    if item:
                        items[category].append(item)

        return {
            "schema_version": self.SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sources": sources,
            "items": items,
        }

    def _collect_markdown_files(self, source_dir: str) -> List[str]:
        markdown_files = []
        for root, _, files in os.walk(source_dir):
            for name in files:
                if name.lower().endswith(".md"):
                    markdown_files.append(os.path.join(root, name))
        return sorted(markdown_files)

    def _read_lines(self, path: str) -> List[str]:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.readlines()

    def _build_source_entry(self, path: str, root_path: str) -> Dict[str, Any]:
        stat = os.stat(path)
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            digest.update(handle.read())

        return {
            "tool": self.TOOL_NAME,
            "root_path": root_path,
            "file": os.path.relpath(path, root_path),
            "last_modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "hash": f"sha256:{digest.hexdigest()}",
        }

    def _parse_sections(self, lines: List[str]) -> List[Dict[str, Any]]:
        sections: List[Dict[str, Any]] = []
        current = {
            "heading": "root",
            "level": 0,
            "start_line": 1,
            "content": [],
            "end_line": len(lines),
        }

        heading_expr = re.compile(r"^(#{1,6})\s+(.*)$")
        for index, raw in enumerate(lines, start=1):
            line = raw.rstrip("\n")
            match = heading_expr.match(line)
            if match:
                if current["content"] or current["heading"] != "root":
                    current["end_line"] = index - 1
                    sections.append(current)
                current = {
                    "heading": match.group(2).strip(),
                    "level": len(match.group(1)),
                    "start_line": index,
                    "content": [],
                    "end_line": len(lines),
                }
            else:
                current["content"].append((index, line))

        if current["heading"] or current["content"]:
            current["end_line"] = len(lines)
            sections.append(current)

        return sections

    def _classify_section(self, heading: str, content: List[Tuple[int, str]]) -> str:
        text = " ".join([heading] + [line for _, line in content]).lower()
        # Check warnings first to prioritize them
        if any(word in text for word in ["warning", "warnings", "אזהרה", "אזהרות", "רגיש", "לא לגעת", "זהירות", "סיכון", "caution", "note", "important", "attention", "critical", "sensitive", "do not", "never"]):
            return "warnings"
        if any(word in text for word in ["decision", "decisions", "החלטה", "החלטות", "נבחר", "הוחלט", "בחרו", "chosen", "selected", "stack", "architecture"]):
            return "decisions"
        if any(word in text for word in ["rule", "rules", "guideline", "guidelines", "הנחיה", "הנחיות", "כללים", "חייב", "אסור", "יש", "must", "should", "convention", "pattern", "standard", "security", "authentication", "authorization"]):
            return "rules"

        heading_lower = heading.lower()
        if any(word in heading_lower for word in ["warning", "אזהרה", "רגיש", "לא לגעת", "caution", "note", "critical"]):
            return "warnings"
        if any(word in heading_lower for word in ["decision", "החלטה", "stack", "architecture", "technology"]):
            return "decisions"
        if any(word in heading_lower for word in ["rule", "guideline", "הנחיה", "כללים", "convention", "pattern", "security", "authentication"]):
            return "rules"

        return "rules"

    def _extract_items_from_section(
        self, path: str, section: Dict[str, Any], category: str
    ) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        bullets = self._extract_bullets(section["content"])
        source = self._build_reference(path, section)

        if bullets:
            for bullet in bullets:
                # Classify each bullet individually to catch warnings
                bullet_category = self._classify_sentence(bullet)
                final_category = bullet_category if bullet_category else category
                item = self._build_item(final_category, section["heading"], bullet, source)
                if item:
                    items.append(item)
            return items

        sentences = self._extract_sentences(section["content"])
        for sentence in sentences:
            sentence_category = self._classify_sentence(sentence)
            if sentence_category:
                item = self._build_item(sentence_category, section["heading"], sentence, source)
                if item:
                    items.append(item)

        if items:
            return items

        text = self._clean_block_text(section["content"])
        if text:
            item = self._build_item(category, section["heading"], text, source)
            if item:
                items.append(item)
        return items

    def _extract_sentences(self, content: List[Tuple[int, str]]) -> List[str]:
        text = " ".join(line for _, line in content if line.strip())
        raw_sentences = re.split(r"(?<=[\.\?!])\s+", text)
        return [sentence.strip() for sentence in raw_sentences if sentence.strip()]

    def _classify_sentence(self, sentence: str) -> Optional[str]:
        lower = sentence.lower()
        
        decision_keywords = ["decision", "decisions", "החלטה", "החלטות", "נבחר", "הוחלט", "בחרו", "בחרנו", "מועדף", "bedrock", "bun", "vue", "pinia", "vite", "websocket", "dynamodb", "cognito", "s3", "cloudfront", "memorydb", "redis", "sharp"]
        rule_keywords = ["rule", "rules", "guideline", "guidelines", "הנחיה", "הנחיות", "כללים", "חייב", "אסור", "יש", "must", "should", "recommended", "standard", "convention", "pattern", "architecture", "uses", "leverages", "integration", "framework", "library", "service", "component", "security", "authentication", "authorization"]
        warning_keywords = ["warning", "warnings", "אזהרה", "אזהרות", "רגיש", "לא לגעת", "לא לשנות", "זהירות", "סיכון", "vulnerable", "not safe", "don't", "caution", "critical", "high", "attention", "note", "important", "careful", "strict", "שים לב", "never", "do not", "sensitive", "without approval", "requires approval"]
        
        if any(word in lower for word in warning_keywords):
            return "warnings"
        if any(word in lower for word in decision_keywords):
            return "decisions"
        if any(word in lower for word in rule_keywords):
            return "rules"
        return None

    def _extract_bullets(self, content: List[Tuple[int, str]]) -> List[str]:
        bullets = []
        bullet_expr = re.compile(r"^\s*([-*+]|\d+\.)\s+(.*)$")
        for _, line in content:
            match = bullet_expr.match(line)
            if match:
                bullets.append(match.group(2).strip())
        return bullets

    def _clean_block_text(self, content: List[Tuple[int, str]]) -> str:
        lines = [line.strip() for _, line in content if line.strip()]
        return " ".join(lines).strip()

    def _build_reference(self, path: str, section: Dict[str, Any]) -> Dict[str, Any]:
        observed_at = datetime.fromtimestamp(os.stat(path).st_mtime, timezone.utc).isoformat()
        return {
            "tool": self.TOOL_NAME,
            "file": os.path.relpath(path),
            "anchor": self._slugify(section["heading"]),
            "line_range": [section["start_line"], section["end_line"]],
            "observed_at": observed_at,
        }

    def _slugify(self, text: str) -> str:
        text = text.strip().lower()
        text = re.sub(r"[^\w\-]+", "-", text)
        text = re.sub(r"-+", "-", text)
        return text.strip("-") or "root"

    def _build_item(self, category: str, heading: str, content: str, source: Dict[str, Any]) -> Dict[str, Any]:
        base_id = hashlib.sha256(f"{category}:{heading}:{content}".encode("utf-8")).hexdigest()[:12]
        if category == "decisions":
            return {
                "id": f"dec-{base_id}",
                "title": heading or content[:50],
                "summary": content,
                "tags": self._infer_tags(heading, content),
                "source": source,
                "observed_at": source.get("observed_at", ""),
            }
        if category == "rules":
            return {
                "id": f"rule-{base_id}",
                "rule": content,
                "scope": heading or "general",
                "notes": "",
                "source": source,
                "observed_at": source.get("observed_at", ""),
            }
        if category == "warnings":
            return {
                "id": f"warn-{base_id}",
                "area": heading or "general",
                "message": content,
                "severity": self._infer_severity(content),
                "source": source,
                "observed_at": source.get("observed_at", ""),
            }
        return {}

    def _infer_tags(self, heading: str, content: str) -> List[str]:
        candidate_text = f"{heading} {content}".lower()
        tags = []
        for keyword in ["db", "architecture", "ui", "backend", "api", "security", "auth", "performance"]:
            if keyword in candidate_text:
                tags.append(keyword)
        return sorted(set(tags))

    def _infer_severity(self, content: str) -> str:
        lowered = content.lower()
        if any(keyword in lowered for keyword in ["high", "very high", "critical", "חמור", "גבוה"]):
            return "high"
        if any(keyword in lowered for keyword in ["low", "medium", "בינוני", "נמוך"]):
            return "medium"
        return "medium"
