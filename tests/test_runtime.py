import pytest

from linguaforge.config import get_config
from linguaforge.runtime import Runtime


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
