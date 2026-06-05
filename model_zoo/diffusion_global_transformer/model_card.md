# Model Card: diffusion_global_costmap_transformer_v0

> The curated generative **global path** (Mode B) model in the **transformer**
> family — a DETR-style set-prediction planner whose raw proposals **aim at an
> off-centre slot** where the flow Mode B model's proposals cannot. Manifest:
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

## What it shows — a representational advance, not a benchmark win

[docs/generative_limits.md](../../docs/generative_limits.md) documented that the
flow Mode B model could **not** aim a proposal at an off-centre gap (a wall blocking
the straight line with a slot ~2 m off-axis): trained on gap data it stayed
near-straight or veered to the wrong side, because a 16-dimensional CNN embedding
cannot localize a thin slot.

This transformer, trained on the **same** gap data, **aims its proposals at the
slot on both sides**. The difference is architectural: a strided conv tokenizes the
patch into spatial cells with learned positions, and K query tokens **cross-attend**
over those tokens, so the model localizes the slot and bends every candidate toward
it. Measured (held-out gap patches, exported ONNX): slot at +2.0 m → candidates'
lateral offset at the wall ≈ +2.0 m; slot at −2.0 m → ≈ −2.0 m. In a direct A/B on
the same gap-only data the flow model does not (flow loss 0.12, stays near-straight /
wrong side; transformer loss 0.009, aims on both sides).

**Honest scope — a benchmark *peer* of the flow model, plus the slot-aiming
property; not a gap-solving win.** On the footprint-validated `planner_benchmark`
this model behaves like the flow Mode B model: it clears *clear* and *side obstacle*
and reports *no path* on *off-centre gap* / *slalom*. (The K candidates are trained
as a small lateral fan so the validator gets a spread of options around the aimed
route — the flow model gets this for free from its K fixed latents; adding it fixed
an earlier side-obstacle regression.) Its distinct property is at the *proposal*
level: it aims proposals at the off-centre slot where the flow model cannot — a
representational result, verified by the A/B probe and the C++ direction test
(`OnnxPathModelTest.CuratedZooTransformerAimsAtOffCentreSlot`). But that aim still
does **not** thread the narrow (1 m) footprint-validated slot, so pure-generative
does not solve *off-centre gap*; the **hybrid** planner (generative propose →
classical search dispose) remains the completeness guarantee. The value here is
evidence that the *proposal-direction* limitation is architectural, not fundamental
— a step toward a generative planner that could pass the validated gap with a wider
slot / larger capacity / footprint-aware training.

## Intended use

Research demonstration of architecture-dependent spatial routing in the *propose*
stage. Not a deployment model and not a drop-in upgrade over the flow Mode B model
for the benchmark; the deterministic costmap-validity layer gates every proposal and
the hybrid planner remains the completeness guarantee.

## Out-of-scope / limitations

- **Synthetic data only.** Never validated on a real robot or rosbag.
- **Benchmark peer, not a gap solver.** On `planner_benchmark` it matches the flow
  model (clears *clear* + *side obstacle*); it does **not** pass *off-centre gap* (its
  proposals aim at the slot but pure-generative validation still fails on the 1 m
  slot). The hybrid planner solves the gap.
- **Window-bounded.** Slot aiming demonstrated for offsets up to ~2 m inside the
  24×24 / 6×6 m goal-aligned patch; classical search / the hybrid planner own the
  general routing problem.
- **Research model.** Do not deploy on hardware; the validity layer is the authority.

## Training data

`make_costmap_path_dataset` (one-sided obstacle → bow to the free side) +
`make_costmap_path_gap_dataset` (wall with one off-centre slot → expert routes through
the slot via a Gaussian detour peaking at the slot offset where the path crosses the
wall), combined as the `'both'` dataset (192 samples). Mirrored +y/−y pairs and clear
samples keep the response symmetric. Fully procedural; no real data.

## Benchmark results

Research placeholder → checked **behaviourally** at the proposal level:

- **Off-centre-slot aiming (exported ONNX):** wall + slot at ±2 m → every candidate's
  lateral offset at the wall ≈ the slot offset. The flow Mode B model fails the same
  probe. Guarded by `OnnxPathModelTest.CuratedZooTransformerAimsAtOffCentreSlot`.
- **One-sided obstacle:** candidates veer to the free side.
- **Footprint-validated planner benchmark:** a peer of the flow Mode B model —
  clears *clear* and *side obstacle*, *no path* on *off-centre gap* / *slalom* (the
  hybrid planner solves those); see
  [docs/planner_comparison.md](../../docs/planner_comparison.md) and
  [docs/generative_limits.md](../../docs/generative_limits.md).
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
  (slot aiming, side selection) is stable.

## License

Model: Apache-2.0 · Data: Apache-2.0 (procedurally generated here) · Code: Apache-2.0
