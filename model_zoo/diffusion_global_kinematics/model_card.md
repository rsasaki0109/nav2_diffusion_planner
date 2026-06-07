# Model Card: diffusion_global_costmap_kinematics_v0

> A **kinematics-conditioned** generative Mode B path model: one network, conditioned
> on the vehicle's **min turn radius R** (the second context input), proposes a *sharp*
> detour for a differential-drive robot and a *gentle* one for an Ackermann car through
> the same gap — and the planner's curvature validator *disposes* of any proposal that
> turns tighter than the vehicle can. Manifest: [manifest.yaml](manifest.yaml).
> Reproduce: [export.py](export.py). Architecture sibling (8/8 all-course):
> [../diffusion_global_attnseq/model_card.md](../diffusion_global_attnseq/model_card.md).

## Summary

- **Model family:** attnseq (no-fan cross-attention autoregressive), conditioned on R
- **Task:** vehicle-kinematics-aware global **path** proposal for Nav2 **Mode B**
- **Inputs:** goal-aligned costmap patch (24×24) + **[goal distance, min turn radius R]**
- **Output:** 5 candidate paths × 12 waypoints in the goal-aligned frame
- **Runtime / precision:** ONNX / fp32
- **Artifact:** `costmap_kinematics.onnx` (checked in, reproducible from `export.py`).

## What it shows — one model, many steering geometries

The Mode B `PathModel` seam had a spare context slot (`context = [goal_distance, 0]`).
Filling it with the vehicle **min turn radius R** lets a single model serve several
steering geometries. Training shapes each maneuver's lateral detour so its peak
curvature ≈ 1/R (a Gaussian of width `w = sqrt(2·off·R)`): small R (a differential-drive
robot that can pivot) → a sharp, tight detour; large R (an Ackermann / car-like robot)
→ a gentle, wide one — through the *same* gap.

The planner closes the loop with a **curvature validator**: a `min_turn_radius`
parameter makes `DiffusionGlobalPlanner::isPathValid` reject any proposal whose discrete
curvature (Menger circumradius of consecutive waypoints) exceeds 1/R anywhere. This is
the propose/dispose split extended from footprint to **vehicle dynamics**: the model
*proposes* a kinematics-appropriate path, the deterministic layer *disposes* of
infeasible ones.

**Result (real C++ `planner_benchmark`):**

| course | diff-drive (R=0.3) | Ackermann (R=1.5) |
|---|:-:|:-:|
| clear / centred gap / narrow gap / double gate | yes | yes |
| **off-centre gap / far off-centre gap** | **yes** | **no path** |

On the off-centre gap, the diff-drive row threads a sharp detour; the Ackermann row's
path would need curvature ~0.7 > 1/R = 0.67, so the curvature validator disposes it
(*no path*) — kinematically correct, a 2 m lateral jog in ~1 m of travel is past a car's
turning circle. The peak output curvature is **monotonic** in the commanded R
(diff > mid > Ackermann), measured on the exported ONNX.

## Honest scope — what it does NOT do

- **Demonstration model.** Covers clear / off-centre / far / centred gap conditioned on
  R; **slalom and double gate are out of scope** (their fixed S is not a single R-shaped
  bump — use `diffusion_global_costmap_attnseq_v0` for those). The side-obstacle course
  is not tuned in this model.
- **R range** demonstrated 0.3..1.5 m. The **curvature validator is the authority** on
  feasibility, not the model; the model only biases the proposal toward the commanded R.
- **Synthetic data only.** Never validated on a real robot or rosbag.
- **Not complete.** Pure generative; the hybrid planner remains the completeness
  guarantee on arbitrary maps.
- **GPU training is not bit-exact** run-to-run; the committed artifact reproduces the
  R-conditioning trend (checksum fixed in the manifest).

## Intended use

Research demonstration that a single costmap-conditioned generative planner can be made
**vehicle-kinematics-aware** via a context scalar, with the deterministic safety layer
extended to a curvature (turning-circle) check. Not a deployment model; the validity
layer is the authority.

## Training data

`make_costmap_path_kinematics_dataset` (400 samples): clear, off-centre / far off-centre
gap, dead-ahead gap and one-sided obstacle, each with `context = [d, R]` and a detour
whose width sets peak curvature ≈ 1/R. Deployment-matched patches
(`_resampled_aligned_patch`). Fully procedural; no real data.

## Safety

- The model has **no** validity authority; the planner validates every proposal against
  the live costmap (footprint) **and** the commanded min turn radius (curvature), and
  reports no-path if none is valid.
- Not for hardware use; no ODD validation performed.

## Reproducibility

- **Command:** `PYTHONPATH=../../generative/nav2_diffusion_training python3 export.py`
- **Seed:** 0 · **Toolchain:** torch 2.10.0+cu128, onnx 1.21.0; trained on CUDA,
  exported on CPU
- **Hyperparameters:** attnseq (dim 64 / 8 heads), `'kinematics'` dataset, 400 samples,
  2500 epochs, lr 0.004 cosine, grad-clip 1.0, best-checkpoint

## License

Model: Apache-2.0 · Data: Apache-2.0 (procedurally generated here) · Code: Apache-2.0
