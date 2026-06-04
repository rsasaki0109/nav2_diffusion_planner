# Model Card: diffusion_local_costmap_flow_v0

> The curated generative **local controller** (Mode A) model — the repo's headline
> "learned models propose trajectories" mode, now running end-to-end through the
> C++ inference path. Manifest: [manifest.yaml](manifest.yaml). Reproduce:
> [export.py](export.py). See also the Mode B sibling
> [../diffusion_global/model_card.md](../diffusion_global/model_card.md).

## Summary

- **Model family:** flow matching (conditional, 2 Euler integration steps)
- **Task:** local **trajectory** proposal for the Nav2 **Mode A** controller
  (`nav2_diffusion_controller::DiffusionController` →
  `nav2_diffusion_onnx::OnnxTrajectoryModel`)
- **Robot kinematics:** differential drive (unicycle)
- **Inputs:** egocentric local-costmap patch (32×32) + carrot (base frame) + speed limits
- **Output:** 3 candidate base-frame SE(2) trajectories × 10 steps (~1 s), gated and
  scored by the controller's deterministic safety layer
- **Runtime / precision:** ONNX / fp32
- **Artifact:** `costmap_flow.onnx` (≈268 KB), checked in directly (small, fully
  reproducible from `export.py`).

## Intended use

Demonstration / research. It proves the *propose → safety-gate → score → cmd_vel*
controller architecture with a real learned proposer: the model reads the
egocentric costmap and biases **every** candidate away from a one-sided obstacle,
the deterministic kinematic + footprint filters reject unsafe candidates, and the
scorer picks the most direct safe one. In closed loop the small per-step lateral
bias accumulates into avoidance. The built-in analytic `FanRolloutModel` (a
constant-curvature fan blind to the costmap) cannot do this.

## Out-of-scope / limitations

Honest and load-bearing:

- **Synthetic data only.** Never validated on a real robot or rosbag.
- **One-sided obstacles only.** A symmetric head-on block is ambiguous (the model
  never saw a centred obstacle); breaking that symmetry is a reactive-controller
  job (see VFH+/ND). The catalog benchmark uses a *side obstacle* scenario that
  matches this competence.
- **Short, gentle.** ~1 s / ~0.3 m horizon with ~0.2 m lateral veer; it leans on
  closed-loop replanning rather than one big swerve.
- **Small research model.** It drives closed-loop but does not reliably reach the
  goal box or complete obstacle scenarios in `controller_benchmark` — mature
  reactive controllers (VFH+/ND) do. The architecture and inference are sound (the
  C++ test passes); the *model* needs better training data / capacity to be a usable
  controller.
- **Carrot distribution.** Trained on carrots ~0.9–1.1 m ahead with bearing ±0.3 rad;
  larger off-axis carrots are out of distribution.
- **No safety authority.** The kinematic + footprint filters gate every proposal;
  if none is safe the controller falls back or stops. Do not deploy on hardware.

## Training data

`nav2_diffusion_training.generative_planners.make_costmap_dataset` (240 samples).
Each configuration places a one-sided obstacle band on the +y (low cols, matching
`cropEgocentricPatch`) or −y side of the 32×32 egocentric patch, with **varied
row-band and column width**, emitted as a **mirrored +y/−y pair** (symmetric, no
lateral bias), plus **clear (no-obstacle)** samples. The carrot (context
goal_x/goal_y) is **varied in distance (~0.9–1.1 m) and bearing (±0.3 rad)** so the
controller stays in distribution as its heading drifts; the expert heads toward the
carrot (`_expert_trajectory`) with a half-sine lateral bow away from the obstacle
and a path-tangent yaw. Fully procedural; no real data.

## Benchmark results

Research placeholder → checked **behaviourally**, not against the full Nav2
deployment benchmark:

- **Costmap side-selection (end-to-end C++):** obstacle on the left → all 3
  candidates veer right (mean lateral < 0); obstacle on the right → all veer left;
  no obstacle → centred. Asserted in `nav2_diffusion_onnx`'s
  `test_onnx_trajectory_model` (`CuratedZooModelVeersAwayFromObstacle`, runs where
  onnxruntime is available).
- **Closed-loop catalog comparison:** appears as *Diffusion (Mode A, learned)* in
  [docs/controller_comparison.md](../../docs/controller_comparison.md). It drives
  closed-loop — traversing most of the *open* corridor — but, as a small research
  model, does **not** reliably reach the goal box or complete the obstacle
  scenarios (it times out where VFH+/ND reach). It is included to show a learned
  controller running in the same harness; the architecture is sound, the model is
  the limitation.
- **Collisions:** gated by the deterministic kinematic + footprint safety layer; a
  candidate entering the footprint is rejected regardless of model quality (0
  collisions in the benchmark).

## Safety

- The model has **no** safety authority. Every proposal passes the kinematic and
  footprint filters; if none is safe the controller delegates to its
  `fallback_controller_plugin` (e.g. MPPI/RPP) or stops — never an unsafe command.
- Failure mode: a head-on symmetric block (out of distribution) → it may fail to
  pick a side; the safety layer still prevents collision (stop / fallback).
- Not for hardware use; no ODD validation performed.

## Reproducibility

- **Command:** `PYTHONPATH=../../nav2_diffusion_training CUDA_VISIBLE_DEVICES= python3 export.py`
- **Seed:** 0 (`torch.manual_seed(0)` inside the training function)
- **Toolchain:** torch 2.10.0+cu128, onnx 1.21.0, exported on CPU
- **Hyperparameters:** flow, 240 samples, 1500 epochs, lr 0.01, 4 flow steps,
  sample_weight 30 (direct MSE to the smooth expert, so per-step speeds stay
  within the kinematic gate)
- Bit-for-bit reproduction may vary across torch versions / hardware; behaviour
  (side-selection, veer magnitude) is stable.

## License

Model: Apache-2.0 · Data: Apache-2.0 (procedurally generated here) · Code: Apache-2.0
