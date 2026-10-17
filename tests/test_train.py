import json
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

from rice_pest_detector.train import (  # noqa: E402
    TrainConfig, ManifestDataset, build_model, collate, evaluate, load_checkpoint, record_best,
    resume_best, save_checkpoint,
)
from transformers import RTDetrConfig  # noqa: E402

pytestmark = pytest.mark.torch


def _tiny_cfg() -> TrainConfig:
    return TrainConfig(base_model="__tiny__", revision="", epochs=1, batch_size=1, fp16=False, num_workers=0)


def test_collate_stacks_pixels_and_keeps_targets():
    item = (torch.zeros(3, 640, 640), {"class_labels": torch.tensor([1]), "boxes": torch.rand(1, 4)})
    pixels, targets = collate([item, item])
    assert pixels.shape == (2, 3, 640, 640) and len(targets) == 2


def test_checkpoint_round_trip_restores_epoch_metric_and_optimizer(tmp_path: Path, monkeypatch):
    cfg = _tiny_cfg()
    monkeypatch.setattr("rice_pest_detector.train._tiny_config",
                        lambda: RTDetrConfig(num_labels=4, num_queries=10, encoder_layers=1,
                                             decoder_layers=1, d_model=32, encoder_hidden_dim=32,
                                             use_pretrained_backbone=False))
    model = build_model(cfg)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=10)
    scaler = torch.amp.GradScaler("cpu", enabled=True, init_scale=1024.0)
    for p in model.parameters():
        p.grad = torch.ones_like(p)
    opt.step()
    sched.step()
    save_checkpoint(tmp_path / "last.pt", model, opt, sched, epoch=3, best_metric=0.42, scaler=scaler)
    model2 = build_model(cfg)
    opt2 = torch.optim.AdamW(model2.parameters(), lr=1e-4)
    sched2 = torch.optim.lr_scheduler.CosineAnnealingLR(opt2, T_max=10)
    scaler2 = torch.amp.GradScaler("cpu", enabled=True)
    assert load_checkpoint(tmp_path / "last.pt", model2, opt2, sched2, scaler=scaler2) == (4, 0.42)
    assert sched2.last_epoch == sched.last_epoch
    assert scaler2.get_scale() == 1024.0
    assert opt.state_dict()["state"], "optimizer must have state to compare"
    for k, st in opt.state_dict()["state"].items():
        for name, v in st.items():
            assert torch.equal(torch.as_tensor(v), torch.as_tensor(opt2.state_dict()["state"][k][name]))
    a, b = next(model.parameters()), next(model2.parameters())
    assert torch.equal(a, b)


def _tiny_model(monkeypatch):
    monkeypatch.setattr("rice_pest_detector.train._tiny_config",
                        lambda: RTDetrConfig(num_labels=4, num_queries=10, encoder_layers=1,
                                             decoder_layers=1, d_model=32, encoder_hidden_dim=32,
                                             decoder_in_channels=[32, 32, 32],
                                             use_pretrained_backbone=False))
    return build_model(_tiny_cfg())


def test_loss_runs_in_fp32_with_autocast_off_under_mixed_precision(monkeypatch):
    # The fp16 Hungarian matcher can produce inf costs that scipy rejects (ValueError) before
    # the loop's finite-loss check; CPU torch cannot run cdist in half, so we pin the contract:
    # every tensor reaching the loss is float32 and autocast is disabled inside it.
    from rice_pest_detector.train import fp32_loss
    model = _tiny_model(monkeypatch)
    inner, seen = model.loss_function.__wrapped__, []

    def spy(*args, **kwargs):
        tensors = [x for x in args if torch.is_tensor(x)] + [v for v in kwargs.values() if torch.is_tensor(v)]
        tensors += [v for lab in args[1] for v in lab.values()]
        seen.append(({t.dtype for t in tensors if t.is_floating_point()}, torch.is_autocast_enabled("cpu")))
        return inner(*args, **kwargs)

    model.loss_function = fp32_loss(spy)
    model.train()
    labels = [{"class_labels": torch.tensor([1]), "boxes": torch.tensor([[0.5, 0.5, 0.2, 0.2]])}]
    with torch.autocast("cpu", dtype=torch.bfloat16):
        out = model(pixel_values=torch.rand(1, 3, 64, 64), labels=labels)
    assert out.logits.dtype == torch.bfloat16  # autocast was really active for the forward pass
    assert seen == [({torch.float32}, False)]
    assert torch.isfinite(out.loss)


