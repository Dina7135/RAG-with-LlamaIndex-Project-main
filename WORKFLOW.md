# Workflow Diagram

## Event-Driven Architecture Flow

```mermaid
graph TD
    START[START] --> LOAD[Load Documents]
    LOAD -->|Success| DOCS_LOADED[DOCUMENTS_LOADED]
    LOAD -->|Failure| FAILED[WORKFLOW_FAILED]
    
    DOCS_LOADED --> EXTRACT[Extract Structured Data]
    EXTRACT -->|Success| DATA_EXTRACTED[DATA_EXTRACTED]
    EXTRACT -->|Failure| FAILED
    
    DATA_EXTRACTED --> CHUNK[Chunk Documents]
    CHUNK -->|Success| NODES_READY[NODES_READY]
    CHUNK -->|Failure| FAILED
    
    NODES_READY --> EMBED[Prepare Embedding Model]
    EMBED -->|Success| EMBEDDING_READY[EMBEDDING_READY]
    EMBED -->|Failure| FAILED
    
    EMBEDDING_READY --> VECTOR[Prepare Vector Store]
    VECTOR -->|Success| VECTOR_STORE_READY[VECTOR_STORE_READY]
    VECTOR -->|Failure| FAILED
    
    VECTOR_STORE_READY --> INDEX[Index Documents]
    INDEX -->|Success| COMPLETE[WORKFLOW_COMPLETE]
    INDEX -->|Failure| FAILED
    
    style START fill:#e1f5ff
    style COMPLETE fill:#d4edda
    style FAILED fill:#f8d7da
    style DOCS_LOADED fill:#fff3cd
    style DATA_EXTRACTED fill:#fff3cd
    style NODES_READY fill:#fff3cd
    style EMBEDDING_READY fill:#fff3cd
    style VECTOR_STORE_READY fill:#fff3cd
```

## Query Processing Flow

```mermaid
graph TD
    Q[User Question] --> ROUTER{LlamaIndex Router}
    
    ROUTER -->|Structured Query| PLANNER[Structured Query Planner]
    ROUTER -->|Semantic Query| SEMANTIC[Semantic Search]
    
    PLANNER --> RETRIEVER[Structured Data Retriever]
    RETRIEVER --> FILTERS[Apply Filters]
    FILTERS --> RESULTS[Results]
    
    RESULTS --> COMPOSER[Answer Composer]
    SEMANTIC --> COMPOSER
    
    COMPOSER -->|Has LLM| SYNTHESIZER[Response Synthesizer]
    COMPOSER -->|No LLM| FORMAT[Format Results]
    
    SYNTHESIZER --> ANSWER[Final Answer]
    FORMAT --> ANSWER
    
    ANSWER --> UI[Gradio UI]
    
    style ROUTER fill:#e1f5ff
    style PLANNER fill:#fff3cd
    style RETRIEVER fill:#fff3cd
    style COMPOSER fill:#fff3cd
    style SYNTHESIZER fill:#d4edda
    style ANSWER fill:#d4edda
```

## Data Extraction Flow

```mermaid
graph TD
    MD[Markdown Files] --> READER[SimpleDirectoryReader]
    READER --> DOCS[Documents]
    
    DOCS --> PARSER[SentenceSplitter]
    PARSER --> NODES[Nodes]
    
    DOCS --> EXTRACTOR[StructuredDataExtractor]
    EXTRACTOR --> SECTIONS[Parse Sections]
    SECTIONS --> CLASSIFY[Classify Section]
    CLASSIFY --> DECISIONS{Decisions?}
    CLASSIFY --> RULES{Rules?}
    CLASSIFY --> WARNINGS{Warnings?}
    
    DECISIONS -->|Yes| DEC_ITEMS[Decision Items]
    RULES -->|Yes| RULE_ITEMS[Rule Items]
    WARNINGS -->|Yes| WARN_ITEMS[Warning Items]
    
    DEC_ITEMS --> JSON[structured_data.json]
    RULE_ITEMS --> JSON
    WARN_ITEMS --> JSON
    
    style EXTRACTOR fill:#e1f5ff
    style JSON fill:#d4edda
```

## Component Architecture

```mermaid
graph TB
    subgraph "UI Layer"
        GRADIO[Gradio Interface]
    end
    
    subgraph "Query Layer"
        ROUTER[LlamaIndex Router]
        PLANNER[Query Planner]
        RETRIEVER[Data Retriever]
        COMPOSER[Answer Composer]
    end
    
    subgraph "Search Layer"
        SEMANTIC[Semantic Search Engine]
        POSTPROCESSOR[Node Postprocessor]
        SYNTHESIZER[Response Synthesizer]
    end
    
    subgraph "Data Layer"
        EXTRACTOR[Data Extractor]
        STRUCTURED[Structured Data JSON]
        VECTOR[Pinecone Vector Store]
    end
    
    subgraph "Workflow Layer"
        ENGINE[Workflow Engine]
        STATE[Workflow State]
        EVENTS[Workflow Events]
    end
    
    GRADIO --> ROUTER
    ROUTER --> PLANNER
    ROUTER --> SEMANTIC
    
    PLANNER --> RETRIEVER
    RETRIEVER --> STRUCTURED
    
    SEMANTIC --> VECTOR
    SEMANTIC --> POSTPROCESSOR
    
    RETRIEVER --> COMPOSER
    SEMANTIC --> COMPOSER
    
    COMPOSER --> SYNTHESIZER
    SYNTHESIZER --> GRADIO
    
    EXTRACTOR --> STRUCTURED
    ENGINE --> STATE
    STATE --> EVENTS
    
    style GRADIO fill:#e1f5ff
    style ROUTER fill:#fff3cd
    style SYNTHESIZER fill:#d4edda
    style STRUCTURED fill:#d4edda
```

## Key Components

### LlamaIndex Components Used
- **SimilarityPostprocessor**: Filters search results by similarity score
- **Response Synthesizer**: Generates natural language responses from retrieved context
- **LLMSingleSelector**: Intelligently routes queries between semantic and structured search
- **QueryEngineTool**: Tools used by the router for decision making

### Custom Components
- **StructuredDataExtractor**: Extracts decisions, rules, and warnings from markdown
- **LlamaIndexRouter**: Wrapper around LlamaIndex selector with fallback logic
- **WorkflowEngine**: Event-driven workflow engine with state management
- **SimpleSemanticFallback**: Fallback semantic search when vector store unavailable
