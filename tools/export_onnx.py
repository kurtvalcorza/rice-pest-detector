"""Export a trained RT-DETR checkpoint to ONNX under the inference contract (spec §4.5) and check
parity with PyTorch: same kept detections (count and classes), box IoU >= 0.99, score diff <= 1e-3.
Detections are paired by class and box overlap, not by list order, so near-equal scores that the two
runtimes rank differently do not count as a failure.

Export runs in inference mode (eval + no_grad). Exporting outside it froze input-dependent values
into the graph and outputs diverged on any input other than the one used to trace.

Run: python -m tools.export_onnx --checkpoint runs/run-r18/best.pt --out models/rice-pest-r18-1.onnx
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch

from rice_pest_detector.infer import INPUT_SIZE, postprocess

OPSET = 17
IOU_MIN, SCORE_DIFF_MAX = 0.99, 1e-3


class _ContractOutputs(torch.nn.Module):
    """Expose only the contract's two outputs, under their contract names."""

    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, pixel_values):
        out = self.model(pixel_values=pixel_values)
        return out.logits, out.pred_boxes


class _FrozenPosEncodings:
    """RF-DETR's DINOv2 backbone resizes its position embeddings with antialiased bicubic interpolation,
    which has no ONNX op, and always runs it while tracing. At a fixed input size the result is a constant:
    compute it eagerly (exact training-time values), serve it during the trace, then restore the method."""

    def __init__(self, model, example):
        self.model, self.example, self.patched = model, example, []

    def __enter__(self):
        for module in self.model.modules():
            original = getattr(module, "interpolate_pos_encoding", None)
            if original is None or not callable(original):
                continue
            cache = {}

            def frozen(embeddings, height, width, _original=original, _cache=cache):
                key = (int(height), int(width))  # traced shapes arrive as 0-d tensors
                if key not in _cache:
                    _cache[key] = _original(embeddings, height, width).detach()
                return _cache[key]

            module.interpolate_pos_encoding = frozen
            self.patched.append(module)
        if self.patched:
            with torch.no_grad():
                self.model(pixel_values=self.example)  # eager pass fills the caches
        return self

    def __exit__(self, *exc):
        for module in self.patched:
            del module.interpolate_pos_encoding  # drop the instance attribute; the class method is back
        return False


def export_onnx(model, out: Path, size: int = INPUT_SIZE) -> dict:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    wrapper = _ContractOutputs(model).eval()
    example = torch.zeros(1, 3, size, size)
    with torch.no_grad(), _FrozenPosEncodings(wrapper.model, example):
        torch.onnx.export(wrapper, (example,), str(out), input_names=["pixel_values"],
                          output_names=["logits", "pred_boxes"], opset_version=OPSET, dynamo=False)
    data = out.read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "opset": OPSET,
            "input": f"pixel_values (1,3,{size},{size}) float32, [0,1], NCHW", "outputs": ["logits", "pred_boxes"]}


def _iou(a, b) -> float:
    ix = max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0))
    iy = max(0.0, min(a.y1, b.y1) - max(a.y0, b.y0))
    inter = ix * iy
    union = (a.x1 - a.x0) * (a.y1 - a.y0) + (b.x1 - b.x0) * (b.y1 - b.y0) - inter
    return inter / union if union > 0 else 1.0


def _pair(a, b):
    """Pair each ONNX detection with a PyTorch detection of the same class, greedily by highest box IoU.

    Detections are not compared by list position: when scores are nearly equal, the two runtimes can rank the
    same detections in a different order (and break exact ties differently from one platform to another).
    Returns the pairs, or None when the counts differ or a detection has no same-class partner."""
    if len(a) != len(b):
        return None
    candidates = sorted(((_iou(da, db), i, j) for i, da in enumerate(a) for j, db in enumerate(b)
                         if da.class_id == db.class_id), reverse=True)
    used_a, used_b, pairs = set(), set(), []
    for _, i, j in candidates:
        if i not in used_a and j not in used_b:
            used_a.add(i)
            used_b.add(j)
            pairs.append((a[i], b[j]))
    return pairs if len(pairs) == len(a) else None


def parity(model, onnx_path: Path, images: list[np.ndarray], threshold: float = 0.5,
           width: int = INPUT_SIZE, height: int = INPUT_SIZE) -> dict:
    """Compare kept detections from PyTorch and ONNX Runtime on preprocessed (1,3,640,640) inputs."""
    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    model = model.eval()
    failures, max_score, min_iou, compared = [], 0.0, 1.0, 0
    for i, x in enumerate(images):
        logits, boxes = sess.run(["logits", "pred_boxes"], {"pixel_values": x})
        with torch.no_grad():
            ref = model(pixel_values=torch.from_numpy(x))
        a = postprocess(logits, boxes, width, height, threshold)
        b = postprocess(ref.logits.numpy(), ref.pred_boxes.numpy(), width, height, threshold)
        pairs = _pair(a, b)
        if pairs is None:
            failures.append({"image": i, "reason": f"kept {len(a)} vs {len(b)} or classes differ"})
            continue
        compared += len(pairs)
        for da, db in pairs:
            max_score = max(max_score, abs(da.score - db.score))
            min_iou = min(min_iou, _iou(da, db))
        if max_score > SCORE_DIFF_MAX or min_iou < IOU_MIN:
            failures.append({"image": i, "reason": f"score diff {max_score:.2e}, iou {min_iou:.4f}"})
    return {"images": len(images), "threshold": threshold, "max_score_diff": max_score,
            "min_box_iou": min_iou, "detections_compared": compared, "failures": failures}


def load_trained(checkpoint: Path, base_model: str, revision: str):
    """Rebuild the fine-tuned architecture from the base config (no base weights) and load best.pt."""
    from transformers import AutoConfig, AutoModelForObjectDetection

    from rice_pest_detector import CLASS_NAMES
    from rice_pest_detector.train import load_best

    id2label = dict(enumerate(CLASS_NAMES))
    config = AutoConfig.from_pretrained(base_model, revision=revision, num_labels=len(CLASS_NAMES),
                                        id2label=id2label, label2id={v: k for k, v in id2label.items()},
                                        num_queries=300)
    config.use_pretrained_backbone = False
    model = AutoModelForObjectDetection.from_config(config)
    state, meta = load_best(checkpoint)
    model.load_state_dict(state)
    return model.eval(), meta


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--base-model", default="PekingU/rtdetr_r18vd")
    ap.add_argument("--revision", default="ac77a11ff0170a41b771c03264987f8ce2b0d753")
    ap.add_argument("--size", type=int, default=INPUT_SIZE, help="square input size the model was trained at")
    args = ap.parse_args(argv)
    model, meta = load_trained(args.checkpoint, args.base_model, args.revision)
    info = export_onnx(model, args.out, size=args.size)
    info["checkpoint_sha256"] = hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
    info["checkpoint_epoch"] = meta.get("epoch")
    args.out.with_suffix(".json").write_text(json.dumps(info, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(info, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
