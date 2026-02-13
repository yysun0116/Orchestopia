from typing import Dict, Generic, TypeVar

T = TypeVar("T")

class BaseRegistry(Generic[T]):
    def __init__(self):
        self._items: Dict[str, T] = {}

    def register(self, name: str, item: T) -> None:
        if name in self._items:
            raise ValueError(f"{name} already registered")
        self._items[name] = item

    def get(self, name: str) -> T:
        if name in self._items:
            return self._items[name]
        else:
            print(f"There is no `{name}` instance in the registry")

    def all(self) -> Dict[str, T]: # internal use only
        return self._items
    
    def snapshot(self) -> Dict[str, T]:
        return dict(self._items)

    def cleanup(self) -> None:
        self._items.clear()

    def delete(self, name: str) -> None:
        del self._items[name]

    