import pprint
from typing import Optional, Dict, Any, Union, List
import gc
import os

from ..log_config import logger
from ..event import VectorEvent, ErrorEvent, ActionEvent
from ..session import Session, get_current_session
from ..helpers import get_ISO_time
from agentops.llms.instrumented_provider import InstrumentedProvider
from ..singleton import singleton
from ..enums import EventType
from pinecone.grpc import PineconeGRPC

@singleton
class PineconeProvider(InstrumentedProvider):
    def __init__(self, client):
        super().__init__(client)
        self._provider_name = "Pinecone"
        self.original_methods = {}
        self.override()

    def handle_response(
        self, response: Any, kwargs: Dict, init_timestamp: str, session: Optional[Session] = None
    ) -> Any:
        """Handle responses for Pinecone operations"""
        operation_type = kwargs.get("operation_type", "unknown")
        
        # Create ActionEvent with operation details
        event = ActionEvent(
            init_timestamp=init_timestamp,
            action_type=operation_type,
            returns=self._format_response(response, operation_type)
        )
        
        # Add operation details
        operation_details = self._get_operation_details(operation_type, kwargs, response)
        if operation_details:
            event.params = operation_details
        
        if session:
            event.session_id = session.session_id
            if "event_counts" in session.__dict__:
                session.event_counts["vectors"] += 1
            if operation_type in [
                "upsert", "delete", "update", "create_index",
                "delete_index", "describe_index", "list_indexes"
            ]:
                session.event_counts["actions"] += 1
        
        self._safe_record(session, event)
        
        # For index operations that return a generator or response object
        if operation_type in ["create_index", "describe_index"]:
            try:
                if hasattr(response, '__iter__') and not isinstance(response, (dict, list, str)):
                    response_list = list(response)
                    if response_list:
                        return response_list[0]
                    return response
            except Exception as e:
                logger.error(f"Error processing index operation response: {e}")
                return response

        return response

    def _get_operation_details(self, operation_type: str, kwargs: Dict, response: Any) -> Dict:
        """Get detailed information about the operation"""
        details = {
            "operation": operation_type,
            "timestamp": get_ISO_time(),
            "namespace": kwargs.get("namespace", "default"),
            "operation_status": "success" if response is not None else "no_response"
        }
        try:
            if operation_type == "create_index":
                details.update({
                    "action_description": f"Creating index '{kwargs.get('name')}'",
                    "index_name": kwargs.get("name"),
                    "dimension": kwargs.get("dimension"),
                    "metric": kwargs.get("metric"),
                    "spec": kwargs.get("spec").__dict__ if hasattr(kwargs.get("spec"), '__dict__') else kwargs.get("spec")
                })
            elif operation_type == "delete_index":
                details.update({
                    "action_description": f"Deleting index '{kwargs.get('name')}'",
                    "index_name": kwargs.get("name")
                })
            elif operation_type == "upsert":
                vectors = kwargs.get("vectors", [])
                details.update({
                    "action_description": f"Upserting {len(vectors)} vectors",
                    "vector_count": len(vectors),
                    "vector_ids": [v.get("id") for v in vectors],
                    "has_metadata": any("metadata" in v for v in vectors),
                    "has_sparse_values": any("sparse_values" in v for v in vectors),
                    "sample_vector": vectors[0] if vectors else None,
                    "dimension": len(vectors[0].get("values", [])) if vectors else None,
                    "metadata_fields": list(vectors[0].get("metadata", {}).keys()) if vectors and "metadata" in vectors[0] else []
                })
            elif operation_type == "query":
                details.update({
                    "action_description": f"Querying with top_k={kwargs.get('top_k', 0)}",
                    "query_vector": kwargs.get("vector"),
                    "top_k": kwargs.get("top_k"),
                    "filter": kwargs.get("filter"),
                    "include_values": kwargs.get("include_values", False),
                    "include_metadata": kwargs.get("include_metadata", False),
                    "matches_found": len(response.get("matches", [])) if response else 0,
                    "match_scores": [m.get("score") for m in response.get("matches", [])] if response else []
                })
            elif operation_type == "delete":
                details.update({
                    "action_description": "Deleting vectors",
                    "filter": kwargs.get("filter"),
                    "ids": kwargs.get("ids", []),
                    "delete_all": kwargs.get("delete_all", False)
                })
            elif operation_type == "fetch":
                vectors = response.vectors if hasattr(response, 'vectors') else {}
                details.update({
                    "action_description": f"Fetching {len(kwargs.get('ids', []))} vectors",
                    "ids": kwargs.get("ids", []),
                    "vectors_found": len(vectors)
                })
            elif operation_type == "update":
                details.update({
                    "action_description": f"Updating vector {kwargs.get('id')}",
                    "vector_id": kwargs.get("id"),
                    "values": kwargs.get("values"),
                    "sparse_values": kwargs.get("sparse_values"),
                    "set_metadata": kwargs.get("set_metadata")
                })
            elif operation_type == "describe_index_stats":
                if response:
                    details.update({
                        "action_description": "Getting index statistics",
                        "dimension": response.get("dimension"),
                        "total_vector_count": response.get("total_vector_count"),
                        "namespaces": response.get("namespaces", {})
                    })
            elif operation_type == "list_indexes":
                details.update({
                    "action_description": "Listing all indexes",
                    "index_count": len(response.get("indexes", [])) if response else 0,
                    "index_names": [idx.get("name") for idx in response.get("indexes", [])] if response else [],
                    "index_statuses": [idx.get("status", {}).get("state") for idx in response.get("indexes", [])] if response else []
                })
            elif operation_type in ["create_index", "describe_index", "configure_index"]:
                details.update({
                    "action_description": f"{operation_type.replace('_', ' ').title()}",
                    "index_name": kwargs.get("name"),
                    "dimension": kwargs.get("dimension"),
                    "metric": kwargs.get("metric"),
                    "pods": kwargs.get("pods"),
                    "replicas": kwargs.get("replicas"),
                    "pod_type": kwargs.get("pod_type")
                })
            elif operation_type == "list":
                vector_ids = list(response) if hasattr(response, '__iter__') else []
                details.update({
                    "action_description": "Listing vector IDs",
                    "prefix": kwargs.get("prefix"),
                    "limit": kwargs.get("limit"),
                    "vector_ids": vector_ids
                })
            elif operation_type == "start_import":
                details.update({
                    "action_description": "Starting vector import",
                    "source_file": kwargs.get("source"),
                    "namespace": kwargs.get("namespace"),
                    "import_id": response.get("import_id") if response else None
                })
            elif operation_type == "list_imports":
                details.update({
                    "action_description": "Listing imports",
                    "imports": response.get("imports", []) if response else []
                })
            elif operation_type == "describe_import":
                details.update({
                    "action_description": f"Describing import {kwargs.get('import_id')}",
                    "import_id": kwargs.get("import_id"),
                    "status": response.get("status") if response else None
                })
            elif operation_type == "cancel_import":
                details.update({
                    "action_description": f"Canceling import {kwargs.get('import_id')}",
                    "import_id": kwargs.get("import_id")
                })
            elif operation_type == "embed_data":
                details.update({
                    "action_description": "Embedding data",
                    "model": kwargs.get("model"),
                    "input_count": len(kwargs.get("input", [])),
                    "dimension": len(response[0]) if response else None
                })
            elif operation_type == "rerank_documents":
                details.update({
                    "action_description": "Reranking documents",
                    "model": kwargs.get("model"),
                    "document_count": len(kwargs.get("documents", [])),
                    "query": kwargs.get("query")
                })
        except Exception as e:
            details["error"] = str(e)
            details["operation_status"] = "error_in_details"
        return details

    def _format_response(self, response: Any, operation_type: str) -> Dict:
        """Format response with context based on operation type"""
        try:
            if operation_type == "list":
                # Handle generator response
                vector_ids = list(response) if hasattr(response, '__iter__') else []
                formatted = {"vector_ids": vector_ids}
            elif isinstance(response, dict):
                formatted = response
            elif hasattr(response, 'to_dict'):
                formatted = response.to_dict()
            elif isinstance(response, (list, tuple)):
                formatted = {"items": [str(item) for item in response]}
            else:
                formatted = {"raw_response": str(response)}
            
            # Convert any integer keys to strings
            if isinstance(formatted, dict):
                formatted = {str(k): v for k, v in formatted.items()}
            
            formatted["operation_type"] = operation_type
            return formatted
        except Exception as e:
            return {
                "operation_type": operation_type,
                "error": str(e),
                "raw_response": str(response)
            }

    def override(self):
        """Override Pinecone's methods using module-level patching"""
        import pinecone
        from pinecone.grpc import PineconeGRPC
        
        # Skip if already patched
        if hasattr(pinecone.Index, '_is_patched'):
            return
        
        # Data plane operations
        index_methods = {
            'upsert': pinecone.Index.upsert,
            'query': pinecone.Index.query,
            'delete': pinecone.Index.delete,
            'update': pinecone.Index.update,
            'fetch': pinecone.Index.fetch,
            'list': pinecone.Index.list,
            'describe_index_stats': pinecone.Index.describe_index_stats,
        }
        
        # Control plane operations
        pinecone_methods = {
            'list_indexes': pinecone.Pinecone.list_indexes,
            'create_index': pinecone.Pinecone.create_index,
            'describe_index': pinecone.Pinecone.describe_index,
            'delete_index': pinecone.Pinecone.delete_index,
            'configure_index': pinecone.Pinecone.configure_index,
            'list_collections': pinecone.Pinecone.list_collections,
            'create_collection': pinecone.Pinecone.create_collection,
            'describe_collection': pinecone.Pinecone.describe_collection,
            'delete_collection': pinecone.Pinecone.delete_collection,
        }
        
        # Inference operations
        def wrapped_embed(pc_instance, model: str, inputs: List[str], **kwargs):
            """Wrapper for Pinecone's embed method"""
            init_timestamp = get_ISO_time()
            session = get_current_session()
            try:
                response = pc_instance.inference.embed(model=model, inputs=inputs, **kwargs)
                
                # Safely extract usage data
                usage_data = {}
                if hasattr(response, 'usage'):
                    usage = response.usage
                    if hasattr(usage, '_data_store'):
                        usage_data = {
                            'total_tokens': usage._data_store.get('total_tokens'),
                            '_check_type': usage._data_store.get('_check_type'),
                            '_spec_property_naming': usage._data_store.get('_spec_property_naming'),
                        }
                        # Only include received_data if it exists and is serializable
                        if 'received_data' in usage._data_store:
                            try:
                                usage_data['received_data'] = usage._data_store['received_data']
                            except:
                                usage_data['received_data'] = str(usage._data_store['received_data'])

                # Create a safe response dictionary
                response_data = {
                    "model": model,
                    "embedding_count": len(response.data) if hasattr(response, 'data') else 0,
                    "usage": usage_data
                }
                
                event = ActionEvent(
                    init_timestamp=init_timestamp,
                    action_type="embed",
                    returns=response_data,
                    params={
                        "model": model,
                        "input_count": len(inputs),
                        "parameters": kwargs
                    }
                )
                if session:
                    event.session_id = session.session_id
                    session.event_counts["actions"] += 1
                self._safe_record(session, event)
                return response
            except Exception as e:
                error_event = ErrorEvent(
                    trigger_event=ActionEvent(
                        init_timestamp=init_timestamp,
                        action_type="embed",
                        returns={"error": str(e)}
                    ),
                    exception=e,
                    details={"model": model, "input_count": len(inputs)}
                )
                if session:
                    error_event.trigger_event.session_id = session.session_id
                self._safe_record(session, error_event)
                raise

        def wrapped_rerank(pc_instance, model: str, query: str, documents: List[Dict], **kwargs):
            """Wrapper for Pinecone's rerank method"""
            init_timestamp = get_ISO_time()
            session = get_current_session()
            try:
                response = pc_instance.inference.rerank(model=model, query=query, documents=documents, **kwargs)
                
                # Safely extract top scores
                top_scores = []
                if hasattr(response, 'data'):
                    top_scores = [item.score for item in response.data[:3]] if response.data else []
                
                # Create a safe response dictionary with basic info
                response_data = {
                    "model": model,
                    "rerank_count": len(documents),
                    "top_scores": top_scores
                }
                
                # Only add usage if it contains data
                if hasattr(response, 'usage') and response.usage:
                    usage = response.usage
                    if hasattr(usage, '_data_store') and usage._data_store:
                        usage_data = {
                            k: v for k, v in usage._data_store.items()
                            if v is not None and k not in ['_configuration', '_visited_composed_classes']
                        }
                        if usage_data:  # Only add if there's actual data
                            response_data["usage"] = usage_data
                
                event = ActionEvent(
                    init_timestamp=init_timestamp,
                    action_type="rerank",
                    returns=response_data,
                    params={
                        "model": model,
                        "query": query,
                        "document_count": len(documents),
                        "parameters": kwargs
                    }
                )
                if session:
                    event.session_id = session.session_id
                    session.event_counts["actions"] += 1
                self._safe_record(session, event)
                return response
            except Exception as e:
                error_event = ErrorEvent(
                    trigger_event=ActionEvent(
                        init_timestamp=init_timestamp,
                        action_type="rerank",
                        returns={"error": str(e)}
                    ),
                    exception=e,
                    details={"model": model, "query": query, "document_count": len(documents)}
                )
                if session:
                    error_event.trigger_event.session_id = session.session_id
                self._safe_record(session, error_event)
                raise

        # Add inference methods to provider
        self.embed = wrapped_embed
        self.rerank = wrapped_rerank

        # Create patched method wrapper
        def make_patched(name, orig):
            def patched(*args, **kwargs):
                init_timestamp = get_ISO_time()
                session = get_current_session()
                event_kwargs = kwargs.copy()
                event_kwargs["operation_type"] = name
                
                try:
                    result = orig(*args, **kwargs)
                    return self.handle_response(result, event_kwargs, init_timestamp, session=session)
                except Exception as e:
                    # Create ActionEvent for the error
                    action_event = ActionEvent(
                        event_type=EventType.ACTION.value,
                        init_timestamp=init_timestamp,
                        action_type=name,
                        returns={"error": str(e)}
                    )
                    
                    # Extract error details
                    error_details = {
                        "operation_type": name,
                        "kwargs": str(kwargs)
                    }
                    
                    error_event = ErrorEvent(
                        trigger_event=action_event,
                        exception=e,
                        details=error_details
                    )
                    if session:
                        error_event.trigger_event.session_id = session.session_id
                    self._safe_record(session, error_event)
                    raise

            return patched

        # Store and patch all methods
        for method_name, method in index_methods.items():
            self.original_methods[f'Index.{method_name}'] = method
            setattr(pinecone.Index, method_name, make_patched(method_name, method))

        for method_name, method in pinecone_methods.items():
            self.original_methods[f'Pinecone.{method_name}'] = method
            setattr(pinecone.Pinecone, method_name, make_patched(method_name, method))

        # Mark as patched
        pinecone.Index._is_patched = True
        pinecone.Pinecone._is_patched = True

    def undo_override(self) -> None:
        """Restore original Pinecone methods"""
        import pinecone

        for method_name, original_method in self.original_methods.items():
            class_name, method = method_name.split('.')
            if class_name == 'Index':
                setattr(pinecone.Index, method, original_method)
            elif class_name == 'Pinecone':
                setattr(pinecone.Pinecone, method, original_method)

    def _safe_record(self, session: Optional[Session], event: Union[VectorEvent, ErrorEvent]) -> None:
        """Safely record events with duplicate handling"""
        try:
            if session is not None:
                max_retries = 3
                retry_count = 0
                while retry_count < max_retries:
                    try:
                        session.record(event)
                        break
                    except Exception as e:
                        if "duplicate key value" in str(e) and retry_count < max_retries - 1:
                            if hasattr(event, 'event_id'):
                                event.event_id = f"{event.event_id}_{retry_count}"
                            retry_count += 1
                            continue
                        logger.error(f"Failed to record event after {retry_count + 1} attempts: {e}")
                        break
        except Exception as e:
            logger.error(f"Failed to record event: {e}")
