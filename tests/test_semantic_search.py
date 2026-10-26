import unittest
from unittest.mock import MagicMock, patch

from semantic_search import SemanticSearchEngine


class SemanticSearchEngineTests(unittest.TestCase):
    def test_node_postprocessor_filters_results(self):
        """Test that Node Postprocessor filters results by similarity."""
        engine = SemanticSearchEngine(source_dir="test-dir", pinecone_index_name="test")
        
        # Mock the index
        mock_index = MagicMock()
        mock_retriever = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever
        engine.index = mock_index
        
        # Create mock nodes with different similarities
        from llama_index.core.schema import NodeWithScore, TextNode
        
        node1 = TextNode(text="High similarity content")
        node_with_score1 = NodeWithScore(node=node1, score=0.8)
        
        node2 = TextNode(text="Low similarity content")
        node_with_score2 = NodeWithScore(node=node2, score=0.3)
        
        mock_retriever.retrieve.return_value = [node_with_score1, node_with_score2]
        
        # Search should filter out low similarity nodes
        result = engine.search("test question")
        
        # Verify retriever was called
        mock_retriever.retrieve.assert_called_once()
        
        # The result should contain high similarity content
        self.assertIn("High similarity content", result)
        
    def test_node_postprocessor_returns_empty_when_all_below_cutoff(self):
        """Test that Node Postprocessor returns empty when all results are below cutoff."""
        engine = SemanticSearchEngine(source_dir="test-dir", pinecone_index_name="test")
        
        # Mock the index
        mock_index = MagicMock()
        mock_retriever = MagicMock()
        mock_index.as_retriever.return_value = mock_retriever
        engine.index = mock_index
        
        # Create mock nodes with low similarities
        from llama_index.core.schema import NodeWithScore, TextNode
        
        node = TextNode(text="Low similarity content")
        node_with_score = NodeWithScore(node=node, score=0.2)
        
        mock_retriever.retrieve.return_value = [node_with_score]
        
        # Search should return no results message
        result = engine.search("test question")
        
        self.assertIn("לא נמצאו תוצאות רלוונטיות", result)


if __name__ == "__main__":
    unittest.main()
