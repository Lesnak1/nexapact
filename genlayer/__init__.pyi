from typing import Any, Callable, TypeVar, Generic

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')

def allow_storage(cls: T) -> T: ...

class Address(str):
    def __init__(self, val: str) -> None: ...

class u256(int):
    def __init__(self, val: int | str = 0) -> None: ...

class u32(int):
    def __init__(self, val: int | str = 0) -> None: ...

class TreeMap(dict, Generic[K, V]):
    pass

class NonDetModule:
    class web:
        @staticmethod
        def get(url: str) -> str: ...
    @staticmethod
    def exec_prompt(prompt: str) -> str: ...

class VMModule:
    class UserError(Exception): ...
    @staticmethod
    def run_nondet_unsafe(leader_fn: Callable[[], Any], validator_fn: Callable[[Any, Any], bool]) -> Any: ...

class MessageProxy:
    sender_address: Address
    value: u256

class PublicDecorator:
    class WriteDecorator:
        def __call__(self, fn: T) -> T: ...
        def payable(self, fn: T) -> T: ...
    class ViewDecorator:
        def __call__(self, fn: T) -> T: ...
    write: WriteDecorator
    view: ViewDecorator

class gl:
    class Contract: ...
    vm: VMModule
    nondet: NonDetModule
    message: MessageProxy
    current_address: Address
    public: PublicDecorator
    @staticmethod
    def emit_transfer(to: Address, amount: u256) -> None: ...

def emit_transfer(to: Address, amount: u256) -> None: ...
current_address: Address
