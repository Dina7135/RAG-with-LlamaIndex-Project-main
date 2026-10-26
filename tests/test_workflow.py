import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import workflow
from workflow import WorkflowEngine, WorkflowState


class WorkflowEngineTests(unittest.TestCase):
    def test_missing_source_dir_fails(self):
        state = WorkflowState(source_dir="missing-dir", pinecone_index_name="first")
        engine = WorkflowEngine()

        result = engine.run(state)

        self.assertEqual(result.name, "WORKFLOW_FAILED")
        self.assertTrue(any("source directory not found" in error.lower() for error in state.errors))

    def test_empty_directory_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = WorkflowState(source_dir=tmpdir, pinecone_index_name="first")
            engine = WorkflowEngine()

            with patch("workflow.SimpleDirectoryReader") as reader_class:
                reader_class.return_value.load_data.return_value = []
                result = engine.run(state)

            self.assertEqual(result.name, "WORKFLOW_FAILED")
            self.assertTrue(any("no documents found" in error.lower() for error in state.errors))

    def test_missing_pinecone_index_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = WorkflowState(source_dir=tmpdir, pinecone_index_name="first")
            engine = WorkflowEngine()

            with patch("workflow.SimpleDirectoryReader") as reader_class, patch.dict(os.environ, {"COHERE_API_KEY": "test-key", "PINECONE_API_KEY": "test-key"}):
                reader_class.return_value.load_data.return_value = [object()]

                with patch("workflow.SentenceSplitter") as splitter_class:
                    splitter_class.return_value.get_nodes_from_documents.return_value = [object()]

                    with patch("workflow.Pinecone") as pinecone_class:
                        pinecone_client = MagicMock()
                        pinecone_client.Index.side_effect = workflow.NotFoundException()
                        pinecone_class.return_value = pinecone_client

                        result = engine.run(state)

            self.assertEqual(result.name, "WORKFLOW_FAILED")
            self.assertTrue(any("pinecone index 'first' not found" in error.lower() for error in state.errors))

    def test_full_event_flow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = WorkflowState(source_dir=tmpdir, pinecone_index_name="first")
            state.structured_data_file = os.path.join(tmpdir, "structured_data.json")
            engine = WorkflowEngine()

            with patch("workflow.SimpleDirectoryReader") as reader_class, patch.dict(os.environ, {"COHERE_API_KEY": "test-key", "PINECONE_API_KEY": "test-key"}):
                reader_class.return_value.load_data.return_value = [object()]

                with patch.object(workflow.StructuredDataExtractor, "extract_from_directory", return_value={"schema_version": "1.0", "generated_at": "2026-01-01T00:00:00+00:00", "sources": [], "items": {"decisions": [], "rules": [], "warnings": []}}):
                    with patch("workflow.SentenceSplitter") as splitter_class:
                        splitter_class.return_value.get_nodes_from_documents.return_value = [object()]

                        with patch("workflow.Pinecone") as pinecone_class, patch("workflow.PineconeVectorStore") as vector_store_class, patch.object(workflow.VectorStoreIndex, "from_documents", return_value=object()):
                            pinecone_client = MagicMock()
                            pinecone_client.Index.return_value = MagicMock()
                            pinecone_class.return_value = pinecone_client
                            vector_store_class.return_value = MagicMock()

                            result = engine.run(state)

            self.assertEqual(result.name, "WORKFLOW_COMPLETE")
            self.assertEqual(len(state.errors), 0)
            self.assertTrue(any("workflow completed successfully" in entry.lower() for entry in state.history))


if __name__ == "__main__":
    unittest.main()
