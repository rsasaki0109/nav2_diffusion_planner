# Model Card: diffusion_global_costmap_kinematics_v0

> A **kinematics-conditioned** generative Mode B path model: one network, conditioned
> on the vehicle's **min turn radius R** (the second context input, `R=0` = omni), proposes
> a *sharp* detour for an omni / differential-drive robot and a *gentle* one for an
> Ackermann car through the same gap — and the planner's curvature validator *disposes* of
> any proposal that turns tighter than the vehicle can. Trained across **all eight benchmark
> courses** (slalom for omni only). Manifest: [manifest.yaml](manifest.yaml).
> Reproduce: [export.py](export.py). Architecture sibling (8/8 all-course):
> [../diffusion_global_attnseq/model_card.md](../diffusion_global_attnseq/model_card.md).

## Summary

- **Model family:** attnseq (no-fan cross-attention autoregressive), conditioned on R
- **Task:** vehicle-kinematics-aware global **path** proposal for Nav2 **Mode B**
- **Inputs:** goal-aligned costmap patch (24×24) + **[goal distance, min turn radius R]** (`R=0` = omni)
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

**Result (real C++ `planner_benchmark`, all 8 courses, pure generative):**

| course | omni (R=0) | diff-drive (R=0.3) | Ackermann (R=1.5) |
|---|:-:|:-:|:-:|
| clear / centred gap / double gate | yes | yes | yes |
| narrow gap | yes | yes | **no path** |
| **off-centre / far off-centre gap** | yes | **yes** | **no path** |
| **side obstacle** | yes | yes | **no path** |
| **slalom** | yes | **yes** | **no path** |
| **total** | **8/8** | **8/8** | **3/8** |

One model, three vehicles, the *same weights* — only the R input and the curvature gate
differ. **omni** (R=0, gate off) threads all eight courses including the S-shaped slalom.
**diff** (R=0.3, gate 1/R=3.33) threads all eight too: its sharp turning circle clears
every lateral maneuver, and the benchmark slalom's coarse 12-pose S stays under its gate.
**Ackermann** (R=1.5, gate 1/R=0.67) threads only the near-straight courses; the curvature
validator disposes every course needing a real lateral move — *narrow gap* (a ~1.5 aim
correction into the tight slot), *off-centre* / *far gap* (a 2 m jog in ~1 m of travel),
*side obstacle* (a ~2.2 bow), and *slalom* — all past a 1.5 m turning circle. The peak
output curvature is **monotonic** in the commanded R (omni/diff sharp > Ackermann gentle),
measured on the exported ONNX. The slalom-S proposal for omni is trained directly; diff /
Ackermann inherit it but the gate decides feasibility.

## Honest scope — what it does NOT do

- **All-course demonstration model.** Covers all eight benchmark courses conditioned on
  R. **Slalom is feasible — and trained — for omni (R=0) only:** the benchmark slalom's
  ±2 m crossings in a ~1.6 m gap need curvature ~1/0.02 m, far past any wheeled turning
  circle, so the curvature validator correctly disposes the slalom proposal for diff /
  Ackermann (a single all-course pure-generative model with no kinematic gate is
  `diffusion_global_costmap_attnseq_v0`).
- **R range** demonstrated 0.0 (omni) .. 1.5 m. The **curvature validator is the authority**
  on feasibility, not the model; the model only biases the proposal toward the commanded R.
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

`make_costmap_path_kinematics_dataset` (500 samples): all eight benchmark courses —
clear / centred / double gate (straight, R-invariant), off-centre / far off-centre gap
and one-sided side obstacle (R-shaped detour whose width sets peak curvature ≈ 1/R), and
an **omni-only slalom block** (R=0). `context = [d, R]` with `R=0` = omni. The *clear*
straight expert spans goal distances 4.0–5.8 m to match the benchmark's off-axis diagonal
(so a small-R proposal does not extrapolate spurious curvature on the empty map).
Deployment-matched patches (`_resampled_aligned_patch`). Fully procedural; no real data.

## Safety

- The model has **no** validity authority; the planner validates every proposal against
  the live costmap (footprint) **and** the commanded min turn radius (curvature), and
  reports no-path if none is valid.
- Not for hardware use; no ODD validation performed.

## Reproducibility

- **Command:** `PYTHONPATH=../../generative/nav2_diffusion_training python3 export.py`
- **Seed:** 0 · **Toolchain:** torch 2.10.0+cu128, onnx 1.21.0; trained on CUDA,
  exported on CPU
- **Hyperparameters:** attnseq (dim 64 / 8 heads), `'kinematics'` dataset (all courses +
  omni), 500 samples, 3500 epochs, lr 0.004 cosine, grad-clip 1.0, best-checkpoint

## License

Model: Apache-2.0 · Data: Apache-2.0 (procedurally generated here) · Code: Apache-2.0
