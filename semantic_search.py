import os
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv()

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.embeddings.cohere import CohereEmbedding
from llama_index.vector_stores.pinecone import PineconeVectorStore
from pinecone import Pinecone
from pinecone.exceptions import NotFoundException


class SemanticSearchEngine:
    def __init__(self, source_dir: str, pinecone_index_name: str = "first", namespace: str = "kiro-steering"):
        self.source_dir = source_dir
        self.pinecone_index_name = pinecone_index_name
        self.namespace = namespace
        self.index = None
        self._initialize()

    def _initialize(self) -> None:
        if not os.path.isdir(self.source_dir):
            return

        api_key_cohere = os.getenv("COHERE_API_KEY")
        api_key_pinecone = os.getenv("PINECONE_API_KEY")

        if not api_key_cohere or not api_key_pinecone:
            return

        try:
            reader = SimpleDirectoryReader(input_dir=self.source_dir)
            documents = reader.load_data()

            if not documents:
                return

            parser = SentenceSplitter(chunk_size=500, chunk_overlap=20)
            nodes = parser.get_nodes_from_documents(documents=documents, show_progress=False)

            embed_model = CohereEmbedding(
                api_key=api_key_cohere,
                model_name="embed-english-v3.0",
                input_type="search_document",
            )

            pc = Pinecone(api_key=api_key_pinecone)
            try:
                pinecone_index = pc.Index(self.pinecone_index_name)
            except NotFoundException:
                return

            vector_store = PineconeVectorStore(pinecone_index=pinecone_index, namespace=self.namespace)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)

            self.index = VectorStoreIndex.from_documents(
                documents=documents,
                storage_context=storage_context,
                embed_model=embed_model,
            )
        except Exception:
            return

    def search(self, question: str, top_k: int = 3) -> str:
        if self.index is None:
            return f"סוג השליפה: חיפוש סמנטי. משימה לא הושלמה — השקעה בחיפוש סמנטי לא הוקמה עדיין."

        try:
            retriever = self.index.as_retriever(similarity_top_k=top_k)
            results = retriever.retrieve(question)

            # Apply Node Postprocessor to filter results by similarity
            postprocessor = SimilarityPostprocessor(similarity_cutoff=0.5)
            processed_results = postprocessor.postprocess_nodes(results, query_str=question)

            if not processed_results:
                return f"לא נמצאו תוצאות רלוונטיות בחיפוש סמנטי עבור: '{question}'"

            answer_lines = [f"תוצאות חיפוש סמנטי עבור '{question}':"]
            for i, result in enumerate(processed_results, start=1):
                content = result.get_content() if hasattr(result, 'get_content') else str(result.text)[:200]
                answer_lines.append(f"{i}. {content}")

            return "\n".join(answer_lines)
        except Exception as e:
            return f"שגיאה בחיפוש סמנטי: {str(e)}"


class SimpleSemanticFallback:
    def __init__(self, source_dir: str):
        self.documents = {}
        self._load_documents(source_dir)

    def _load_documents(self, source_dir: str) -> None:
        if not os.path.isdir(source_dir):
            return
        for filename in os.listdir(source_dir):
            if filename.endswith(".md"):
                filepath = os.path.join(source_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        self.documents[filename] = f.read()
                except Exception:
                    pass

    def _extract_sentences(self, text: str) -> List[str]:
        """חלוק טקסט למשפטים ושורות משמעותיות."""
        sentences = []
        for line in text.split("\n"):
            line = line.strip()
            # Remove markdown headers
            if line.startswith("#"):
                continue
            # Remove bullet points
            if line.startswith("-") or line.startswith("*"):
                line = line[1:].strip()
            if line and len(line) > 5:
                sentences.append(line)
        return sentences

    def _score_sentence(self, sentence: str, question_words: set) -> int:
        """דרג משפט לפי כמה מילים מהשאלה יש בו."""
        sentence_words = set(word.lower() for word in sentence.split())
        return len(question_words & sentence_words)

    def search(self, question: str) -> str:
        if not self.documents:
            return "לא נמצאו מסמכים לחיפוש."

        # פרק את השאלה למילים חשובות (בעלות 2+ תווים)
        question_words = set(
            word.lower() for word in question.split() if len(word) > 1
        )

        # אסוף משפטים עם ציונים
        scored_sentences = []
        for doc_name, content in self.documents.items():
            sentences = self._extract_sentences(content)
            for sentence in sentences:
                score = self._score_sentence(sentence, question_words)
                # Accept sentences with some match or if they're substantial
                if score > 0 or (len(sentence.split()) > 3 and any(word in sentence.lower() for word in ["rtl", "interface", "ui", "design", "guideline"])):
                    if score == 0:
                        score = 1  # Give minimal score for substantial sentences
                    scored_sentences.append((score, doc_name, sentence))

        if not scored_sentences:
            return f"לא נמצאה תשובה לשאלה: {question}"

        # דרג לפי ציון (מהגבוה לנמוך)
        scored_sentences.sort(reverse=True)

        # קח את 5 המשפטים הרלוונטיים ביותר
        top_results = scored_sentences[:5]

        answer_lines = [f"תוצאות חיפוש עבור: {question}\n"]
        for score, doc_name, sentence in top_results:
            answer_lines.append(f"• {sentence} [{doc_name}]")

        return "\n".join(answer_lines)
