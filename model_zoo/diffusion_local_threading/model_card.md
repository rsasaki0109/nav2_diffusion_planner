# Model Card: diffusion_local_costmap_threading_v0

> The first learned **Mode A** (local controller) model in this repo to **thread obstacles
> purely generatively** (no classical fallback) in the real C++ `controller_benchmark` — it
> clears the *side obstacle* **and the *corridor*** (where it centres better than the
> classical VFH+/ND baselines). It is the costmap-token transformer **DAgger-trained on a
> corrected reactive dodge oracle**, run with the controller's **windowed footprint gate**
> (`safety_check_points`). Manifest: [manifest.yaml](manifest.yaml). Reproduce:
> [export.py](export.py).

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

With these, the DAgger-trained **transformer** reaches the goal **4/6 closed-loop** in the
costmap sim (the small CNN-embedding flow model cannot fit the sharp dodge — it stays at
1/4; capacity matters).

**Result (real C++ `controller_benchmark`, `safety_check_points=3`, no fallback):**

| scenario | learned / transformer / recurrent | **threading** |
|---|:-:|:-:|
| open | reached | reached |
| **side obstacle** | timeout (~1.0 m) | **reached (4.25 m traverse)** |
| **corridor** (off-centre start) | timeout | **reached (mean \|y-centre\| 0.24 m < VFH+ 0.28 / ND 0.31)** |
| frontal obstacle (dead-ahead) | timeout (~1.0 m, 0.75 m) | timeout (1.66 m, **0.21 m** clearance) |

It is the **first learned Mode A model here to thread obstacles generatively** — the side
obstacle and the corridor, which it even **centres better than the classical baselines**.
On the dead-ahead *frontal* block it drives markedly further and closer but does not
complete (see scope below).

## Honest scope — what it does NOT do

- **Not a full solve.** Threads the *side obstacle* and the *corridor* generatively, but the
  dead-ahead *frontal* block still times out. The reactive oracle threads it *expert-only*,
  so the gap is real but specific: the controller's deterministic progress-greedy selector
  defeats the symmetric left/right dodge, and the small model underfits the hardest head-on,
  late-sensed commit (the block is seen only ~0.8 m ahead in the 32-cell patch). The
  **hybrid (VFH+ fallback)** remains the all-scenario guarantee.
- **Requires** the windowed footprint gate (`safety_check_points>0`). Under the default
  full-horizon gate it is hard-rejected like the other learned models.
- **Synthetic data only.** Never validated on a real robot or rosbag.
- **Research / demonstration model.** Do not deploy on hardware; the safety layer is the authority.

## Reproducibility

- **Command:** `PYTHONPATH=../../generative/nav2_diffusion_training python3 export.py`
- **Seed:** 0 · **Toolchain:** torch 2.10.0+cu128, onnx 1.21.0; trained on CUDA, exported on CPU.
- **Hyperparameters:** `CostmapTransformerPlanner`; DAgger iters 8, base 320, epochs 900,
  lr 0.003 cosine, grad-clip 1.0, best-checkpoint; `SAFETY_WINDOW` 3.
- DAgger + GPU training is not bit-exact run-to-run; the checksum is fixed in the manifest
  and a re-export reproduces the threading behaviour.

## License

Model: Apache-2.0 · Data: Apache-2.0 (procedurally generated) · Code: Apache-2.0
