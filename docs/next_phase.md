# 次フェーズ実行計画（データ・環境依存の前進）

> 関連: [roadmap.md](roadmap.md) / [generative_limits.md](generative_limits.md) / [training.md](training.md) / [deployment.md](deployment.md) / [simulation.md](simulation.md)

## このノートの位置づけ

v0.8.0 までで、**純ソフトで到達できる前進はほぼ出尽くした**。

- 生成系は Mode A（trajectory）/ Mode B（path）の learned モデルが実 C++ ONNX 推論でループ稼働（[model_zoo](../model_zoo)）。
- 生成ファミリは 4 系統（flow / diffusion / consistency / **transformer**）を同一 ONNX 契約で実装。
- 天井（gap-routing / obstacle-threading）は**ハイブリッド**（fallback / guided）で実際に超える。
- DAgger 閉ループ学習基盤は動くが、小型モデル + 軽量シムでは改善 marginal（[generative_limits.md](generative_limits.md)）。

残る本質的な前進は、いずれも**実データ・実シミュレータ・GPU/エッジ実機が前提**で、ソースだけでは閉じない。本ノートはその次フェーズを「何が要るか → どの順で → 何を満たせば完了か」に落とし、roadmap の高レベル項目と生成系の道筋を**実行可能な手順**として束ねる。新しい主張ではなく、着手のための設計書である。

## 前提（このフェーズに入る条件）

| 区分 | 必要なもの | 現状 | 備考 |
|---|---|---|---|
| 計算 | 学習用 GPU（CUDA が安定して初期化できる占有環境） | ⬜ | 現環境は他ワークスペース負荷で CUDA 初期化が停滞 → 学習は CPU 実行で凌いでいる |
| シム | Gazebo / Isaac の閉ループ（Nav2 スタックを実際に走らせられる） | 部分 | launch・params はあるが実走行 numbers は未収集（[simulation.md](simulation.md)） |
| データ | rosbag または sim ログ（goal・障害物・gap 配置の多様性、expert/介入ラベル） | ⬜ | 現状は合成データのみ（[training.md](training.md) の ingestion 経路は実装済み） |
| 実機 | 差し替え可能な Nav2 ロボット（shadow mode 評価用） | ⬜ | 安全層・fallback・診断は実装済みで shadow mode を載せられる |
| エッジ | Jetson（TensorRT 検証用） | ⬜ | [deployment.md](deployment.md) §11 |

> どれか 1 つでも整えば、対応する段（下記）に着手できる。全部は要らない。

## 実行順（依存の浅い順）

### 段 1 — 忠実な閉ループでの DAgger（GPU + シム）

**狙い**: 軽量 numpy シムの marginal を脱し、分布シフトを本当に潰す。

1. ロールアウトを numpy シムから **実 C++ コントローラ / Gazebo** に差し替える（`dagger.py` の `rollout` の状態遷移を sim ブリッジに置換、crop / first-segment / lookahead / dt は既に C++ と揃えてある）。
2. モデル容量を上げる（transformer エンコーダ増強、隠れ次元・層数・トークン数）。
3. β スケジュール（expert 混合率）を減衰させながら集約・再学習を反復。

**完了条件 (DoD)**: `controller_benchmark` の障害物シナリオで、fallback に頼らず learned 単体の閉ループ成功が現状（open のみ）から障害物ありへ拡張し、衝突ゼロを保つ。

### 段 2 — 大容量モデル + 多様な実/シムデータ（GPU + データ）

**狙い**: 小型 CNN/MLP の容量と合成→実の転移ギャップ（[generative_limits.md](generative_limits.md) §「なぜ天井になるか」）を埋める。

1. rosbag / sim から goal・障害物・**off-centre gap** 配置を広く収集（ingestion は [training.md](training.md) に実装済み）。
2. costmap エンコーダを増強（transformer トークン化 + 位置埋め込みは既に入っている — 段数/幅/解像度を上げる）。
3. 段 1 の DAgger と併用。

**DoD**: Mode B の off-centre gap を、ハイブリッド委譲ではなく **learned 単体**で通せる事例が出る（少なくとも 1 配置で、転移が反転しないことを `planner_comparison.md` の再サンプル patch で確認）。達成できなければ「探索が勝つ領域」という現結論を、より強い証拠付きで再確認して記録する。

### 段 3 — 実機 shadow mode（実機 + データ）

**狙い**: 安全層を効かせたまま、実走行分布で learned 提案の質を測る。

1. learned コントローラを shadow（cmd は既存プランナ、提案はログのみ）で実機に載せる。
2. 介入・棄却理由・安全状態を収集（[visualization.md](visualization.md) の診断を流用）。
3. 集めたログを段 2 のデータに還流（fleet learning の最小形）。

**DoD**: 実走行 benchmark numbers（成功率・介入率・棄却理由分布）を [model_comparison.md](model_comparison.md) に実機列として追加。

### 段 4 — TensorRT / Jetson（エッジ実機）

**狙い**: edge-GPU での実時間性を確定。

1. ONNX → TensorRT backend を `nav2_diffusion_onnx` の seam の隣に追加（既存の optional パッケージ作法を踏襲）。
2. Jetson でレイテンシ / 消費電力を計測。

**DoD**: [roadmap.md](roadmap.md) v1.0 の「x86 GPU and Jetson validated」を満たす数値を [deployment.md](deployment.md) に記録。

## 各段が触る箇所（既存資産）

| 段 | 主に触るコード | 既にある足場 |
|---|---|---|
| 1 | `nav2_diffusion_training/dagger.py`、sim ブリッジ | DAgger ループ・C++ 整合の crop/抽出 |
| 2 | `generative_planners.py`（容量）、`rosbag_io.py` / `dataset.py`（ingestion） | 4 生成ファミリ・2 入力 ONNX 契約 |
| 3 | shadow mode launch、診断 | 安全層・fallback・RViz/Foxglove |
| 4 | `nav2_diffusion_onnx`（TensorRT backend） | optional backend 作法・ONNX 契約 |

## 何をしないか（スコープ外）

- 合成データのさらなる作り込みでの天井突破（[generative_limits.md](generative_limits.md) で転移しないと実証済み — 容量と実データが本筋）。
- classical planner/controller の網羅追加（一区切り済み）。
- 安全認証（本リポジトリは研究/評価用、[safety.md](safety.md)）。

## まとめ

次の前進は「もっとコードを書く」ではなく「**GPU・シム・実データ・実機のどれかを 1 つ用意し、上の段に着手する**」こと。足場（4 生成ファミリ・2 入力 ONNX 契約・DAgger 基盤・安全層・ハイブリッド・比較ベンチ）は揃っている。どれか整い次第、対応する段から始められる。
