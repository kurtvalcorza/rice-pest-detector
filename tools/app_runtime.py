"""Keep exported ONNX models loadable by the app's ONNX Runtime.

The Android app runs models on the ONNX Runtime that flutter_onnxruntime bundles (APP_ORT below), not on the
runtime this repository tests with. 1.28 has no float64 kernels for several ops (Cos and Sin among them), so a
graph that computes anything in float64 fails to open on the phone even though it runs here. D-FINE-L's export
did exactly that: its encoder position embedding is computed in float64 (2026-10-25).

At the app's fixed input size such float64 parts depend on the input only through its shape, so they are
constants. fold_float64 computes them once and stores the results as initializers; nothing else changes.

Run: python -m tools.app_runtime check models/x.onnx
     python -m tools.app_runtime fold models/x.onnx models/x-app.onnx
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import onnx
from onnx import helper, numpy_helper

# flutter_onnxruntime version (app/pubspec.lock) -> the onnxruntime-android it bundles (its android/build.gradle).
# A plugin upgrade must add its row here; tests/test_app_runtime.py fails until it does.
PLUGIN_ORT = {"1.9.0": "1.28.0"}
APP_ORT = PLUGIN_ORT["1.9.0"]

DOUBLE = onnx.TensorProto.DOUBLE


def _dtypes(model: onnx.ModelProto) -> dict[str, int]:
    g = onnx.shape_inference.infer_shapes(model).graph
    types = {v.name: v.type.tensor_type.elem_type for v in list(g.value_info) + list(g.input) + list(g.output)}
    types.update({t.name: t.data_type for t in g.initializer})
    return types


def problems(model: onnx.ModelProto) -> list[str]:
    """Reasons the app's runtime would refuse the model; empty when it fits."""
    types = _dtypes(model)
    found = []
    for n in model.graph.node:
        if any(types.get(t) == DOUBLE for t in list(n.input) + list(n.output)):
            found.append(f"{n.op_type} node {n.name!r} uses float64")
    found += [f"initializer {t.name!r} is float64" for t in model.graph.initializer if t.data_type == DOUBLE]
    return found


def _boundary(model: onnx.ModelProto) -> list[str]:
    """Tensors where the float64 region ends: produced by a node that reads float64 but writes none."""
    types = _dtypes(model)
    return [o for n in model.graph.node
            if any(types.get(i) == DOUBLE for i in n.input) and all(types.get(o) != DOUBLE for o in n.output)
            for o in n.output]


def _check_constant(model: onnx.ModelProto, names: list[str]) -> None:
    """Each tensor must reach the graph input only through a Shape node, and the input shape must be fixed."""
    g = model.graph
    inputs = {i.name: i for i in g.input}
    for i in inputs.values():
        dims = i.type.tensor_type.shape.dim
        if any(not d.HasField("dim_value") for d in dims):
            raise ValueError(f"input {i.name!r} has a dynamic shape; float64 parts are not constants")
    producer = {o: n for n in g.node for o in n.output}
    seen: set[str] = set()
    stack = list(names)
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        if name in inputs:
            raise ValueError(f"float64 part reads the pixel values of {name!r}; it is not a constant")
        node = producer.get(name)
        if node is not None and node.op_type != "Shape":
            stack.extend(i for i in node.input if i)


def fold_float64(src: Path, dst: Path) -> list[str]:
    """Replace the model's float64 parts by their constant results. Returns the folded tensor names."""
    import onnxruntime as ort

    model = onnx.load(str(src))
    names = _boundary(model)
    if not names:
        onnx.save(model, str(dst))
        return []
    _check_constant(model, names)

    types = _dtypes(model)
    probe = onnx.load(str(src))
    probe.graph.output.extend(helper.make_tensor_value_info(n, types[n], None) for n in names)
    sess = ort.InferenceSession(probe.SerializeToString(), providers=["CPUExecutionProvider"])
    feeds = {}
    for i in model.graph.input:
        shape = [d.dim_value for d in i.type.tensor_type.shape.dim]
        feeds[i.name] = np.zeros(shape, helper.tensor_dtype_to_np_dtype(i.type.tensor_type.elem_type))
    values = dict(zip(names, sess.run(names, feeds)))

    g = model.graph
    kept = [n for n in g.node if not set(n.output) & set(names)]
    g.initializer.extend(numpy_helper.from_array(np.asarray(values[n]), n) for n in names)
    # Drop the nodes and initializers nothing reads any more.
    needed = {o.name for o in g.output}
    live = []
    for n in reversed(kept):
        if set(n.output) & needed:
            live.append(n)
            needed.update(i for i in n.input if i)
    del g.node[:]
    g.node.extend(reversed(live))
    inits = [t for t in g.initializer if t.name in needed]
    del g.initializer[:]
    g.initializer.extend(inits)

    onnx.checker.check_model(model)
    left = problems(model)
    if left:
        raise ValueError("float64 remains after folding: " + "; ".join(left))
    onnx.save(model, str(dst))
    return names


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="list what the app's ONNX Runtime would refuse")
    c.add_argument("model", type=Path)
    f = sub.add_parser("fold", help="fold the float64 parts into constants")
    f.add_argument("model", type=Path)
    f.add_argument("out", type=Path)
    args = ap.parse_args(argv)
    if args.cmd == "fold":
        folded = fold_float64(args.model, args.out)
        print(f"folded {len(folded)} tensors into constants: {args.out}")
        return 0
    found = problems(onnx.load(str(args.model)))
    for p in found:
        print(p)
    print(f"{args.model}: {'fits' if not found else 'does not fit'} the app's ONNX Runtime {APP_ORT}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
