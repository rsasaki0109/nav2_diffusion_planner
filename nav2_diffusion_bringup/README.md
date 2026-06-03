# nav2_diffusion_bringup

example launch/config for Nav2。

**Status: closed-loop demo の launch / params あり。**

既存 Nav2 ユーザーが **Controller を差し替えるだけ** で試せる launch / param 例を提供する。試用障壁を下げることが DX 上の勝ち筋（[../docs/architecture.md](../docs/architecture.md) §15.6）。

## 内容

| ファイル | 役割 |
|---|---|
| `params/nav2_diffusion_tb3.yaml` | nav2_bringup の `nav2_params.yaml` から **controller_server → FollowPath だけ** を `DiffusionController` に差し替えた完全な Nav2 params（他は Nav2 デフォルト） |
| `params/diffusion_controller_example.yaml` | controller_server ブロックのみの最小スニペット（ドキュメント用） |
| `launch/tb3_loopback_diffusion.launch.py` | loopback シムでの closed-loop demo |
| `launch/tb3_gazebo_diffusion.launch.py` | Gazebo での closed-loop demo |

## 実行

```bash
# loopback（軽量・GPU 不要。nav2_loopback_sim が必要）
ros2 launch nav2_diffusion_bringup tb3_loopback_diffusion.launch.py

# Gazebo（標準 demo。シム LiDAR/カメラの描画に GPU が必要）
ros2 launch nav2_diffusion_bringup tb3_gazebo_diffusion.launch.py headless:=True
```

RViz の "2D Pose Estimate" で初期姿勢を、"Nav2 Goal" でゴールを与えると、`DiffusionController` が走行する。

## 前提条件と検証状況（重要）

- **loopback demo** は `nav2_loopback_sim`（apt: `ros-<distro>-nav2-loopback-sim`）が必要。
- **Gazebo demo** はシム LiDAR/カメラのレンダリングに **動作する GPU** が必要。GPU レンダリング不可の環境では `/scan` が出ず closed-loop が成立しない。
- これらの実走行 demo に依存しない **closed-loop 検証**として、`nav2_diffusion_controller` に統合テスト（`test/test_diffusion_controller_integration.cpp`）を用意している。稼働中の `nav2_costmap_2d::Costmap2DROS` に対して実プラグインを configure/activate し、**クリア路では前進・footprint が障害物に当たる場合は stop** することを GPU/シム無しで検証する。これが現状の「動く」ことの一次保証。
