from dataclasses import asdict, dataclass, field


@dataclass
class FooBase:
    x: int = field(default=1)
    y: int = field(default=1)
    z: int = field(init=False)  # Define z as a field but don't include in __init__


class Foo(FooBase):
    @property
    def z(self) -> int:
        return 2


print(asdict(Foo()))  # {'x': 1, 'y': 1, 'z': 2}
