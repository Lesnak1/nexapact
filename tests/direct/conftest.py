import json
import re
import pytest


class UserError(Exception):
    pass


class RevertExpectationContext:
    def __init__(self, expected_msg=""):
        self.expected_msg = expected_msg

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            raise AssertionError(f"Expected revert with '{self.expected_msg}', but call succeeded.")
        err_str = str(exc_val)
        if self.expected_msg and self.expected_msg not in err_str:
            raise AssertionError(
                f"Expected revert containing '{self.expected_msg}', but got: {err_str}"
            )
        return True


class MockDirectVM:
    def __init__(self):
        self.sender = "0x70997970c51812dc3a010c7d01b50e0d17dc79c8"
        self.value = 0
        self.block_timestamp = 1770000000
        self.web_mocks = []
        self.llm_mocks = []
        self.llm_queue = []

    def mock_web(self, pattern: str, response: str):
        self.web_mocks.append((re.compile(pattern), response))

    def mock_llm(self, pattern: str, response: str):
        self.llm_mocks.append((re.compile(pattern), response))

    def queue_llm_response(self, response: str):
        self.llm_queue.append(response)

    def get_web(self, url: str):
        for pat, resp in reversed(self.web_mocks):
            if pat.search(url):
                return resp
        # Default mock response
        return "MOCK EVIDENCE: Pull Request #42 merged with 100% tests passing."

    def exec_prompt(self, prompt: str):
        if self.llm_queue:
            return self.llm_queue.pop(0)
        for pat, resp in reversed(self.llm_mocks):
            if pat.search(prompt):
                return resp
        # Default passing evaluation
        return json.dumps({
            "functional": 90,
            "criteria": 92,
            "quality": 88,
            "defect_severity": "NONE",
            "summary": "All acceptance criteria verified with high quality."
        })

    def expect_revert(self, expected_msg=""):
        return RevertExpectationContext(expected_msg)


@pytest.fixture
def direct_vm():
    return MockDirectVM()


@pytest.fixture
def direct_alice():
    return "0x70997970c51812dc3a010c7d01b50e0d17dc79c8"


@pytest.fixture
def direct_bob():
    return "0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc"


@pytest.fixture
def direct_deploy(direct_vm):
    def _deploy(contract_path: str):
        import importlib.util
        import sys
        import types

        mock_gl = types.ModuleType("genlayer")

        class Address(str):
            def __new__(cls, val):
                return super().__new__(cls, str(val).lower())

        class u256(int):
            pass

        class u32(int):
            pass

        class TreeMap(dict):
            pass

        def allow_storage(cls):
            return cls

        class VMModule:
            UserError = UserError

            @staticmethod
            def run_nondet_unsafe(leader_fn, validator_fn):
                lead_res = leader_fn()
                # Real GenVM invokes validator_fn with a single leader result argument.
                # validator_fn independently re-runs the pipeline and performs equivalence check.
                if not validator_fn(lead_res):
                    raise UserError("Validator equivalence check failed.")
                return lead_res

        class NonDetModule:
            class web:
                @staticmethod
                def get(url):
                    return direct_vm.get_web(url)

            @staticmethod
            def exec_prompt(prompt):
                return direct_vm.exec_prompt(prompt)

        class MessageProxy:
            @property
            def sender_address(self):
                return Address(direct_vm.sender)

            @sender_address.setter
            def sender_address(self, val):
                direct_vm.sender = val

            @property
            def value(self):
                return u256(direct_vm.value)

            @value.setter
            def value(self, val):
                direct_vm.value = val

        class PublicDecorator:
            class WriteDecorator:
                def __call__(self, fn):
                    return fn

                def payable(self, fn):
                    return fn

            class ViewDecorator:
                def __call__(self, fn):
                    return fn

            write = WriteDecorator()
            view = ViewDecorator()

        class StorageModule:
            allow = staticmethod(lambda fn: fn)

        StorageModule.TreeMap = TreeMap

        class ContractModule:
            Contract = object

        mock_gl.Address = Address
        mock_gl.u256 = u256
        mock_gl.u32 = u32
        mock_gl.TreeMap = TreeMap
        mock_gl.allow_storage = allow_storage
        mock_gl.Contract = object
        mock_gl.storage = StorageModule
        mock_gl.contract = ContractModule
        mock_gl.public = PublicDecorator()
        mock_gl.vm = VMModule()
        mock_gl.nondet = NonDetModule()
        mock_gl.message = MessageProxy()
        mock_gl.current_address = Address("0x0000000000000000000000000000000000000001")
        mock_gl.emit_transfer = lambda to_addr, amount: None
        mock_gl.gl = mock_gl

        sys.modules["genlayer"] = mock_gl

        spec = importlib.util.spec_from_file_location("contract_mod", contract_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        instance = mod.NexaPact()
        instance.agreements = {}
        instance.milestones = {}
        instance.agents = {}
        return instance

    return _deploy
