import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from semantic_search import SimpleSemanticFallback
from netfree_unstrict_ssl import unstrict_ssl
unstrict_ssl()
# ניסיון לטעון LLM
try:
    from llama_index.llms.openai import OpenAI
    from llama_index.core.response_synthesizers import ResponseMode, get_response_synthesizer
    from llama_index.core.selectors import LLMSingleSelector
    HAS_LLM = True
except ImportError:
    HAS_LLM = False


class QueryMode(str, Enum):
    SEMANTIC = "semantic"
    STRUCTURED = "structured"


@dataclass
class StructuredQuery:
    item_type: str
    filters: Dict[str, Any]
    text: str


class QueryRouter:
    STRUCTURED_KEYWORDS = [
        "decision",
        "decisions",
        "rule",
        "rules",
        "guideline",
        "guidelines",
        "החלטה",
        "החלטות",
        "הנחיה",
        "הנחיות",
        "כללים",
        "warning",
        "warnings",
        "אזהרה",
        "אזהרות",
        "רגיש",
        "לא לגעת",
        "sensitive",
        "latest",
        "recent",
        "last week",
        "last month",
        "עדכני",
        "עדכנית",
        "נכון לעכשיו",
        "שבוע האחרון",
        "חודש האחרון",
        "רשימה",
        "list",
    ]

    def route(self, question: str, structured_schema: Dict[str, Any]) -> QueryMode:
        text = question.lower()
        if not question.strip():
            return QueryMode.SEMANTIC

        if any(keyword in text for keyword in self.STRUCTURED_KEYWORDS):
            return QueryMode.STRUCTURED

        # If we have structured data and the question contains any schema term,
        # prefer structured retrieval.
        if structured_schema and structured_schema.get("items"):
            schema_keys = " ".join(structured_schema["items"].keys())
            if any(word in text for word in schema_keys.split()):
                return QueryMode.STRUCTURED

        return QueryMode.SEMANTIC


class LlamaIndexRouter:
    """Router using LlamaIndex RouterQueryEngine for intelligent query routing."""
    
    def __init__(self):
        self.llm = None
        self._initialize_llm()
    
    def _initialize_llm(self) -> None:
        """Initialize LLM for LlamaIndex Router."""
        if not HAS_LLM:
            return
        
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                self.llm = OpenAI(api_key=api_key, model="gpt-3.5-turbo")
            except Exception:
                self.llm = None
    
    def route(self, question: str, structured_schema: Dict[str, Any]) -> QueryMode:
        """Route query using LlamaIndex Router or fallback to heuristic."""
        if not self.llm:
            # Fallback to heuristic router
            return self._route_with_heuristics(question, structured_schema)
        
        try:
            return self._route_with_llamaindex(question, structured_schema)
        except Exception:
            # Fallback to heuristic router on error
            return self._route_with_heuristics(question, structured_schema)
    
    def _route_with_llamaindex(self, question: str, structured_schema: Dict[str, Any]) -> QueryMode:
        """Use LlamaIndex LLMSingleSelector for intelligent routing."""
        from llama_index.core.tools import QueryEngineTool, ToolMetadata
        from llama_index.core import QueryEngine
        from llama_index.core.response import Response
        
        # Create mock query engines for semantic and structured
        class MockSemanticEngine(QueryEngine):
            def query(self, query_str, **kwargs):
                return Response(response="semantic")
        
        class MockStructuredEngine(QueryEngine):
            def query(self, query_str, **kwargs):
                return Response(response="structured")
        
        semantic_engine = MockSemanticEngine()
        structured_engine = MockStructuredEngine()
        
        # Create query engine tools
        semantic_tool = QueryEngineTool(
            query_engine=semantic_engine,
            metadata=ToolMetadata(
                name="semantic_search",
                description="Use for general semantic search questions about the documentation"
            )
        )
        
        structured_tool = QueryEngineTool(
            query_engine=structured_engine,
            metadata=ToolMetadata(
                name="structured_data",
                description="Use for questions about decisions, rules, warnings, lists, or time-based queries"
            )
        )
        
        # Create selector
        selector = LLMSingleSelector.from_defaults(llm=self.llm)
        
        # Use selector to choose the appropriate tool
        from llama_index.core import Document
        result = selector.select(
            [semantic_tool, structured_tool],
            query=question
        )
        
        # Determine mode based on selector result
        if result.individual_outputs and len(result.individual_outputs) > 0:
            selected_name = result.individual_outputs[0].tool_name
            if selected_name == "structured_data":
                return QueryMode.STRUCTURED
        
        return QueryMode.SEMANTIC
    
    def _route_with_heuristics(self, question: str, structured_schema: Dict[str, Any]) -> QueryMode:
        """Fallback heuristic routing."""
        text = question.lower()
        if not question.strip():
            return QueryMode.SEMANTIC

        if any(keyword in text for keyword in QueryRouter.STRUCTURED_KEYWORDS):
            return QueryMode.STRUCTURED

        if structured_schema and structured_schema.get("items"):
            schema_keys = " ".join(structured_schema["items"].keys())
            if any(word in text for word in schema_keys.split()):
                return QueryMode.STRUCTURED

        return QueryMode.SEMANTIC


