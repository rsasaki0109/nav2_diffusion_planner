# nav2_diffusion_rviz_plugins

candidate trajectory visualization。

**Status: markers ノードあり（ビルド & テスト通過）。**

RViz で候補軌道・best・棄却を可視化する。「すべての候補軌道は可視化・記録できる」という Non-Negotiable Rule（[../docs/architecture.md](../docs/architecture.md) §3.4）を支える。

Ogre 依存のカスタム RViz display ではなく、**標準の MarkerArray display で表示できる markers 変換**方式を採用（堅牢でユニットテスト可能）。

## 現状の実装

- `candidate_markers.hpp`: `toMarkerArray()` — `nav2_diffusion_msgs/TrajectoryCandidates` を `visualization_msgs/MarkerArray` に変換。各候補を LINE_STRIP にし、**best=緑 / safe=青 / rejected=赤**で色分け。先頭に DELETEALL で前周期をクリア。
- `candidate_markers` ノード: `trajectory_candidates` を購読し `candidate_markers`（MarkerArray）を publish する薄い ROS グルー。
- gtest（`test/test_candidate_markers.cpp`）

### 使い方

```bash
ros2 run nav2_diffusion_rviz_plugins candidate_markers \
  --ros-args -r trajectory_candidates:=/controller_server/FollowPath/trajectory_candidates
# RViz で MarkerArray display を /candidate_markers に向ける
```

## TODO

- `nav2_diffusion_msgs/SafetyState` の状態表示（テキスト marker / panel）
- best trajectory のハイライト強調・棄却理由のテキスト付与
