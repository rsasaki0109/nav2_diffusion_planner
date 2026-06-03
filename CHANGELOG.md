# Changelog

All notable changes to this project are documented here. The project aims to
follow [Semantic Versioning](https://semver.org/); APIs are not yet stable
before 1.0.0 (see [docs/roadmap.md](docs/roadmap.md)).

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

[0.1.0]: https://github.com/rsasaki0109/nav2_diffusion_planner/releases/tag/v0.1.0