class StructuredQueryPlanner:
    def __init__(self):
        self.llm = None
        self._initialize_llm()
    
    def _initialize_llm(self) -> None:
        """יצור LLM אם יש OpenAI API Key."""
        if not HAS_LLM:
            return
        
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                self.llm = OpenAI(api_key=api_key, model="gpt-3.5-turbo")
            except Exception:
                self.llm = None

    def plan(self, question: str, schema: Dict[str, Any]) -> StructuredQuery:
        text = question.strip()
        
        # אם יש LLM, השתמש בו ליצירת שאילתה
        if self.llm:
            return self._plan_with_llm(text, schema)
        
        # אחרת, השתמש בהיוריסטיקה
        return self._plan_with_heuristics(text, schema)
    
    def _plan_with_llm(self, question: str, schema: Dict[str, Any]) -> StructuredQuery:
        """בקשה מ-LLM ליצור שאילתה מובנית."""
        schema_str = json.dumps(schema.get("items", {}), ensure_ascii=False)
        
        prompt = f"""בהינתן סכמה של נתונים מובנים, צור שאילתה מובנית כדי לענות על השאלה.

סכמה:
{schema_str}

שאלה: {question}

ענה בפורמט JSON בלבד (ללא טקסט נוסף):
{{
  "item_type": "decisions" | "rules" | "warnings",
  "filters": {{}},
  "explanation": "הסבר קצר"
}}"""
        
        try:
            response = self.llm.complete(prompt)
            result_text = response.text.strip()
            
            # נסה לחלץ JSON
            if "{" in result_text and "}" in result_text:
                json_str = result_text[result_text.find("{"):result_text.rfind("}")+1]
                result = json.loads(json_str)
                return StructuredQuery(
                    item_type=result.get("item_type", "decisions"),
                    filters=result.get("filters", {}),
                    text=question
                )
        except Exception:
            pass
        
        # fallback להיוריסטיקה
        return self._plan_with_heuristics(question, schema)

    def _plan_with_heuristics(self, question: str, schema: Dict[str, Any]) -> StructuredQuery:
        """תכנון בהיוריסטיקה (בלי LLM)."""
        item_type = self._infer_item_type(question)
        filters = self._infer_filters(question)
        return StructuredQuery(item_type=item_type, filters=filters, text=question)

    def _infer_item_type(self, question: str) -> str:
        lower = question.lower()
        if any(word in lower for word in ["decision", "decisions", "החלטה", "החלטות"]):
            return "decisions"
        if any(word in lower for word in ["rule", "rules", "guideline", "guidelines", "הנחיה", "הנחיות", "כללים"]):
            return "rules"
        if any(word in lower for word in ["warning", "warnings", "אזהרה", "אזהרות", "רגיש", "לא לגעת", "sensitive"]):
            return "warnings"
        return "decisions"

    def _infer_filters(self, question: str) -> Dict[str, Any]:
        filters: Dict[str, Any] = {}
        lower = question.lower()

        if any(pattern in lower for pattern in ["last week", "שבוע האחרון"]):
            filters["observed_after"] = self._now_utc() - timedelta(days=7)
        elif any(pattern in lower for pattern in ["last month", "חודש האחרון"]):
            filters["observed_after"] = self._now_utc() - timedelta(days=30)
        elif any(pattern in lower for pattern in ["recent", "עדכני", "נכון לעכשיו"]):
            filters["observed_after"] = self._now_utc() - timedelta(days=30)

        if any(word in lower for word in ["high", "critical", "חמור", "גבוה"]):
            filters["severity"] = "high"
        if any(word in lower for word in ["medium", "בינוני"]):
            filters["severity"] = "medium"
        if any(word in lower for word in ["low", "נמוך"]):
            filters["severity"] = "low"

        if "rtl" in lower or "rtl" in question:
            filters["text_contains"] = "rtl"
        if "jwt" in lower:
            filters["text_contains"] = "jwt"
        if "api" in lower:
            filters["text_contains"] = "api"

        return filters

    def _now_utc(self) -> datetime:
        return datetime.now(timezone.utc)


