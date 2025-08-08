from typing import Any, Optional, TypeVar
from abc import abstractmethod
from dataclasses import dataclass

from jockey.backend import get_client


class classproperty:
    """Descriptor for class properties."""

    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        return self.func(owner)


T = TypeVar('T', bound='BaseModel')


class BaseModel:
    """Base model for Kubernetes resources.

    Supports both configuration-based models (ConfigMap, Secret, etc.)
    and data-wrapper models (Pod, Service from existing k8s objects).
    """

    @classproperty
    def client(cls):
        """Get the Kubernetes client instance."""
        return get_client()

    @classmethod
    def get(cls: type[T], name: str, namespace: str) -> Optional[T]:
        """Get a resource by name and namespace. Override in subclasses."""
        raise NotImplementedError(f"{cls.__name__} doesn't support get()")

    @classmethod
    def filter(cls: type[T], namespace: str, **kwargs) -> list[T]:
        """Filter resources in the namespace. Override in subclasses."""
        raise NotImplementedError(f"{cls.__name__} doesn't support filter()")


@dataclass
class KubernetesResourceWrapper(BaseModel):
    """Base class for models that wrap existing Kubernetes objects."""

    _data: Optional[Any] = None

    def __init__(self, data: Any) -> None:
        """Initialize model with k8s data."""
        self._data = data

    def __repr__(self) -> str:
        """String representation of the resource."""
        class_name = self.__class__.__name__
        return f"{class_name}(name='{self.name}', namespace='{self.namespace}')"

    @property
    def name(self) -> str:
        """Get the resource name from data."""
        return str(self.data.metadata.name)

    @property
    def namespace(self) -> str:
        """Get the resource namespace from data."""
        return str(self.data.metadata.namespace)

    @property
    def data(self) -> Any:
        """Get the underlying Kubernetes object data."""
        if self._data is None:
            raise RuntimeError(f"No data loaded for {self.__class__.__name__}")
        return self._data

    @classmethod
    @abstractmethod
    def create(cls: type[T], namespace: str, body: Any) -> T:
        """Create a new resource."""
        ...
