from typing import Any, Callable, Optional, Union, TypeVar
from dataclasses import dataclass
from fastapi import APIRouter, Request
from abc import ABC, abstractmethod
import inspect


__all__ = ["RouteConfig", "BaseView", "register_routes", "reverse_path"]

_path_registry: dict[str, str] = {}


class BaseView(ABC):
    """
    Abstract base class for views in the route configuration.
    This class must be extended to create specific views.
    """

    request: Request

    def __init__(self, request: Request):
        self.request = request

    @classmethod
    async def create(cls, **kwargs) -> 'BaseView':
        """
        This method is called when the view is instantiated.
        It can be overridden to perform any setup required for the view.
        """
        return cls(**kwargs)

    @abstractmethod
    async def __call__(self, *args, **kwargs):
        """This method is called when the view is invoked."""
        ...


TBaseView = TypeVar('TBaseView', bound=BaseView)


def _apply_view_docs(wrapper: Callable, view_class: type[TBaseView]) -> None:
    """Applies documentation-related attributes to the wrapper function from a class based view."""
    call_method = getattr(view_class, '__call__')
    call_sig = inspect.signature(call_method)

    params = []
    has_request_param = any(name == 'request' for name in call_sig.parameters.keys())

    for name, param in call_sig.parameters.items():
        if name == 'self':
            # Only replace 'self' with 'request: Request' if there's no existing 'request' parameter
            if not has_request_param:
                param = inspect.Parameter(
                    'request',
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=Request,
                )
            else:
                # Skip 'self' parameter if there's already a 'request' parameter
                continue
        params.append(param)

    wrapper.__doc__ = view_class.__doc__  # use the view class docstring
    wrapper.__name__ = view_class.__dict__.get('__name__', view_class.__name__)
    wrapper.__signature__ = inspect.Signature(
        parameters=params,
        return_annotation=call_sig.return_annotation,
    )


@dataclass
class RouteConfig:
    """
    Route configuration for a FastAPI route.

    Usage with function endpoints:
    ```python
    from fastapi import APIRouter
    from agentops.common.route_config import RouteConfig, register_routes

    route_config: list[RouteConfig] = [
        RouteConfig(
            name="example_route",
            path="/example",
            endpoint=example_endpoint,
            methods=["GET"],
        ),
    ]
    router = APIRouter(prefix="/api")
    register_routes(router, route_config)

    # use the router like you would normally
    app.include_router(router)

    # this allows us to reverse paths by name
    from agentops.common.route_config import reverse_path
    path = reverse_path("example_route")
    >> "/api/example"
    ```

    Usage with class-based views:
    ```python
    from agentops.common.route_config import BaseView, RouteConfig

    class ExampleView(BaseView):
        __name__ = "Get Example Data"

        async def __call__(self, item_id: int) -> dict:
            return {"id": item_id, "data": "example"}

    route_config: list[RouteConfig] = [
        RouteConfig(
            name="example_view",
            path="/example/{item_id}",
            endpoint=ExampleView,
            methods=["GET"],
        ),
    ]
    ```
    """

    name: str
    path: str
    endpoint: Union[Callable, type[TBaseView]]
    methods: list[str]
    summary: Optional[str] = None
    description: Optional[str] = None
    deprecated: Optional[bool] = None

    @property
    def kwargs(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "description": self.description,
            "deprecated": self.deprecated,
        }

    def _create_class_view(self, view_class: type[TBaseView]) -> Callable:
        async def wrapper(request: Request, **kwargs):
            view_instance = await view_class.create(request=request)

            # filter kwargs to only include parameters that the __call__ method expects
            call_method = getattr(view_instance, '__call__')
            sig = inspect.signature(call_method)
            filtered_kwargs = {}
            for param_name, param in sig.parameters.items():
                if param_name in kwargs:
                    filtered_kwargs[param_name] = kwargs[param_name]

            return await view_instance(**filtered_kwargs)

        _apply_view_docs(wrapper, view_class)

        # copy is_public attribute from class __call__ method to wrapper for AuthenticatedRoute middleware
        # TODO this is a bit too couple with agentops.auth for my taste, but we can fix that later.
        if hasattr(view_class.__call__, 'is_public'):
            wrapper.is_public = view_class.__call__.is_public

        return wrapper

    def as_view(self) -> Callable:
        """
        Returns the appropriate callable for this route.
        If endpoint is a class-based view, wraps it with request injection.
        If endpoint is a function, returns it as-is.
        """
        if not inspect.isclass(self.endpoint):
            return self.endpoint

        if issubclass(self.endpoint, BaseView):
            return self._create_class_view(self.endpoint)

        raise TypeError(f"`endpoint` {self.endpoint.__name__} must be a function or inherit from BaseView")


def reverse_path(route_name: str) -> Optional[str]:
    """
    Reverse a path by name.
    Args:
        route_name (str): The name of the route to reverse (from `RouteConfig.name`)
    """
    global _path_registry

    return _path_registry.get(route_name, None)


def register_routes(router: APIRouter, configs: list[RouteConfig], prefix: str = "") -> None:
    """
    Registers a list of route configurations with a FastAPI router, applying an optional prefix.

    Args:
        router (APIRouter): The FastAPI router to register the routes with.
        configs (list[RouteConfig]): A list of RouteConfig objects defining the routes to register.
        prefix (str): An optional prefix to prepend to the route paths. This is in addition to
            any prefix already defined on the router itself and is used when adding an app
            to a parent app with `app.mount()` (since we are not able to determine the prefix
            of the parent app at runtime).
    """
    global _path_registry

    for config in configs:
        _path_registry[config.name] = f"{prefix}{router.prefix}{config.path}"

        for method in config.methods:
            router.add_api_route(
                path=config.path,
                endpoint=config.as_view(),
                methods=[method],
                **config.kwargs,
            )
