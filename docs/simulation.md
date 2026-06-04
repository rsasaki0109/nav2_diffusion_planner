# Simulation Strategy

> 関連: [training.md](training.md) §6.2 Data Sources、[benchmarking.md](benchmarking.md)、[deployment.md](deployment.md)

## 10.1 Simulation Stack

| Simulator | 役割 |
|---|---|
| Gazebo / ros-gz | CI、軽量テスト、Nav2 標準 demo |
| Isaac Sim | photoreal, RGB/depth, warehouse, domain randomization |
| rosbag Replay | 実機ログ再評価 |
| Loopback / Mock Sim | unit-level regression, latency tests |
| Hardware-in-the-loop | deployment 前 validation |

Nav2 Getting Started は、Gazebo simulator 上の TurtleBot3 navigation から開始する流れを提供しているため、OSS の最初の demo は Nav2 標準導線に合わせるべきである。

## 10.2 Golden Scenarios

GitHub 公開時に最低限必要な scenario。

| Scenario | 目的 |
|---|---|
| simple_corridor | install 確認 |
| narrow_doorway | 狭路性能 |
| dynamic_crossing | 動的障害物 |
| u_trap | local minima |
| warehouse_shelves | AMR 用途 |
| crowded_hallway | human-aware preview |
| sensor_dropout | robustness |
| gpu_timeout | fallback 確認 |

## 10.3 Simulation-to-Benchmark Pipeline

| Stage | 内容 |
|---|---|
| Scenario Definition | map, robot, obstacles, dynamic agents, seed |
| Run Configuration | planner/controller/model/backend |
| Execution | headless simulation |
| Recording | rosbag, metrics, trace, RViz markers |
| Evaluation | metrics extraction |
| Report | markdown/html summary |
| Regression Gate | pass/fail |

## 10.4 Isaac Sim Role

Isaac Sim は v0.1 必須ではない。v0.1 は Gazebo と rosbag replay で十分に価値を出す。Isaac Sim は v0.5 以降、以下で使う。

- RGB / depth / semantic camera training
- warehouse scene diversity
- sensor realism
- domain randomization
- synthetic dynamic humans / forklifts
- edge GPU deployment rehearsal

## 10.5 実走検証: headless bring-up と既知の制約

> 関連: [next_phase.md](next_phase.md) 段3。2026-06-05 に `tb3_gazebo_diffusion.launch.py`
> を実際に headless 起動して確認した結果。**正直なスコープ**: sim は立ち上がるが、
> このセッションのサンドボックスでは**完全自動の閉ループ数値ベンチは完走できない**。

### 動いたこと（検証済み）

`ros2 launch nav2_diffusion_bringup tb3_gazebo_diffusion.launch.py use_rviz:=False
headless:=True`（`TURTLEBOT3_MODEL=waffle`）で:

- **Gazebo（gz, Jazzy）が headless で起動**し、`nav2_minimal_tb3_sim` の `tb3_sandbox`
  ワールドに TB3 waffle を spawn（"Entity creation successful"）。
- **GPU LiDAR が実際にレンダリングされて publish**: `gz topic -e -t /scan` で
  `count: 360`, `range_max: 20` を確認。起動ログに
  `libEGL warning: ... failed to create dri2 screen` が出るが**非致命**（ray センサは
  描画され /scan は出る）。
- **ros_gz bridge が稼働**: `/clock`, `/odom`, `/scan`, `/tf`, `/imu`（GZ→ROS）と
  `cmd_vel`（ROS→GZ）を生成。
- **Nav2 スタックがロード**（`nav2_container` に controller_server / planner_server /
  costmaps / BT / collision_monitor / docking 等）。`FollowPath` は
  `nav2_diffusion_controller::DiffusionController` を指す（[params](../nav2_diffusion_bringup/params/nav2_diffusion_tb3.yaml)）。
  Mode A 学習モデルを使うには `FollowPath` に `model_plugin:
  nav2_diffusion_onnx::OnnxTrajectoryModel` ＋ `model_path`（[model_zoo](../model_zoo)）＋
  `costmap_patch_size: 32` を足す。

### 完走をブロックしたこと（このサンドボックス固有）

1. **localization 未確立**: 初期姿勢を与えないと AMCL が map→odom を出さず、
   `global_costmap` が "transform base_link→map did not become available" で
   activate 失敗。通常は RViz の 2D Pose Estimate か `/initialpose` への publish が要る。
2. **DDS が外部プロセスを受け付けない**:
   - Fast DDS（既定）: `/dev/shm` の `open_and_lock_file failed`（SHM transport ロック
     失敗）。同一 launch 内のノード同士は UDP fallback で動くが、**後から起動する外部
     CLI（`ros2 topic list/echo`, goal 送信）が DDS グラフに join できず全てタイムアウト**。
   - CycloneDDS（`RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`, `ROS_LOCALHOST_ONLY=1`）:
     `Failed to find a free participant index for domain 0` で participant 生成自体が失敗。
   - → **外部スクリプトから goal 投入・odom 記録・成功判定ができない**ため、自動の
     閉ループ数値ベンチはこの環境では完走不可。

### 完走に必要なもの（next_phase.md 段3 へ）

- **DDS が通る実 ROS ホスト**（`/dev/shm` 制限のないネイティブ環境）、または
- **すべてを 1 つの launch に内包**する方式: sim + Nav2 ＋「初期姿勢を publish →
  `NavigateToPose` を送る → `/odom` を購読して成功率/経路長/時間を集計し結果ファイルへ
  書き出す」**mission ノード**を launch 内で起動（外部 discovery に依存しない）。
  intra-launch 通信は本環境でも動くため、これが現実的な実装路。
- map_server に TB3 マップ、初期姿勢の自動設定。

結論: **bring-up と GPU センサ描画は本物で動く**ことを実走で確認済み。残りは
「初期姿勢＋mission ノード＋DDS の通る環境」であり、コードの不足ではなく**実行環境と
未実装の mission ハーネス**が律速。番号（実走 numbers）はそれが揃ってから
[model_comparison.md](model_comparison.md) / [controller_comparison.md](controller_comparison.md)
に実機/実 sim 列として追加する。
