# Changelog

All notable changes to this project are documented here. The project aims to
follow [Semantic Versioning](https://semver.org/); APIs are not yet stable
before 1.0.0 (see [docs/roadmap.md](docs/roadmap.md)).

## [0.2.0] - 2026-06-03

Theme: **learned models, end to end.** A real ONNX inference backend behind the
plugin seam, a training pipeline that produces models for it, richer
visualization, and a fuller benchmark suite.

### Added

- **`nav2_diffusion_onnx`** (optional): `OnnxTrajectoryModel` implementing
  `TrajectoryModel` via ONNX Runtime (§5.2/§7.2), exported as a pluginlib plugin.
  Builds only when onnxruntime is found; otherwise builds empty so a plain
  `colcon build` never fails.
- **Controller model plugin loading**: `TrajectoryModel::configure()` plus
  `model_plugin` / `model_path` params let `DiffusionController` load a learned
  model (e.g. ONNX) at runtime via pluginlib, without the controller or core
  linking any inference library. Default stays the built-in `FanRolloutModel`.
- **Training pipeline** (`nav2_diffusion_training`): `build_samples` (base-frame
  future-trajectory labels), `track_from_bag` (rosbag ingestion),
  `unicycle_to_goal` (rule-based expert), and `train`/`train_and_export` (PyTorch
  → ONNX) matching the backend I/O contract. The expert→dataset→train→export→
  backend round trip is verified by tests.
- **RViz visualization** (`nav2_diffusion_rviz_plugins`): candidate markers
  (best/safe/rejected, best highlighted, rejection-reason text) and a SafetyState
  text marker; wired into the demo launches.
- **Benchmark suite** (`nav2_diffusion_benchmarks`): task/safety/smoothness
  metrics, safety-first composite score, leaderboard, per-controller aggregation,
  YAML scenario definitions, and a `benchmark_runner` node (§9.3–9.6).

### Changed

- Controller proposal stage now goes through the `TrajectoryModel` seam
  (`FanRolloutModel` built in) and extracts cmd_vel from the best trajectory.

### Verification

- ROS 2 Jazzy: `colcon build`/`colcon test` across all packages, 0 failures
  (370+ tests incl. gtest, pytest, and ament lints; the ONNX backend built
  against onnxruntime 1.24.2 and the training round trip both pass locally).

## [0.1.0] - 2026-06-03

First tagged milestone: **Nav2-native generative local controller** with a
deterministic safety layer and a benchmark suite. Matches the v0.1 theme
"costmap-conditioned generative local controller" in the roadmap.

### Added

- **Architecture docs** (`docs/`): architecture, safety, training, benchmarking,
  simulation, deployment, roadmap, risks, getting_started, contributing,
  model_zoo.
- **`nav2_diffusion_msgs`**: `TrajectoryCandidate`, `TrajectoryCandidates`, and
  `SafetyState` message contracts (architecture §4.3/§4.4, safety §8.3).
- **`nav2_diffusion_core`**: time-indexed SE(2) `Trajectory` types, a
  `TrajectoryScorer` (progress + smoothness), and the `TrajectoryModel` plugin
  seam (§5.2) with a built-in `FanRolloutModel` placeholder for learned models.
- **`nav2_diffusion_safety`**: deterministic, GPU-independent safety filters —
  `KinematicLimitsFilter` and costmap-based `FootprintCollisionFilter` (§8.2).
- **`nav2_diffusion_controller`**: a `nav2_core::Controller` plugin
  (`DiffusionController`) implementing the propose → input-validity → safety gate
  → score → extract pipeline (Mode A), with stale-data runtime gating (§7.4) and
  delegation to a configurable fallback controller (MPPI/RPP) when no safe
  candidate exists (§8.4). Loads in Nav2 alongside MPPI/RPP.
- **`nav2_diffusion_bringup`**: full Nav2 params (FollowPath → DiffusionController
  swap) plus loopback and Gazebo closed-loop demo launches.
- **`nav2_diffusion_benchmarks`**: task / safety / smoothness metrics, a
  safety-first composite score and Markdown leaderboard (§9.4–9.6), a Markdown
  report, and a `benchmark_runner` node with a unit-tested `RunRecorder`.
- **OSS scaffolding**: Apache-2.0 license, GitHub Actions CI (build + test across
  all packages on ROS 2 Jazzy), model manifest and model-card templates, issue /
  PR templates, and an RFC template.

### Verification

- ROS 2 Jazzy: `colcon build` of all six packages succeeds; `colcon test`
  reports 0 errors / 0 failures across gtest plus the ament lints.
- The controller's closed-loop behavior (drive-forward, stop-on-collision,
  stop-on-stale-pose, multimodal turn selection, fallback delegation) is covered
  by integration tests against a live `Costmap2DROS`, without Gazebo/GPU.

### Known limitations

- The generative model is the analytic `FanRolloutModel` placeholder; no learned
  model is included yet. ONNX/TensorRT backends will plug in behind
  `TrajectoryModel` in a later release.
- Live Gazebo closed-loop and the benchmark runner's cross-process service
  round-trip were not validated in the development sandbox (no GPU rendering for
  simulated LiDAR; DDS discovery flakiness). The underlying logic is unit-tested.
- This is not a safety-certified product; see [docs/safety.md](docs/safety.md).

[0.2.0]: https://github.com/rsasaki0109/nav2_diffusion_planner/releases/tag/v0.2.0
[0.1.0]: https://github.com/rsasaki0109/nav2_diffusion_planner/releases/tag/v0.1.0