def test_fp32_loss_casts_nested_inputs_and_keeps_integers():
    from rice_pest_detector.train import fp32_loss
    got = {}

    def loss(logits, labels, meta=None):
        got.update(logits=logits.dtype, cls=labels[0]["class_labels"].dtype,
                   boxes=labels[0]["boxes"].dtype, meta=meta)
        return logits.sum()

    labels = [{"class_labels": torch.tensor([1]), "boxes": torch.zeros(1, 4, dtype=torch.float16)}]
    fp32_loss(loss)(torch.zeros(2, dtype=torch.float16), labels, meta={"n": 3})
    assert got == {"logits": torch.float32, "cls": torch.long, "boxes": torch.float32, "meta": {"n": 3}}


def test_best_pt_carries_its_own_score_so_a_stale_sidecar_cannot_mislead_resume(tmp_path: Path, monkeypatch):
    from rice_pest_detector.train import load_best
    model = _tiny_model(monkeypatch)
    record_best(tmp_path, model, score=0.4, epoch=2, best=-1.0)
    old_sidecar = (tmp_path / "best.json").read_text()
    record_best(tmp_path, model, score=0.9, epoch=5, best=0.4)
    (tmp_path / "best.json").write_text(old_sidecar)  # disconnect between best.pt and best.json
    assert resume_best(tmp_path, ckpt_best=0.4) == 0.9
    state, meta = load_best(tmp_path / "best.pt")
    assert meta["map50_species"] == 0.9 and meta["epoch"] == 5
    assert state.keys() == model.state_dict().keys()
    assert record_best(tmp_path, model, score=0.5, epoch=6, best=resume_best(tmp_path, 0.4)) == 0.9
    assert load_best(tmp_path / "best.pt")[1]["epoch"] == 5


def test_legacy_bare_state_dict_best_pt_still_loads(tmp_path: Path, monkeypatch):
    from rice_pest_detector.train import load_best
    model = _tiny_model(monkeypatch)
    torch.save(model.state_dict(), tmp_path / "best.pt")
    (tmp_path / "best.json").write_text(json.dumps({"map50_species": 0.83, "epoch": 3}))
    state, meta = load_best(tmp_path / "best.pt")
    assert meta == {} and state.keys() == model.state_dict().keys()
    assert resume_best(tmp_path, ckpt_best=0.1) == 0.83


def _opt_sched(model):
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4)
    return opt, torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=10)


def test_resume_refuses_a_different_experiment(tmp_path: Path, monkeypatch):
    from rice_pest_detector.train import experiment_id
    model = _tiny_model(monkeypatch)
    cfg = _tiny_cfg()
    saved = experiment_id(cfg, {"images": []}, b"{}")
    save_checkpoint(tmp_path / "last.pt", model, *_opt_sched(model), epoch=0, best_metric=0.1,
                    experiment=saved)
    same = experiment_id(TrainConfig(**{**cfg.__dict__, "num_workers": 7}), {"images": []}, b"{}")
    assert load_checkpoint(tmp_path / "last.pt", model, *_opt_sched(model), experiment=same) == (1, 0.1)
    changed = experiment_id(TrainConfig(**{**cfg.__dict__, "lr": 9e-4}), {"images": [{"x": 1}]}, b"{}")
    with pytest.raises(RuntimeError, match=r"changed: lr, manifest_sha256.*new RUN_DIR"):
        load_checkpoint(tmp_path / "last.pt", model, *_opt_sched(model), experiment=changed)


