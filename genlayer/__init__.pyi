from typing import Any, Callable, TypeVar, Generic

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')

def allow_storage(cls: T) -> T: ...

class Address(str):
    def __init__(self, val: str) -> None: ...

class u256(int):
    def __init__(self, val: int | str = 0) -> None: ...
    def __add__(self, other: Any) -> 'u256': ...
    def __sub__(self, other: Any) -> 'u256': ...
    def __mul__(self, other: Any) -> 'u256': ...
    def __floordiv__(self, other: Any) -> 'u256': ...

class u32(int):
    def __init__(self, val: int | str = 0) -> None: ...
    def __add__(self, other: Any) -> 'u32': ...
    def __sub__(self, other: Any) -> 'u32': ...

class TreeMap(dict[K, V], Generic[K, V]):
    pass

class StorageModule:
    @staticmethod
    def allow(target: T) -> T: ...
    class TreeMap(dict[K, V], Generic[K, V]): ...

class ContractModule:
    class Contract: ...

class NonDetModule:
    class web:
        @staticmethod
        def get(url: str) -> str: ...
    @staticmethod
    def exec_prompt(prompt: str) -> str: ...

class VMModule:
    class UserError(Exception): ...
    @staticmethod
    def run_nondet_unsafe(leader_fn: Callable[[], Any], validator_fn: Callable[[Any], bool]) -> Any: ...

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

# Module-level definitions
Contract = ContractModule.Contract
storage = StorageModule
contract = ContractModule
vm: VMModule
nondet: NonDetModule
message: MessageProxy
public: PublicDecorator
current_address: Address

def emit_transfer(to: Address, amount: u256) -> None: ...

class gl:
    Contract = ContractModule.Contract
    storage = StorageModule
    contract = ContractModule
    vm: VMModule
    nondet: NonDetModule
    message: MessageProxy
    current_address: Address
    public: PublicDecorator
    @staticmethod
    def emit_transfer(to: Address, amount: u256) -> None: ...