class StructuredDataRetriever:
    def retrieve(self, structured_data: Dict[str, Any], query: StructuredQuery) -> List[Dict[str, Any]]:
        items = structured_data.get("items", {})
        candidates = []

        if query.item_type in items:
            candidates = items[query.item_type]
        else:
            for lst in items.values():
                candidates.extend(lst)

        results = []
        for item in candidates:
            if self._matches_filters(item, query.filters):
                results.append(item)

        return results

    def _matches_filters(self, item: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        if not filters:
            return True

        if "observed_after" in filters:
            observed_at = item.get("observed_at")
            if not observed_at:
                return False
            try:
                observed_dt = datetime.fromisoformat(observed_at)
            except ValueError:
                return False
            if observed_dt < filters["observed_after"]:
                return False

        if "severity" in filters and item.get("severity"):
            if item.get("severity").lower() != filters["severity"]:
                return False

        if "text_contains" in filters:
            text = " ".join(str(value) for value in item.values()).lower()
            if filters["text_contains"].lower() not in text:
                return False

        return True


class AnswerComposer:
    def __init__(self, source_dir: str = "kiro-steering"):
        self.semantic_search = SimpleSemanticFallback(source_dir)
        self.llm = None
        self._initialize_llm()
    
    def _initialize_llm(self) -> None:
        """יצור LLM אם יש OpenAI API Key."""
        if not HAS_LLM:
            return
        
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                self.llm = OpenAI(api_key=api_key, model="gpt-3.5-turbo")
            except Exception:
                self.llm = None

    def compose(
        self,
        question: str,
        mode: QueryMode,
        results: List[Dict[str, Any]],
        query: Optional[StructuredQuery] = None,
    ) -> str:
        if mode == QueryMode.SEMANTIC:
            # For semantic queries, get the fallback context (top sentences)
            context = self.semantic_search.search(question)
            # If we have an LLM available, synthesize a natural answer from context
            if self.llm:
                return self._synthesize_with_llm(question, context)
            return context

        if not results:
            return (
                "לא נמצאו פריטים מתאימים במידע המובנה עבור השאלה שלך. "
                "המערכת עוברת למצב חיפוש סמנטי.\n\n"
                + self.semantic_search.search(question)
            )

        # הכן context מתוך התוצאות
        context = self._format_results_as_context(results, query)
        
        # אם יש LLM, שתמש בו להכנת תשובה סופית
        if self.llm:
            return self._synthesize_with_llm(question, context)
        
        # אחרת, הצג את הנתונים כפי שהם
        return self._format_results_as_answer(results, query)
    
    def _format_results_as_context(self, results: List[Dict[str, Any]], query: Optional[StructuredQuery]) -> str:
        """הפוך תוצאות למחרוזת context."""
        lines = []
        for item in results:
            if query and query.item_type == "decisions":
                lines.append(f"- החלטה: {item.get('summary')} [{item['source']['file']}]")
            elif query and query.item_type == "rules":
                lines.append(f"- כלל: {item.get('rule')} [{item['source']['file']}]")
            elif query and query.item_type == "warnings":
                lines.append(f"- אזהרה: {item.get('message')} (חומרה: {item.get('severity')}) [{item['source']['file']}]")
            else:
                lines.append(f"- {json.dumps(item, ensure_ascii=False)}")
        return "\n".join(lines)
    
    def _synthesize_with_llm(self, question: str, context: str) -> str:
        """שלח את ההקשר ל-LLM להכנת תשובה סופית באמצעות Response Synthesizer."""
        try:
            # Create Response Synthesizer using LlamaIndex
            synthesizer = get_response_synthesizer(
                response_mode=ResponseMode.COMPACT,
                llm=self.llm,
            )
            
            # Convert context string to nodes for synthesizer
            from llama_index.core import Document
            doc = Document(text=context)
            
            # Synthesize response
            response = synthesizer.synthesize(
                query=question,
                nodes=[doc],
            )
            
            return response.response
        except Exception:
            # fallback: הצג את הנתונים כפי שהם
            return self._format_results_as_answer_from_context(context)
    
    def _format_results_as_answer(self, results: List[Dict[str, Any]], query: Optional[StructuredQuery]) -> str:
        """הצג תוצאות בתבנית סטטית."""
        summary_lines = [f"נתונים מובנים:"]
        for item in results:
            if query and query.item_type == "decisions":
                summary_lines.append(f"• {item.get('summary')} [{item['source']['file']}]".strip())
            elif query and query.item_type == "rules":
                summary_lines.append(f"• {item.get('rule')} [{item['source']['file']}]".strip())
            elif query and query.item_type == "warnings":
                summary_lines.append(f"• {item.get('message')} (severity={item.get('severity')}) [{item['source']['file']}]".strip())
            else:
                summary_lines.append(f"• {json.dumps(item, ensure_ascii=False)}")
        return "\n".join(summary_lines)
    
    def _format_results_as_answer_from_context(self, context: str) -> str:
        """הצג context כתשובה."""
        return f"נתונים:\n\n{context}"


def load_structured_data(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        return {"schema_version": "1.0", "generated_at": "", "sources": [], "items": {"decisions": [], "rules": [], "warnings": []}}
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def answer_question(question: str, structured_data_path: str, source_dir: str = "kiro-steering") -> str:
    structured_data = load_structured_data(structured_data_path)
    
    # Use LlamaIndexRouter for intelligent routing
    router = LlamaIndexRouter()
    mode = router.route(question, structured_data)

    composer = AnswerComposer(source_dir)

    if mode == QueryMode.SEMANTIC:
        return composer.compose(question, mode, [])

    planner = StructuredQueryPlanner()
    query = planner.plan(question, structured_data)
    retriever = StructuredDataRetriever()
    results = retriever.retrieve(structured_data, query)

    return composer.compose(question, mode, results, query)
