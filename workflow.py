import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

from netfree_unstrict_ssl import unstrict_ssl
unstrict_ssl()

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.cohere import CohereEmbedding
from llama_index.vector_stores.pinecone import PineconeVectorStore
from pinecone import Pinecone
from pinecone.exceptions import NotFoundException

from data_extraction import StructuredDataExtractor


@dataclass
class WorkflowEvent:
    name: str
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowState:
    source_dir: str
    pinecone_index_name: str
    namespace: str = "kiro-steering"
    cohere_model_name: str = "embed-english-v3.0"
    chunk_size: int = 500
    chunk_overlap: int = 20
    documents: List[Any] = field(default_factory=list)
    nodes: List[Any] = field(default_factory=list)
    embed_model: Optional[Any] = None
    vector_store: Optional[Any] = None
    storage_context: Optional[Any] = None
    index: Optional[Any] = None
    structured_data: Dict[str, Any] = field(default_factory=dict)
    structured_data_file: str = "structured_data.json"
    errors: List[str] = field(default_factory=list)
    history: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.history.append(f"ERROR: {message}")

    def add_history(self, message: str) -> None:
        self.history.append(message)


class WorkflowException(Exception):
    pass


class WorkflowEngine:
    TERMINAL_EVENTS = {"WORKFLOW_COMPLETE", "WORKFLOW_FAILED"}

    def __init__(self) -> None:
        self.handlers = {
            "START": self.load_documents,
            "DOCUMENTS_LOADED": self.extract_structured_data,
            "DATA_EXTRACTED": self.chunk_documents,
            "NODES_READY": self.prepare_embedding_model,
            "EMBEDDING_READY": self.prepare_vector_store,
            "VECTOR_STORE_READY": self.index_documents,
        }

    def run(self, state: WorkflowState) -> WorkflowEvent:
        event = WorkflowEvent("START")
        while event.name not in self.TERMINAL_EVENTS:
            handler = self.handlers.get(event.name)
            if handler is None:
                return self.fail(state, f"No handler for event: {event.name}")
            event = handler(state, event)
        return event

    def load_documents(self, state: WorkflowState, event: WorkflowEvent) -> WorkflowEvent:
        state.add_history("Start loading documents")
        if not os.path.isdir(state.source_dir):
            return self.fail(state, f"Source directory not found: {state.source_dir}")

        reader = SimpleDirectoryReader(input_dir=state.source_dir)
        state.documents = reader.load_data()

        if not state.documents:
            return self.fail(state, f"No documents found in source directory: {state.source_dir}")

        state.add_history(f"Loaded {len(state.documents)} document(s)")
        return WorkflowEvent("DOCUMENTS_LOADED")

    def extract_structured_data(self, state: WorkflowState, event: WorkflowEvent) -> WorkflowEvent:
        state.add_history("Start structured data extraction")
        extractor = StructuredDataExtractor()

        try:
            state.structured_data = extractor.extract_from_directory(state.source_dir)
        except Exception as exc:
            return self.fail(state, f"Structured data extraction failed: {exc}")

        state.structured_data_file = os.path.abspath(state.structured_data_file)
        with open(state.structured_data_file, "w", encoding="utf-8") as handle:
            import json

            json.dump(state.structured_data, handle, ensure_ascii=False, indent=2)

        extracted_items = state.structured_data.get("items", {})
        total_items = sum(len(lst) for lst in extracted_items.values())
        state.add_history(f"Extracted {total_items} structured data item(s)")
        state.add_history(f"Saved structured data to {state.structured_data_file}")

        return WorkflowEvent("DATA_EXTRACTED")

    def chunk_documents(self, state: WorkflowState, event: WorkflowEvent) -> WorkflowEvent:
        state.add_history("Start chunking documents")
        if not state.documents:
            return self.fail(state, "No documents available for chunking")

        parser = SentenceSplitter(chunk_size=state.chunk_size, chunk_overlap=state.chunk_overlap)
        state.nodes = parser.get_nodes_from_documents(documents=state.documents, show_progress=False)

        if not state.nodes:
            return self.fail(state, "Chunking produced no nodes")

        state.add_history(f"Created {len(state.nodes)} node(s)")
        return WorkflowEvent("NODES_READY")

    def prepare_embedding_model(self, state: WorkflowState, event: WorkflowEvent) -> WorkflowEvent:
        state.add_history("Prepare embedding model")
        api_key = os.getenv("COHERE_API_KEY")
        if not api_key:
            return self.fail(state, "Missing COHERE_API_KEY environment variable")

        state.embed_model = CohereEmbedding(
            api_key=api_key,
            model_name=state.cohere_model_name,
            input_type="search_document",
        )

        return WorkflowEvent("EMBEDDING_READY")

    def prepare_vector_store(self, state: WorkflowState, event: WorkflowEvent) -> WorkflowEvent:
        state.add_history("Prepare Pinecone vector store")
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            return self.fail(state, "Missing PINECONE_API_KEY environment variable")

        pc = Pinecone(api_key=api_key)
        try:
            pinecone_index = pc.Index(state.pinecone_index_name)
        except NotFoundException:
            return self.fail(state, f"Pinecone index '{state.pinecone_index_name}' not found")

        state.vector_store = PineconeVectorStore(pinecone_index=pinecone_index, namespace=state.namespace)
        state.storage_context = StorageContext.from_defaults(vector_store=state.vector_store)

        return WorkflowEvent("VECTOR_STORE_READY")

    def index_documents(self, state: WorkflowState, event: WorkflowEvent) -> WorkflowEvent:
        state.add_history("Start indexing documents")
        if not state.nodes:
            return self.fail(state, "No nodes available for indexing")
        if state.embed_model is None:
            return self.fail(state, "Embedding model is not initialized")
        if state.storage_context is None:
            return self.fail(state, "Storage context is not initialized")

        state.index = VectorStoreIndex.from_documents(
            nodes=state.nodes,
            storage_context=state.storage_context,
            embed_model=state.embed_model,
        )

        state.add_history("Workflow completed successfully")
        return WorkflowEvent("WORKFLOW_COMPLETE")

    def fail(self, state: WorkflowState, reason: str) -> WorkflowEvent:
        state.add_error(reason)
        return WorkflowEvent("WORKFLOW_FAILED", {"reason": reason})