def test_resume_restores_random_state(tmp_path: Path, monkeypatch):
    import random
    import numpy as np
    model = _tiny_model(monkeypatch)
    save_checkpoint(tmp_path / "last.pt", model, *_opt_sched(model), epoch=0, best_metric=0.0)
    expected = (random.random(), float(np.random.rand()), float(torch.rand(1)))
    random.seed(1), np.random.seed(1), torch.manual_seed(1)
    load_checkpoint(tmp_path / "last.pt", model, *_opt_sched(model))
    assert (random.random(), float(np.random.rand()), float(torch.rand(1))) == expected


def test_history_drops_only_a_truncated_final_line(tmp_path: Path):
    from rice_pest_detector.train import read_history, trim_history
    path = tmp_path / "history.jsonl"
    path.write_text(json.dumps({"epoch": 0}) + "\n" + json.dumps({"epoch": 1}) + "\n" + '{"epoch": 2, "lo')
    assert [r["epoch"] for r in read_history(path)] == [0, 1]
    trim_history(path, 5)
    assert [json.loads(ln)["epoch"] for ln in path.read_text().splitlines()] == [0, 1]
    path.write_text('{"epoch": 0, "lo\n' + json.dumps({"epoch": 1}) + "\n")
    with pytest.raises(json.JSONDecodeError):
        read_history(path)


def test_cached_test_result_is_bound_to_the_whole_evaluation(tmp_path: Path):
    from rice_pest_detector.train import check_cached_test, evaluation_id
    (tmp_path / "best.pt").write_bytes(b"weights")
    (tmp_path / "coco.json").write_text("{}")
    ident = evaluation_id(tmp_path / "best.pt", {"images": []}, tmp_path / "coco.json", 0.5)
    check_cached_test({"evaluation": ident}, ident)
    for change in ({"threshold": 0.3}, {"manifest_sha256": "x"}, {"annotations_sha256": "y"}):
        with pytest.raises(RuntimeError, match=f"changed: {next(iter(change))}"):
            check_cached_test({"evaluation": ident}, {**ident, **change})
    check_cached_test({"best_pt_sha256": ident["best_pt_sha256"]}, ident)  # legacy record
    with pytest.raises(RuntimeError, match="best.pt changed"):
        check_cached_test({"best_pt_sha256": "other"}, ident)


def test_evaluate_reports_count_errors_baseline_and_scores(monkeypatch):
    from types import SimpleNamespace
    from rice_pest_detector import train as T

    class Fixed(torch.nn.Module):  # one well-placed RBB_FEMALE box scoring sigmoid(logit)
        def __init__(self, logit):
            super().__init__()
            self.p = torch.nn.Parameter(torch.zeros(1))
            self.logit = logit

        def forward(self, pixel_values=None):
            logits = torch.full((1, 2, 4), -20.0)
            logits[0, 0, 0] = self.logit
            boxes = torch.tensor([[[0.5, 0.5, 0.2, 0.2], [0.1, 0.1, 0.1, 0.1]]])
            return SimpleNamespace(logits=logits, pred_boxes=boxes)

    rec = {"file": "a.jpg", "relative_path": "a.jpg", "split": "val", "width": 10, "height": 10,
           "boxes": [[0, 0.5, 0.5, 0.2, 0.2]]}
    ds = T.ManifestDataset({"images": [rec]}, Path("."), "val")
    monkeypatch.setattr(T.ManifestDataset, "__getitem__", lambda self, i: (torch.zeros(3, 640, 640), None))
    coco = {"images": [{"id": 1, "file_name": "a.jpg", "width": 10, "height": 10}],
            "annotations": [{"id": 1, "image_id": 1, "category_id": 1, "bbox": [4, 4, 2, 2], "area": 4,
                             "iscrowd": 0}],
            "categories": [{"id": i + 1, "name": n} for i, n in enumerate(T.CLASS_NAMES)]}
    low = T.evaluate(Fixed(-1.0), ds, coco)  # score 0.27: ranked first, but below 0.5
    assert low["detections_kept"] == 0 and low["map50_species"] > 0.9
    assert low["count_accuracy"] == low["count_accuracy_no_detection_baseline"] == 1.0
    assert low["count_errors"]["RBB"]["presence_recall"] == 0.0
    assert low["top_score_per_image"]["max"] == pytest.approx(0.2689, abs=1e-3)
    high = T.evaluate(Fixed(3.0), ds, coco)
    assert high["detections_kept"] == 1 and high["count_errors"]["RBB"]["exact"] == 1.0


