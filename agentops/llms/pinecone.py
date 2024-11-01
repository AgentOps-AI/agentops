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

    def _handle_assistant_response(
        self, response: Any, operation_type: str, kwargs: Dict, init_timestamp: str, session: Optional[Session] = None
    ) -> Any:
        """Handle responses for Pinecone Assistant operations"""
        try:
            # If response is an error dictionary, raise it as an exception
            if isinstance(response, dict) and "error" in response:
                raise Exception(response["error"])

            # Create response data based on operation type
            response_data = {
                "operation_type": operation_type,
                "timestamp": get_ISO_time()
            }
            
            # Add operation-specific data
            if operation_type == "create_assistant":
                response_data.update({
                    "assistant_name": response.get("name"),
                    "status": response.get("status"),
                    "created_at": response.get("created_at")
                })
            elif operation_type == "chat":
                response_data.update({
                    "model": response.get("model"),
                    "usage": response.get("usage"),
                    "citations": response.get("citations")
                })
            elif operation_type == "upload_file":
                response_data.update({
                    "file_id": response.get("id"),
                    "file_name": response.get("name"),
                    "status": response.get("status"),
                    "percent_done": response.get("percent_done")
                })
            
            # Create ActionEvent
            event = ActionEvent(
                init_timestamp=init_timestamp,
                action_type=operation_type,
                returns=response_data,
                params=kwargs
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
                    action_type=operation_type,
                    returns={"error": str(e)}
                ),
                exception=e,
                details=kwargs
            )
            if session:
                error_event.trigger_event.session_id = session.session_id
            self._safe_record(session, error_event)
            raise

    def create_assistant(self, pc_instance, assistant_name: str, instructions: Optional[str] = None,
                        metadata: Optional[Dict] = {}, timeout: int = 30) -> Any:
        """Create a new Pinecone Assistant"""
        init_timestamp = get_ISO_time()
        session = get_current_session()
        kwargs = {
            "assistant_name": assistant_name,
            "instructions": instructions,
            "metadata": metadata or {},
            "timeout": timeout
        }
        try:
            response = pc_instance.assistant.create_assistant(**kwargs)
            return self._handle_assistant_response(response, "create_assistant", kwargs, init_timestamp, session)
        except Exception as e:
            error_event = ErrorEvent(
                trigger_event=ActionEvent(
                    init_timestamp=init_timestamp,
                    action_type="create_assistant",
                    returns={"error": str(e)}
                ),
                exception=e,
                details=kwargs
            )
            if session:
                error_event.trigger_event.session_id = session.session_id
            self._safe_record(session, error_event)
            raise

    def list_assistants(self, pc_instance) -> Any:
        """List all assistants"""
        init_timestamp = get_ISO_time()
        session = get_current_session()
        try:
            response = pc_instance.assistant.list_assistants()
            return self._handle_assistant_response(response, "list_assistants", {}, init_timestamp, session)
        except Exception as e:
            error_event = ErrorEvent(
                trigger_event=ActionEvent(
                    init_timestamp=init_timestamp,
                    action_type="list_assistants",
                    returns={"error": str(e)}
                ),
                exception=e,
                details={}
            )
            if session:
                error_event.trigger_event.session_id = session.session_id
            self._safe_record(session, error_event)
            raise

    def get_assistant(self, pc_instance, assistant_name: str) -> Any:
        """Get assistant status"""
        init_timestamp = get_ISO_time()
        session = get_current_session()
        kwargs = {"assistant_name": assistant_name}
        try:
            # Create an Assistant instance and get its status
            assistant = pc_instance.assistant.Assistant(assistant_name=assistant_name)
            response = assistant.get(name=assistant_name)
            return self._handle_assistant_response(response, "get_assistant", kwargs, init_timestamp, session)
        except Exception as e:
            error_event = ErrorEvent(
                trigger_event=ActionEvent(
                    init_timestamp=init_timestamp,
                    action_type="get_assistant",
                    returns={"error": str(e)}
                ),
                exception=e,
                details=kwargs
            )
            if session:
                error_event.trigger_event.session_id = session.session_id
            self._safe_record(session, error_event)
            raise

    def update_assistant(self, pc_instance, assistant_name: str, instructions: Optional[str] = None,
                        metadata: Optional[Dict] = None) -> Any:
        """Update an existing assistant"""
        init_timestamp = get_ISO_time()
        session = get_current_session()
        kwargs = {
            "assistant_name": assistant_name,
            "instructions": instructions,
            "metadata": metadata
        }
        try:
            response = pc_instance.assistant.update_assistant(**kwargs)
            return self._handle_assistant_response(response, "update_assistant", kwargs, init_timestamp, session)
        except Exception as e:
            raise self._handle_assistant_response({"error": str(e)}, "update_assistant", kwargs, init_timestamp, session)

    def delete_assistant(self, pc_instance, assistant_name: str) -> Any:
        """Delete an assistant"""
        init_timestamp = get_ISO_time()
        session = get_current_session()
        kwargs = {"assistant_name": assistant_name}
        try:
            response = pc_instance.assistant.delete_assistant(assistant_name)
            return self._handle_assistant_response(response, "delete_assistant", kwargs, init_timestamp, session)
        except Exception as e:
            raise self._handle_assistant_response({"error": str(e)}, "delete_assistant", kwargs, init_timestamp, session)

    def chat_with_assistant(self, pc_instance, assistant_name: str, messages: List[Dict],
                           stream: bool = False, model: Optional[str] = None) -> Any:
        """Chat with an assistant"""
        init_timestamp = get_ISO_time()
        session = get_current_session()
        try:
            # Import the Message class
            from pinecone_plugins.assistant.models.chat import Message
            
            # Convert dict messages to Message objects
            message_objects = [Message(content=msg["content"]) for msg in messages]
            
            # Create kwargs for event tracking
            kwargs = {
                "assistant_name": assistant_name,
                "messages": messages,
                "stream": stream,
                "model": model
            }
            
            # Get assistant and chat
            assistant = pc_instance.assistant.Assistant(assistant_name=assistant_name)
            response = assistant.chat(messages=message_objects, stream=stream, model=model)
            return self._handle_assistant_response(response, "chat", kwargs, init_timestamp, session)
        except Exception as e:
            error_event = ErrorEvent(
                trigger_event=ActionEvent(
                    init_timestamp=init_timestamp,
                    action_type="chat",
                    returns={"error": str(e)}
                ),
                exception=e,
                details=kwargs
            )
            if session:
                error_event.trigger_event.session_id = session.session_id
            self._safe_record(session, error_event)
            raise

    def upload_file(self, pc_instance, assistant_name: str, file_path: str, 
                    metadata: Optional[Dict] = None, timeout: Optional[int] = None) -> Any:
        """Upload a file to an assistant"""
        init_timestamp = get_ISO_time()
        session = get_current_session()
        kwargs = {
            "assistant_name": assistant_name,
            "file_path": file_path,
            "metadata": metadata,
            "timeout": timeout
        }
        try:
            # Create an Assistant instance first
            assistant = pc_instance.assistant.Assistant(assistant_name=assistant_name)
            
            # Upload file using the file_path directly
            response = assistant.upload_file(file_path=file_path, timeout=timeout)
            
            # Convert FileModel to dictionary
            if hasattr(response, '__dict__'):
                response = {
                    "id": getattr(response, 'id', None),
                    "name": getattr(response, 'name', None),
                    "metadata": getattr(response, 'metadata', None),
                    "created_on": getattr(response, 'created_on', None),
                    "updated_on": getattr(response, 'updated_on', None),
                    "status": getattr(response, 'status', None),
                    "percent_done": getattr(response, 'percent_done', None),
                    "signed_url": getattr(response, 'signed_url', None)
                }
            
            return self._handle_assistant_response(response, "upload_file", kwargs, init_timestamp, session)
        except Exception as e:
            error_event = ErrorEvent(
                trigger_event=ActionEvent(
                    init_timestamp=init_timestamp,
                    action_type="upload_file",
                    returns={"error": str(e)}
                ),
                exception=e,
                details=kwargs
            )
            if session:
                error_event.trigger_event.session_id = session.session_id
            self._safe_record(session, error_event)
            raise

    def describe_file(self, pc_instance, assistant_name: str, file_id: str) -> Any:
        """Get details about an uploaded file"""
        init_timestamp = get_ISO_time()
        session = get_current_session()
        kwargs = {
            "assistant_name": assistant_name,
            "file_id": file_id
        }
        try:
            # Create an Assistant instance first
            assistant = pc_instance.assistant.Assistant(assistant_name=assistant_name)
            
            # Get file details
            response = assistant.describe_file(file_id=file_id)
            
            # Convert response to dict if it's not already
            if hasattr(response, '__dict__'):
                response = response.__dict__
            
            # Create a safe response dictionary
            formatted_response = {
                "name": response.get("name"),
                "id": response.get("id"),
                "metadata": response.get("metadata"),
                "created_on": response.get("created_on"),
                "updated_on": response.get("updated_on"),
                "status": response.get("status"),
                "percent_done": response.get("percent_done"),
                "signed_url": response.get("signed_url")
            }
            
            return self._handle_assistant_response(formatted_response, "describe_file", kwargs, init_timestamp, session)
        except Exception as e:
            error_event = ErrorEvent(
                trigger_event=ActionEvent(
                    init_timestamp=init_timestamp,
                    action_type="describe_file",
                    returns={"error": str(e)}
                ),
                exception=e,
                details=kwargs
            )
            if session:
                error_event.trigger_event.session_id = session.session_id
            self._safe_record(session, error_event)
            raise

    def delete_file(self, pc_instance, assistant_name: str, file_id: str) -> Any:
        """Delete an uploaded file from an assistant"""
        init_timestamp = get_ISO_time()
        session = get_current_session()
        kwargs = {
            "assistant_name": assistant_name,
            "file_id": file_id
        }
        try:
            # Create an Assistant instance first
            assistant = pc_instance.assistant.Assistant(assistant_name=assistant_name)
            
            # Delete the file
            response = assistant.delete_file(file_id=file_id)
            return self._handle_assistant_response(response, "delete_file", kwargs, init_timestamp, session)
        except Exception as e:
            error_event = ErrorEvent(
                trigger_event=ActionEvent(
                    init_timestamp=init_timestamp,
                    action_type="delete_file",
                    returns={"error": str(e)}
                ),
                exception=e,
                details=kwargs
            )
            if session:
                error_event.trigger_event.session_id = session.session_id
            self._safe_record(session, error_event)
            raise

    def chat_completions(self, pc_instance, assistant_name: str, messages: List[Dict],
                        stream: bool = False, model: Optional[str] = None) -> Any:
        """Chat with an assistant using OpenAI-compatible interface"""
        init_timestamp = get_ISO_time()
        session = get_current_session()
        
        try:
            # Import the Message class
            from pinecone_plugins.assistant.models.chat import Message
            
            # Convert dict messages to Message objects
            message_objects = [Message(content=msg["content"]) for msg in messages]
            
            # Create kwargs for event tracking
            kwargs = {
                "assistant_name": assistant_name,
                "messages": messages,
                "stream": stream,
                "model": model
            }
            
            # Get assistant and use chat_completions
            assistant = pc_instance.assistant.Assistant(assistant_name=assistant_name)
            response = assistant.chat_completions(messages=message_objects, stream=stream, model=model)
            
            # Format response for OpenAI compatibility
            formatted_response = {
                "id": response.get("id"),
                "choices": [{
                    "finish_reason": response.get("finish_reason", "stop"),
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response.get("message", {}).get("content", "")
                    }
                }],
                "model": response.get("model"),
                "usage": response.get("usage", {})
            }
            
            return self._handle_assistant_response(formatted_response, "chat_completions", kwargs, init_timestamp, session)
        except Exception as e:
            error_event = ErrorEvent(
                trigger_event=ActionEvent(
                    init_timestamp=init_timestamp,
                    action_type="chat_completions",
                    returns={"error": str(e)}
                ),
                exception=e,
                details=kwargs
            )
            if session:
                error_event.trigger_event.session_id = session.session_id
            self._safe_record(session, error_event)
            raise
