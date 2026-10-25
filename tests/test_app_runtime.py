import re
from pathlib import Path

import numpy as np
import pytest

onnx = pytest.importorskip("onnx")
ort = pytest.importorskip("onnxruntime")

from onnx import TensorProto, helper  # noqa: E402

from tools.app_runtime import APP_ORT, PLUGIN_ORT, fold_float64, problems  # noqa: E402

pytestmark = pytest.mark.onnx
ROOT = Path(__file__).resolve().parents[1]


def _model(path: Path, *, from_pixels: bool = False, dynamic: bool = False) -> Path:
    """pixel_values -> y = mean(pixels) + cos(float64(shape or pixels)) cast back to float32, like D-FINE's
    position embedding: a float64 part that depends on the input only through its shape."""
    dims = ["n", 3, 8, 8] if dynamic else [1, 3, 8, 8]
    x = helper.make_tensor_value_info("pixel_values", TensorProto.FLOAT, dims)
    y = helper.make_tensor_value_info("y", TensorProto.FLOAT, [4])
    nodes = [helper.make_node("ReduceMean", ["pixel_values"], ["m"], keepdims=0)]
    if from_pixels:
        nodes += [helper.make_node("Cast", ["pixel_values"], ["d"], to=TensorProto.DOUBLE)]
    else:
        nodes += [helper.make_node("Shape", ["pixel_values"], ["s"]),
                  helper.make_node("Cast", ["s"], ["d"], to=TensorProto.DOUBLE)]
    nodes += [helper.make_node("Cos", ["d"], ["c"]),
              helper.make_node("Cast", ["c"], ["f"], to=TensorProto.FLOAT),
              helper.make_node("Add", ["m", "f"], ["y"])]
    model = helper.make_model(helper.make_graph(nodes, "g", [x], [y]), opset_imports=[helper.make_opsetid("", 17)])
    model.ir_version = 8
    onnx.save(model, str(path))
    return path


def _run(path: Path, x: np.ndarray) -> np.ndarray:
    return ort.InferenceSession(str(path), providers=["CPUExecutionProvider"]).run(None, {"pixel_values": x})[0]


def test_fold_removes_float64_and_keeps_outputs(tmp_path):
    src = _model(tmp_path / "a.onnx")
    assert any("Cos" in p for p in problems(onnx.load(str(src))))
    dst = tmp_path / "b.onnx"
    assert fold_float64(src, dst)
    assert problems(onnx.load(str(dst))) == []
    for seed in range(3):
        x = np.random.default_rng(seed).random((1, 3, 8, 8), dtype=np.float32)
        np.testing.assert_array_equal(_run(src, x), _run(dst, x))


def test_fold_leaves_a_float32_model_unchanged(tmp_path):
    src = tmp_path / "a.onnx"
    x = helper.make_tensor_value_info("pixel_values", TensorProto.FLOAT, [1, 3, 8, 8])
    y = helper.make_tensor_value_info("y", TensorProto.FLOAT, [1, 3, 8, 8])
    model = helper.make_model(helper.make_graph([helper.make_node("Relu", ["pixel_values"], ["y"])], "g", [x], [y]),
                              opset_imports=[helper.make_opsetid("", 17)])
    onnx.save(model, str(src))
    assert fold_float64(src, tmp_path / "b.onnx") == []
    assert problems(onnx.load(str(tmp_path / "b.onnx"))) == []


def test_fold_refuses_float64_that_reads_pixels(tmp_path):
    with pytest.raises(ValueError, match="pixel values"):
        fold_float64(_model(tmp_path / "a.onnx", from_pixels=True), tmp_path / "b.onnx")


def test_fold_refuses_a_dynamic_input(tmp_path):
    with pytest.raises(ValueError, match="dynamic shape"):
        fold_float64(_model(tmp_path / "a.onnx", dynamic=True), tmp_path / "b.onnx")


def test_app_runtime_table_covers_the_locked_plugin():
    """APP_ORT must describe the flutter_onnxruntime the app actually locks; a plugin bump needs a new row."""
    lock = (ROOT / "app" / "pubspec.lock").read_text(encoding="utf-8")
    m = re.search(r'flutter_onnxruntime:\n(?:\s+.*\n)*?\s+version: "([^"]+)"', lock)
    assert m, "flutter_onnxruntime not found in app/pubspec.lock"
    assert m.group(1) in PLUGIN_ORT, f"add flutter_onnxruntime {m.group(1)} to tools/app_runtime.PLUGIN_ORT"
    assert PLUGIN_ORT[m.group(1)] == APP_ORT
