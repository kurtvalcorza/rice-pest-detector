import numpy as np
import pytest

torch = pytest.importorskip("torch")
onnx = pytest.importorskip("onnx")
ort = pytest.importorskip("onnxruntime")
pytest.importorskip("transformers")

from transformers import RTDetrConfig, RTDetrForObjectDetection  # noqa: E402

from tools.export_onnx import export_onnx, parity  # noqa: E402

pytestmark = [pytest.mark.torch, pytest.mark.onnx]


@pytest.fixture(scope="module")
def tiny():
    torch.manual_seed(0)
    # initializer_range 0.2, not the default 0.01: at 0.01 each untrained conv and eval-mode BatchNorm shrinks
    # the signal, so every anchor gets the same encoder score and the outputs hardly depend on the input.
    cfg = RTDetrConfig(num_labels=4, num_queries=300, encoder_layers=1, decoder_layers=1, d_model=32,
                       encoder_hidden_dim=32, decoder_in_channels=[32, 32, 32], use_pretrained_backbone=False,
                       initializer_range=0.2)
    return RTDetrForObjectDetection(cfg).eval()


def _max_row_mismatch(onnx_rows: np.ndarray, torch_rows: np.ndarray) -> float:
    """Largest difference after pairing each ONNX query with its closest PyTorch query, one to one.

    The two runtimes can order near-equal queries differently, so rows are matched rather than compared by index."""
    dist = np.abs(onnx_rows[:, None, :] - torch_rows[None, :, :]).max(-1)
    nearest = dist.argmin(1)
    if len(set(nearest.tolist())) != len(nearest):
        return float("inf")
    return float(dist[np.arange(len(nearest)), nearest].max())


@pytest.fixture(scope="module")
def exported(tiny, tmp_path_factory):
    path = tmp_path_factory.mktemp("with space") / "model.onnx"
    meta = export_onnx(tiny, path)
    return path, meta


def test_graph_honours_the_inference_contract(exported):
    path, meta = exported
    model = onnx.load(str(path))
    assert [o.version for o in model.opset_import if o.domain in ("", "ai.onnx")] == [17]
    sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    assert [(i.name, i.shape) for i in sess.get_inputs()] == [("pixel_values", [1, 3, 640, 640])]
    assert [(o.name, o.shape) for o in sess.get_outputs()] == [("logits", [1, 300, 4]), ("pred_boxes", [1, 300, 4])]
    assert meta["opset"] == 17 and meta["bytes"] == path.stat().st_size and len(meta["sha256"]) == 64


def test_outputs_match_pytorch_on_inputs_not_used_for_export(tiny, exported):
    # Regression: exporting outside no_grad/eval froze input-dependent values; fresh inputs then diverged.
    path, _ = exported
    sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    rng = np.random.default_rng(7)
    for _ in range(3):
        x = rng.random((1, 3, 640, 640), dtype=np.float32)
        logits, boxes = sess.run(["logits", "pred_boxes"], {"pixel_values": x})
        with torch.no_grad():
            out = tiny(pixel_values=torch.from_numpy(x))
        onnx_rows = np.concatenate([logits[0], boxes[0]], axis=1)
        torch_rows = np.concatenate([out.logits.numpy()[0], out.pred_boxes.numpy()[0]], axis=1)
        assert _max_row_mismatch(onnx_rows, torch_rows) < 1e-4


def test_parity_report_uses_the_spec_tolerances(tiny, exported):
    path, _ = exported
    rng = np.random.default_rng(3)
    images = [rng.random((1, 3, 640, 640), dtype=np.float32) for _ in range(2)]
    report = parity(tiny, path, images, threshold=0.0)
    assert report["images"] == 2 and report["failures"] == []
    assert report["detections_compared"] == 2 * 300  # threshold 0 keeps every query: not a vacuous pass
    assert report["max_score_diff"] <= 1e-3 and report["min_box_iou"] >= 0.99


