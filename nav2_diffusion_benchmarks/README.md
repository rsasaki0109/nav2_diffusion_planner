# nav2_diffusion_benchmarks

scenarios, metrics, reports。

**Status: metrics ライブラリあり（ビルド & テスト通過）。scenario/harness は未実装。**

MPPI / RPP / Smac / DWB と公正に比較できる再現可能な benchmark suite（[../docs/benchmarking.md](../docs/benchmarking.md)）。「評価可能な navigation framework」であるための中核（[../docs/architecture.md](../docs/architecture.md) §15.5）。

## 現状の実装

- `nav2_diffusion_benchmarks/metrics.hpp`: 実行済み軌道（time-indexed SE(2) path）+ goal から §9.4 の geometry 系 metrics を算出する `evaluateRun()` / `RunMetrics`
  - `reached_goal` / `goal_distance` / `time_to_goal` / `path_length` / `detour_ratio` / `total_turning`
  - costmap 非依存（GPU/シム不要でユニットテスト可能）
- `nav2_diffusion_benchmarks/collision_metrics.hpp`: costmap ベースの safety 系 metrics（§9.4 Safety）`evaluateCollisions()` / `CollisionMetrics`
  - `collision_count` / `collided`（footprint が障害物に当たった path pose 数）
  - `min_clearance`（robot 中心から最近傍 lethal セルまでの距離 [m]、探索半径で saturate）
- `nav2_diffusion_benchmarks/run_result.hpp`: `RunResult`（scenario/controller + metrics）
- `nav2_diffusion_benchmarks/scores.hpp`: **safety 最重視の複合スコア**（§9.6）`computeScores()` / `Scores` / `ScoreWeights`
  - `safety`（衝突で 0、それ以外は clearance/参照値）/ `progress`（未到達で 0、それ以外は 1/detour）/ `comfort`（1/(1+turning)）/ `overall`（重み正規化和、既定 safety 0.5 / progress 0.3 / comfort 0.2）
- `nav2_diffusion_benchmarks/report.hpp`: `toMarkdownTable()`（生 metrics 比較表、§9.5）と `toMarkdownLeaderboard()`（overall 降順の leaderboard、§9.6）
- gtest（`test/test_metrics.cpp`, `test/test_collision_metrics.cpp`, `test/test_scores.cpp`, `test/test_report.cpp`）

### レポート出力例

```
| Scenario | Controller | Reached | Time [s] | Path [m] | Detour | Collisions | Min clear [m] | Turning [rad] |
|---|---|---|---|---|---|---|---|---|
| narrow_doorway | DiffusionController | yes | 12.50 | 8.00 | 1.10 | 0 | 0.35 | 0.40 |
| narrow_doorway | MPPI | no | 0.00 | 0.00 | 1.00 | 2 | 2.00 | 0.00 |
```

social 系 metrics（personal-space 等）は人トラッキングのログがある場合に別途追加予定。実行を購読/rosbag から取り込み metrics を算出して本レポートを出力する **runner ノード**も今後追加予定。

この metrics は、同一 scenario で controller を差し替えて実行した結果（executed path）を入力に、MPPI/RPP/Smac と横並び比較するための土台。

## 想定する内容

- Baselines（benchmarking §9.2、default / tuned / compute-matched を分離）
- Scenario Taxonomy（benchmarking §9.3）
- Metrics（benchmarking §9.4）
- Benchmark Harness（同一 map / robot / global planner で controller だけ差し替え）
- Report 生成（markdown / html）、CI regression threshold
