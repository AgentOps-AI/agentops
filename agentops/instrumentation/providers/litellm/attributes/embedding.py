"""Embedding-specific attribute extraction for LiteLLM instrumentation.

This module provides functions to extract attributes specific to
embedding operations.
"""

from typing import Any, Dict, List, Union

from agentops.instrumentation.providers.litellm.utils import (
    estimate_tokens,
    safe_get_attribute,
)


def extract_embedding_request_attributes(
    input_data: Union[str, List[str], List[int], List[List[int]]], kwargs: Dict[str, Any]
) -> Dict[str, Any]:
    """Extract attributes from embedding request parameters.

    Args:
        input_data: The input text(s) or token(s) to embed
        kwargs: Additional keyword arguments

    Returns:
        Dictionary of embedding request attributes
    """
    attributes = {}

    # Analyze input
    if isinstance(input_data, str):
        # Single string input
        attributes["llm.request.input_type"] = "string"
        attributes["llm.request.input_count"] = 1
        attributes["llm.request.input_length"] = len(input_data)
        attributes["llm.request.estimated_input_tokens"] = estimate_tokens(input_data)

    elif isinstance(input_data, list):
        attributes["llm.request.input_count"] = len(input_data)

        if not input_data:
            attributes["llm.request.input_type"] = "empty_list"
        elif isinstance(input_data[0], str):
            # List of strings
            attributes["llm.request.input_type"] = "string_list"

            # Calculate total length and stats
            lengths = [len(text) for text in input_data]
            total_length = sum(lengths)

            attributes["llm.request.total_input_length"] = total_length
            attributes["llm.request.avg_input_length"] = round(total_length / len(input_data), 2)
            attributes["llm.request.min_input_length"] = min(lengths)
            attributes["llm.request.max_input_length"] = max(lengths)

            # Estimate tokens
            total_tokens = sum(estimate_tokens(text) for text in input_data)
            attributes["llm.request.estimated_total_tokens"] = total_tokens

        elif isinstance(input_data[0], int):
            # List of token IDs
            attributes["llm.request.input_type"] = "token_list"
            attributes["llm.request.token_count"] = len(input_data)

        elif isinstance(input_data[0], list):
            # List of token ID lists (batch)
            attributes["llm.request.input_type"] = "token_batch"
            attributes["llm.request.batch_size"] = len(input_data)

            # Calculate token stats
            token_counts = [len(tokens) for tokens in input_data]
            total_tokens = sum(token_counts)

            attributes["llm.request.total_token_count"] = total_tokens
            attributes["llm.request.avg_tokens_per_input"] = round(total_tokens / len(input_data), 2)
            attributes["llm.request.min_token_count"] = min(token_counts)
            attributes["llm.request.max_token_count"] = max(token_counts)

    # Model-specific parameters
    if "encoding_format" in kwargs:
        attributes["llm.request.encoding_format"] = kwargs["encoding_format"]

    if "dimensions" in kwargs:
        attributes["llm.request.dimensions"] = kwargs["dimensions"]

    # User identifier
    if "user" in kwargs:
        attributes["llm.request.user"] = kwargs["user"]

    return attributes


def extract_embedding_response_attributes(response: Any) -> Dict[str, Any]:
    """Extract attributes from embedding response.

    Args:
        response: Response object from LiteLLM

    Returns:
        Dictionary of embedding response attributes
    """
    attributes = {}

    # Data array
    data = safe_get_attribute(response, "data")
    if data and isinstance(data, list):
        attributes["llm.response.embedding_count"] = len(data)

        if data:
            # Analyze first embedding
            first_embedding = data[0]

            # Index
            index = safe_get_attribute(first_embedding, "index")
            if index is not None:
                attributes["llm.response.first_embedding_index"] = index

            # Object type
            object_type = safe_get_attribute(first_embedding, "object")
            if object_type:
                attributes["llm.response.embedding_object_type"] = object_type

            # Embedding vector
            embedding = safe_get_attribute(first_embedding, "embedding")
            if embedding and isinstance(embedding, list):
                attributes["llm.response.embedding_dimension"] = len(embedding)

                # Check if embeddings are normalized (magnitude ~1)
                if len(embedding) > 0 and all(isinstance(x, (int, float)) for x in embedding[:10]):
                    # Calculate magnitude of first few dimensions as a sample
                    sample_size = min(100, len(embedding))
                    magnitude_squared = sum(x * x for x in embedding[:sample_size])
                    estimated_magnitude = (magnitude_squared * len(embedding) / sample_size) ** 0.5

                    # Check if approximately normalized
                    if 0.95 <= estimated_magnitude <= 1.05:
                        attributes["llm.response.embeddings_normalized"] = True
                    else:
                        attributes["llm.response.embeddings_normalized"] = False
                        attributes["llm.response.estimated_magnitude"] = round(estimated_magnitude, 3)

            # Check consistency across embeddings
            if len(data) > 1:
                dimensions = set()
                for emb_data in data:
                    emb = safe_get_attribute(emb_data, "embedding")
                    if emb and isinstance(emb, list):
                        dimensions.add(len(emb))

                if len(dimensions) == 1:
                    attributes["llm.response.consistent_dimensions"] = True
                else:
                    attributes["llm.response.consistent_dimensions"] = False
                    attributes["llm.response.unique_dimensions"] = len(dimensions)

    # Model used (might differ from requested)
    model = safe_get_attribute(response, "model")
    if model:
        attributes["llm.response.model_used"] = model

    return attributes