def test_fit_skips_update_on_infinite_gradient(tmp_path: Path, monkeypatch):
    from rice_pest_detector import train as T
    manifest, run = _fit_fixture(tmp_path)

    class InfGrad(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.w = torch.nn.Parameter(torch.ones(1))
            self.calls = 0

        def forward(self, pixel_values=None, labels=None):
            from types import SimpleNamespace
            self.calls += 1
            if self.calls == 2:  # finite loss, infinite gradient: sqrt'(0) = inf
                return SimpleNamespace(loss=(self.w - 1).abs().sqrt().sum())
            return SimpleNamespace(loss=(self.w * 0).sum() + 1.0)

    model = InfGrad()
    monkeypatch.setattr(T, "build_model", lambda cfg: model)
    monkeypatch.setattr(T, "evaluate", lambda *a, **k: {"map50_species": 0.1})
    cfg = TrainConfig(base_model="x", revision="", epochs=1, batch_size=1, fp16=False, num_workers=0)
    T.fit(cfg, manifest, tmp_path, run)
    row = json.loads((run / "history.jsonl").read_text().splitlines()[0])
    assert (row["updates"], row["skipped_updates"], row["nonfinite_loss_steps"]) == (2, 1, 0)
    assert torch.isfinite(model.w).all()


def test_resume_does_not_let_worse_model_overwrite_best(tmp_path: Path, monkeypatch):
    model = _tiny_model(monkeypatch)
    # epoch N: best.pt + best.json written, but last.pt still holds epoch N-1 (lower best).
    best = record_best(tmp_path, model, score=0.30, epoch=1, best=-1.0)
    assert best == 0.30
    saved = (tmp_path / "best.pt").read_bytes()
    assert json.loads((tmp_path / "best.json").read_text()) == {"map50_species": 0.30, "epoch": 1}
    assert resume_best(tmp_path, ckpt_best=0.10) == 0.30
    assert resume_best(tmp_path / "nowhere", ckpt_best=0.10) == 0.10
    # resumed epoch scores worse than best.json; perturb the model so a rewrite would be visible.
    with torch.no_grad():
        next(model.parameters()).add_(1.0)
    best = record_best(tmp_path, model, score=0.20, epoch=1, best=resume_best(tmp_path, 0.10))
    assert best == 0.30
    assert (tmp_path / "best.pt").read_bytes() == saved
    assert not list(tmp_path.glob("*.tmp"))
    assert isinstance(torch.load(tmp_path / "best.pt", weights_only=True), dict)


def test_evaluate_rejects_mismatched_coco(monkeypatch):
    model = _tiny_model(monkeypatch)
    ds = ManifestDataset({"images": [{"file": "a.jpg", "relative_path": "a.jpg", "split": "val",
                                      "width": 8, "height": 8, "boxes": []}]}, Path("."), "val")
    with pytest.raises(AssertionError, match="b.jpg.*a.jpg"):
        evaluate(model, ds, {"images": [{"id": 1, "file_name": "b.jpg"}], "annotations": [],
                             "categories": []})


class _FakeModel(torch.nn.Module):
    """Stands in for RT-DETR: loss is `scale * w` so tests control finiteness."""

    def __init__(self, loss_values):
        super().__init__()
        self.w = torch.nn.Parameter(torch.ones(1))
        self.loss_values = loss_values
        self.calls = 0

    def forward(self, pixel_values=None, labels=None):
        value = self.loss_values(self.calls)
        self.calls += 1
        from types import SimpleNamespace
        return SimpleNamespace(loss=self.w.sum() * value)


def _fit_fixture(tmp_path: Path):
    from PIL import Image
    manifest = {"images": []}
    for i in range(3):
        name = f"t{i}.jpg"
        Image.new("RGB", (32, 32)).save(tmp_path / name)
        manifest["images"].append({"file": name, "relative_path": name, "split": "train", "width": 32,
                                   "height": 32, "boxes": [[0, 0.5, 0.5, 0.2, 0.2]]})
    run = tmp_path / "run"
    run.mkdir()
    (run / "annotations_val.json").write_text("{}")
    return manifest, run


def test_fit_raises_after_persistent_nonfinite_loss(tmp_path: Path, monkeypatch):
    from rice_pest_detector import train as T
    manifest, run = _fit_fixture(tmp_path)
    model = _FakeModel(lambda n: float("nan"))
    monkeypatch.setattr(T, "build_model", lambda cfg: model)
    monkeypatch.setattr(T, "MAX_NONFINITE_STEPS", 3)
    cfg = TrainConfig(base_model="x", revision="", epochs=1, batch_size=1, fp16=False, num_workers=0)
    with pytest.raises(RuntimeError, match=r"non-finite.*epoch 0, step 2"):
        T.fit(cfg, manifest, tmp_path, run)


def test_fit_tolerates_isolated_nonfinite_and_excludes_it_from_mean(tmp_path: Path, monkeypatch):
    from rice_pest_detector import train as T
    manifest, run = _fit_fixture(tmp_path)
    model = _FakeModel(lambda n: float("nan") if n == 1 else 2.0)
    monkeypatch.setattr(T, "build_model", lambda cfg: model)
    monkeypatch.setattr(T, "MAX_NONFINITE_STEPS", 2)
    monkeypatch.setattr(T, "evaluate", lambda *a, **k: {"map50_species": 0.1})
    cfg = TrainConfig(base_model="x", revision="", epochs=1, batch_size=1, fp16=False, num_workers=0)
    T.fit(cfg, manifest, tmp_path, run)
    row = json.loads((run / "history.jsonl").read_text().splitlines()[0])
    assert row["train_loss"] == pytest.approx(2.0, abs=0.01)
    assert torch.isfinite(model.w).all()


def test_trim_history_drops_rows_from_resume_epoch(tmp_path: Path):
    from rice_pest_detector.train import trim_history
    path = tmp_path / "history.jsonl"
    path.write_text("".join(json.dumps({"epoch": e}) + "\n" for e in range(4)))
    trim_history(path, 2)
    assert [json.loads(ln)["epoch"] for ln in path.read_text().splitlines()] == [0, 1]
    assert not list(tmp_path.glob("*.tmp"))
    trim_history(tmp_path / "missing.jsonl", 2)  # no-op


def test_record_best_ignores_nan_score(tmp_path: Path, monkeypatch):
    model = _tiny_model(monkeypatch)
    assert record_best(tmp_path, model, score=float("nan"), epoch=0, best=-1.0) == -1.0
    assert not (tmp_path / "best.pt").exists()
    assert record_best(tmp_path, model, score=0.2, epoch=1, best=-1.0) == 0.2
    assert record_best(tmp_path, model, score=float("nan"), epoch=2, best=0.2) == 0.2


def test_input_size_reaches_the_dataset_and_only_non_default_sizes_change_the_fingerprint(tmp_path: Path):
    from PIL import Image as PILImage

    from rice_pest_detector.train import experiment_id

    PILImage.new("RGB", (64, 48)).save(tmp_path / "a.jpg")
    manifest = {"images": [{"file": "a.jpg", "relative_path": "a.jpg", "split": "val",
                            "boxes": [[0, 0.5, 0.5, 0.1, 0.1]]}]}
    pixels, _ = ManifestDataset(manifest, tmp_path, "val", size=576)[0]
    assert tuple(pixels.shape) == (3, 576, 576)
    base = TrainConfig(base_model="m", revision="r")
    legacy = {k: v for k, v in base.__dict__.items() if k not in ("num_workers", "input_size")}
    assert experiment_id(base, {"images": []}, b"{}")["config"] == legacy  # 640 runs keep their identity
    assert experiment_id(TrainConfig(base_model="m", revision="r", input_size=576),
                         {"images": []}, b"{}")["config"]["input_size"] == 576
