from dataclasses import replace

import pytest

from linguaforge.config import get_config
from linguaforge.runtime import Runtime, resolve_runtime


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_runtime_device_is_separate_from_requested_config(device):
    requested_config = get_config()

    runtime = Runtime(device=device)

    assert runtime.device == device
    assert requested_config.device == "auto"


@pytest.mark.parametrize("device", ["auto", "mps"])
def test_runtime_rejects_unresolved_or_unsupported_devices(device):
    with pytest.raises(ValueError, match="Runtime device must be 'cpu' or 'cuda'"):
        Runtime(device=device)


@pytest.mark.parametrize(
    ("requested_device", "cuda_available", "expected_device"),
    [
        ("cpu", False, "cpu"),
        ("cpu", True, "cpu"),
        ("auto", False, "cpu"),
        ("auto", True, "cuda"),
        ("cuda", True, "cuda"),
    ],
)
def test_resolve_runtime_preserves_requested_config(
    requested_device, cuda_available, expected_device
):
    config = replace(get_config(), device=requested_device)

    runtime = resolve_runtime(config, cuda_available=cuda_available)

    assert isinstance(runtime, Runtime)
    assert runtime.device == expected_device
    assert config.device == requested_device


def test_resolve_runtime_rejects_explicit_cuda_when_unavailable():
    config = replace(get_config(), device="cuda")

    with pytest.raises(RuntimeError, match="CUDA was requested but is not available"):
        resolve_runtime(config, cuda_available=False)


@pytest.mark.parametrize("device", ["mps", ""])
def test_resolve_runtime_rejects_unsupported_requested_device(device):
    config = replace(get_config(), device=device)

    with pytest.raises(ValueError, match="Unsupported configured device"):
        resolve_runtime(config, cuda_available=True)