def extract_embedding_statistics(embeddings: List[List[float]]) -> Dict[str, Any]:
    """Extract statistical information from embedding vectors.

    Args:
        embeddings: List of embedding vectors

    Returns:
        Dictionary of embedding statistics
    """
    attributes = {}

    if not embeddings or not all(isinstance(emb, list) for emb in embeddings):
        return attributes

    # Basic stats
    attributes["llm.embeddings.count"] = len(embeddings)

    if embeddings:
        # Dimension consistency
        dimensions = [len(emb) for emb in embeddings]
        unique_dims = set(dimensions)

        if len(unique_dims) == 1:
            attributes["llm.embeddings.dimension"] = dimensions[0]
        else:
            attributes["llm.embeddings.dimension_variance"] = True
            attributes["llm.embeddings.dimensions"] = list(unique_dims)

        # Calculate similarity statistics (for multiple embeddings)
        if len(embeddings) > 1 and len(unique_dims) == 1:
            try:
                # Calculate pairwise cosine similarities for a sample
                sample_size = min(10, len(embeddings))
                similarities = []

                for i in range(sample_size):
                    for j in range(i + 1, sample_size):
                        # Cosine similarity
                        dot_product = sum(a * b for a, b in zip(embeddings[i], embeddings[j]))
                        norm_i = sum(a * a for a in embeddings[i]) ** 0.5
                        norm_j = sum(a * a for a in embeddings[j]) ** 0.5

                        if norm_i > 0 and norm_j > 0:
                            similarity = dot_product / (norm_i * norm_j)
                            similarities.append(similarity)

                if similarities:
                    attributes["llm.embeddings.avg_similarity"] = round(sum(similarities) / len(similarities), 3)
                    attributes["llm.embeddings.min_similarity"] = round(min(similarities), 3)
                    attributes["llm.embeddings.max_similarity"] = round(max(similarities), 3)

            except Exception:
                # Don't fail on statistics calculation errors
                pass

    return attributes


def extract_embedding_model_attributes(model: str, response: Any) -> Dict[str, Any]:
    """Extract model-specific embedding attributes.

    Args:
        model: The model name used
        response: Response object

    Returns:
        Dictionary of model-specific attributes
    """
    attributes = {}

    model_lower = model.lower()

    # OpenAI embedding models
    if "text-embedding" in model_lower:
        if "ada" in model_lower:
            attributes["llm.embedding.model_family"] = "ada"
            attributes["llm.embedding.expected_dimension"] = 1536
        elif "3-small" in model_lower:
            attributes["llm.embedding.model_family"] = "v3-small"
            attributes["llm.embedding.expected_dimension"] = 1536
        elif "3-large" in model_lower:
            attributes["llm.embedding.model_family"] = "v3-large"
            attributes["llm.embedding.expected_dimension"] = 3072

    # Cohere embedding models
    elif "embed-" in model_lower:
        if "english" in model_lower:
            attributes["llm.embedding.model_family"] = "cohere-english"
            attributes["llm.embedding.expected_dimension"] = 4096
        elif "multilingual" in model_lower:
            attributes["llm.embedding.model_family"] = "cohere-multilingual"
            attributes["llm.embedding.expected_dimension"] = 768

    # Voyage embedding models
    elif "voyage-" in model_lower:
        attributes["llm.embedding.model_family"] = "voyage"
        if "large" in model_lower:
            attributes["llm.embedding.expected_dimension"] = 1536
        elif "code" in model_lower:
            attributes["llm.embedding.expected_dimension"] = 1536

    # Check if actual dimension matches expected
    if "llm.embedding.expected_dimension" in attributes:
        data = safe_get_attribute(response, "data")
        if data and isinstance(data, list) and data:
            embedding = safe_get_attribute(data[0], "embedding")
            if embedding and isinstance(embedding, list):
                actual_dim = len(embedding)
                expected_dim = attributes["llm.embedding.expected_dimension"]

                if actual_dim != expected_dim:
                    attributes["llm.embedding.dimension_mismatch"] = True
                    attributes["llm.embedding.actual_dimension"] = actual_dim

    return attributes


def extract_batch_embedding_attributes(input_data: List[Any], response: Any) -> Dict[str, Any]:
    """Extract attributes specific to batch embedding operations.

    Args:
        input_data: The batch input data
        response: Response object

    Returns:
        Dictionary of batch embedding attributes
    """
    attributes = {}

    # Batch size
    batch_size = len(input_data) if isinstance(input_data, list) else 1
    attributes["llm.batch.size"] = batch_size

    # Response data
    data = safe_get_attribute(response, "data")
    if data and isinstance(data, list):
        response_count = len(data)
        attributes["llm.batch.response_count"] = response_count

        # Check if all inputs got responses
        if response_count == batch_size:
            attributes["llm.batch.complete"] = True
        else:
            attributes["llm.batch.complete"] = False
            attributes["llm.batch.missing_count"] = batch_size - response_count

        # Check ordering
        if data:
            indices = []
            for item in data:
                index = safe_get_attribute(item, "index")
                if index is not None:
                    indices.append(index)

            if indices:
                # Check if indices are sequential
                expected_indices = list(range(len(indices)))
                if indices == expected_indices:
                    attributes["llm.batch.ordered"] = True
                else:
                    attributes["llm.batch.ordered"] = False
                    attributes["llm.batch.out_of_order_count"] = sum(1 for i, idx in enumerate(indices) if i != idx)

    return attributes
