# Model Card: diffusion_local_costmap_threading_v0

> The first learned **Mode A** (local controller) model in this repo to **thread obstacles
> purely generatively** (no classical fallback) in the real C++ `controller_benchmark` — it
> clears **all three** obstacle courses: the dead-ahead *frontal* block, the *side obstacle*,
> **and the *corridor*** (where it centres better than the classical VFH+/ND baselines). It is
> the costmap-token transformer **DAgger-trained on a corrected reactive dodge oracle**, run
> with the controller's **windowed footprint gate** (`safety_check_points`) and a **widened
> egocentric field of view** (`costmap_patch_resolution=0.08`). Manifest:
> [manifest.yaml](manifest.yaml). Reproduce: [export.py](export.py).

## Summary

- **Model family:** transformer set-prediction (same net as the transformer Mode A model),
  but **DAgger closed-loop trained** on a corrected oracle.
- **Task:** obstacle-threading local trajectory proposal for Nav2 **Mode A**.
- **Inputs:** egocentric costmap patch (32×32) + **[goal_x, goal_y, linear_speed, max_angular_speed]**.
- **Output:** 3 candidate trajectories × 10 SE(2) waypoints (base frame).
- **Artifact:** `costmap_threading.onnx` (reproducible from `export.py`).

## What it shows — cracking the Mode A obstacle-threading ceiling

The documented Mode A ceiling (the learned controller stalls in front of obstacles) was
diagnosed (docs/generative_limits.md) to **concrete, fixable mechanisms — not raw model
capacity**:

1. **The shipped DAgger oracle itself collided / stalled** — a 0.20 m transient bow plus an
   on-line carrot drives pure-pursuit straight into the block. The **corrected** oracle
   commits a *sustained* lateral offset to the free side (a curvature dodge held until the
   block is *passed*, so the carrot cannot snap the robot back into its side), and leaves a
   corridor's free centre-line to the carrot to centre through.
2. **The deployed full-horizon footprint gate hard-rejects a tight reactive skirt** whose
   1 m lookahead clips the block, though step-wise execution skirts it safely. The
   controller now supports a **windowed gate** (`safety_check_points`): validate only the
   leading points the robot executes before re-planning (receding-horizon; the live
   costmap is re-checked every cycle).
3. **One committed dodge beats a multimodal set.** Regressing the K candidates onto a single
   committed side (not a left+right set) is what threads: a set with both escapes lets the
   controller's progress-greedy selector flip-flop between them every cycle, cancelling the
   turn. The corrected oracle threads all six sim scenarios expert-only.
4. **A wider field of view cracks the dead-ahead block.** The 32-cell patch at the native
   0.05 m costmap resolution sees only ±0.775 m ahead, so a head-on *frontal* block is sensed
   ~0.8 m out and forces a violent late dodge the small model underfits and the progress-greedy
   selector defeats. Decoupling the patch *stride* from the costmap resolution
   (`costmap_patch_resolution=0.08`, matching `PATCH_RES` in training) widens the same 32-cell
   patch to ±1.24 m, so the block is seen ~1.6× earlier and the committed dodge is gentle
   enough to fit and survive selection.

With these, the DAgger-trained **transformer** reaches the goal **5/6 closed-loop** in the
costmap sim (the small CNN-embedding flow model cannot fit the sharp dodge — it stays at
1/4; capacity matters). The lone sim miss is a tight two-block slalom not in the benchmark.

**Result (real C++ `controller_benchmark`, `safety_check_points=3`,
`costmap_patch_resolution=0.08`, no fallback):**

| scenario | learned / transformer / recurrent | **threading** |
|---|:-:|:-:|
| open | reached | reached |
| **frontal obstacle** (dead-ahead) | timeout (~1.0 m, 0.75 m) | **reached (4.24 m, 0.48 m clearance)** |
| **side obstacle** | timeout (~1.0 m) | **reached (4.05 m traverse)** |
| **corridor** (off-centre start) | timeout | **reached (mean \|y-centre\| 0.20 m < VFH+ 0.28 / ND 0.31)** |

It is the **first learned Mode A model here to thread obstacles generatively** — all three
obstacle courses including the dead-ahead *frontal* block (the prior holdout), and it even
**centres better than the classical baselines** in the corridor.

## Honest scope — what it does NOT do

- **Threads the benchmark courses, not arbitrary scenes.** All three benchmark obstacle
  courses (frontal, side, corridor) are threaded generatively, but the model is trained on a
  narrow synthetic distribution; a tight two-block slalom (sim-only) is still a closed-loop
  miss, and on novel scenes the **hybrid (VFH+ fallback)** remains the completeness guarantee.
- **Requires** the windowed footprint gate (`safety_check_points>0`) AND the matching widened
  patch resolution (`costmap_patch_resolution=0.08`). Under the default full-horizon gate it
  is hard-rejected like the other learned models; at the native 0.05 m patch it stalls on the
  frontal block (the field of view is too narrow to commit a gentle dodge in time).
- **Synthetic data only.** Never validated on a real robot or rosbag.
- **Research / demonstration model.** Do not deploy on hardware; the safety layer is the authority.

## Reproducibility

- **Command:** `PYTHONPATH=../../generative/nav2_diffusion_training python3 export.py`
- **Seed:** 0 · **Toolchain:** torch 2.10.0+cu128, onnx 1.21.0; trained on CUDA, exported on CPU.
- **Hyperparameters:** `CostmapTransformerPlanner`; DAgger iters 8, base 320, epochs 900,
  lr 0.003 cosine, grad-clip 1.0, best-checkpoint; `SAFETY_WINDOW` 3, `PATCH_RES` 0.08 m
  (the controller must run with the matching `costmap_patch_resolution=0.08`).
- DAgger + GPU training is not bit-exact run-to-run; the checksum is fixed in the manifest
  and a re-export reproduces the threading behaviour.

## License

Model: Apache-2.0 · Data: Apache-2.0 (procedurally generated) · Code: Apache-2.0