def test_parity_judges_each_image_on_its_own_result(monkeypatch, tmp_path):
    # Regression: after one image missed the tolerance, every later image was reported with the running maximum.
    import tools.export_onnx as ex
    from rice_pest_detector.infer import Detection

    class _Sess:
        def __init__(self, *a, **k):
            pass

        def run(self, names, feeds):
            return feeds["pixel_values"], feeds["pixel_values"]

    def fake_post(logits, boxes, w, h, t):
        off = float(np.asarray(logits).ravel()[0])  # image 0 carries a 5e-3 score offset, later images none
        return [Detection(class_id=0, score=0.5 + off, x0=0, y0=0, x1=10, y1=10)]

    class _Model:
        def eval(self):
            return self

        def __call__(self, pixel_values):
            z = np.zeros_like(pixel_values.numpy())
            return type("R", (), {"logits": torch.from_numpy(z), "pred_boxes": torch.from_numpy(z)})()

    monkeypatch.setattr(ex.ort, "InferenceSession", _Sess)
    monkeypatch.setattr(ex, "postprocess", fake_post)
    images = [np.full((1, 3, 4, 4), v, dtype=np.float32) for v in (5e-3, 0.0, 0.0)]
    report = ex.parity(_Model(), tmp_path / "x.onnx", images, threshold=0.0)
    assert [f["image"] for f in report["failures"]] == [0]
    assert report["max_score_diff"] == pytest.approx(5e-3)


def test_parity_flags_a_different_model(tiny, exported, tmp_path):
    torch.manual_seed(99)
    other = RTDetrForObjectDetection(tiny.config).eval()
    path, _ = exported
    rng = np.random.default_rng(3)
    report = parity(other, path, [rng.random((1, 3, 640, 640), dtype=np.float32)], threshold=0.0)
    assert report["failures"], "a different model must fail parity"


def test_export_takes_a_model_input_size(tiny, tmp_path):
    path = tmp_path / "small.onnx"
    meta = export_onnx(tiny, path, size=320)
    sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    assert sess.get_inputs()[0].shape == [1, 3, 320, 320]
    assert "(1,3,320,320)" in meta["input"]


class _PosEmbed(torch.nn.Module):
    """Mimics DINOv2/RF-DETR: positional embeddings resized with antialiased bicubic (no ONNX op)."""

    def __init__(self):
        super().__init__()
        self.table = torch.nn.Parameter(torch.randn(1, 4, 6, 6))

    def interpolate_pos_encoding(self, embeddings, height, width):
        return torch.nn.functional.interpolate(self.table, size=(height // 16, width // 16), mode="bicubic",
                                               align_corners=False, antialias=True)


class _AntialiasModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.pos = _PosEmbed()
        self.head = torch.nn.Linear(4, 8)

    def forward(self, pixel_values):
        h, w = pixel_values.shape[-2:]
        pe = self.pos.interpolate_pos_encoding(None, h, w).flatten(2).mean(-1)          # (1, 4)
        x = self.head(pe + pixel_values.mean()).unsqueeze(1).expand(1, 300, 8)
        return type("Out", (), {"logits": x[..., :4], "pred_boxes": x[..., 4:].sigmoid()})()


def test_export_freezes_antialiased_position_embeddings_and_matches_eager(tmp_path):
    torch.manual_seed(0)
    model = _AntialiasModel().eval()
    path = tmp_path / "aa.onnx"
    export_onnx(model, path, size=96)
    x = torch.rand(1, 3, 96, 96)
    sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    logits, boxes = sess.run(["logits", "pred_boxes"], {"pixel_values": x.numpy()})
    with torch.no_grad():
        ref = model(x)
    assert np.allclose(logits, ref.logits.numpy(), atol=1e-5) and np.allclose(boxes, ref.pred_boxes.numpy(), atol=1e-5)
    assert model.pos.interpolate_pos_encoding.__func__ is _PosEmbed.interpolate_pos_encoding  # restored after export
