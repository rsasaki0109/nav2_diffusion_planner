# Model Card: diffusion_global_costmap_transformer_v0

> The curated generative **global path** (Mode B) model in the **transformer**
> family — a DETR-style set-prediction planner that **routes through an off-centre
> gap**, the ceiling the flow Mode B model could not cross. Manifest:
> [manifest.yaml](manifest.yaml). Reproduce: [export.py](export.py). Sibling:
> [../diffusion_global/model_card.md](../diffusion_global/model_card.md).

## Summary

- **Model family:** transformer set prediction (1 deterministic forward pass)
- **Task:** global **path** proposal for the Nav2 **Mode B** planner
  (`nav2_diffusion_global_planner::DiffusionGlobalPlanner` →
  `nav2_diffusion_onnx::OnnxPathModel`)
- **Inputs:** goal-aligned costmap patch (24×24, 6×6 m window) + goal distance
- **Output:** 5 candidate start→goal paths × 12 waypoints in the goal-aligned frame,
  validated against the live costmap by the planner
- **Runtime / precision:** ONNX / fp32
- **Artifact:** `costmap_transformer.onnx` (small, checked in, reproducible from
  `export.py`).

## Why it matters — the off-centre-gap ceiling, crossed

[docs/generative_limits.md](../../docs/generative_limits.md) documented that the
flow Mode B model could **not** route through an off-centre gap (a wall blocking the
straight line with a slot ~2 m off-axis): trained on gap data it stayed near-straight
or veered to the wrong side, because a 16-dimensional CNN embedding cannot localize a
thin slot and the decision did not transfer to resampled patches.

This transformer, trained on the **same** gap data, **routes through the slot on both
sides**. The difference is architectural: a strided conv tokenizes the patch into
spatial cells with learned positions, and K query tokens **cross-attend** over those
tokens, so the model can localize the slot and bend every candidate toward it.

Measured (held-out gap patches, exported ONNX): slot at +2.0 m → all candidates'
lateral offset at the wall ≈ +1.3 m (toward the slot); slot at −2.0 m → ≈ −1.6 m. The
flow model on the identical data does not (stays near-straight / wrong side). This is a
genuine architectural ceiling-break, not a hybrid fallback.

## Intended use

Demonstration / research. It proves that the *propose → validate → select* Mode B
architecture can, with an attention-based proposer, solve a routing case previously
left to classical search / the hybrid fallback. The deterministic costmap-validity
layer in the planner still gates every proposal.

## Out-of-scope / limitations

- **Synthetic data only.** Never validated on a real robot or rosbag.
- **Window-bounded.** Slot routing demonstrated for offsets up to ~2 m inside the
  24×24 / 6×6 m goal-aligned patch; larger detours / multi-slot mazes are out of scope
  (classical search still owns the general routing problem — the hybrid planner remains
  available).
- **Research model.** Do not deploy on hardware; the validity layer is the authority.

## Training data

`make_costmap_path_dataset` (one-sided obstacle → bow to the free side) +
`make_costmap_path_gap_dataset` (wall with one off-centre slot → expert routes through
the slot via a Gaussian detour peaking at the slot offset where the path crosses the
wall), combined as the `'both'` dataset (192 samples). Mirrored +y/−y pairs and clear
samples keep the response symmetric. Fully procedural; no real data.

## Benchmark results

Research placeholder → checked **behaviourally**:

- **Off-centre-gap routing (exported ONNX):** wall + slot at ±2 m → every candidate
  detours toward the slot at the wall (see numbers above). The flow Mode B model fails
  the same probe.
- **One-sided obstacle:** candidates veer to the free side (retains the flow model's
  competence).
- **Cross-comparison:** appears as *Diffusion (Mode B, transformer)* in
  [docs/planner_comparison.md](../../docs/planner_comparison.md).
- **Collisions:** the planner's deterministic costmap-validity layer gates every
  proposal regardless of model quality.

## Safety

- The model has **no** validity authority; the planner validates every proposal
  against the live costmap and falls back / reports no-path if none is valid.
- Not for hardware use; no ODD validation performed.

## Reproducibility

- **Command:** `PYTHONPATH=../../nav2_diffusion_training python3 export.py`
  (CUDA when available; `CUDA_VISIBLE_DEVICES= ` forces a deterministic CPU build)
- **Seed:** 0 · **Toolchain:** torch 2.10.0+cu128, onnx 1.21.0; trained on CUDA,
  exported on CPU
- **Hyperparameters:** transformer, `'both'` dataset, 192 samples, 3000 epochs, lr 0.01
- Bit-for-bit reproduction may vary across torch versions / hardware; behaviour
  (gap routing, side selection) is stable.

## License

Model: Apache-2.0 · Data: Apache-2.0 (procedurally generated here) · Code: Apache-2.0
