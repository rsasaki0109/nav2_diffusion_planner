# Contributing

> 関連: [architecture.md](architecture.md) §5 Plugin Architecture / §12 Repository、[benchmarking.md](benchmarking.md)、[safety.md](safety.md)

歓迎します。このOSSは「研究デモ」ではなく「実運用OSS」を目指しているため、コードだけでなく **再現性・安全・ベンチマーク** を伴う貢献を重視します。

## 開発環境

- ROS 2 Jazzy + colcon
- ビルド: `colcon build`
- テスト（gtest + ament lint）: `colcon test && colcon test-result --all`
- すべての C++ は ament lint（copyright / cpplint / uncrustify / lint_cmake / xmllint）を通すこと。CI（`.github/workflows/ci.yml`）でも検証されます。

## コーディング規約

- 周囲のコードに合わせる（命名・コメント密度・イディオム）。
- C++ は 2-space インデント、各ファイルに Apache-2.0 ヘッダ。
- ランタイムパッケージに重い Python 学習依存を持ち込まない（[architecture.md](architecture.md) §12.2）。

## モデルを追加する（Generative Model Plugin）

新しい生成モデルは `nav2_diffusion_core::TrajectoryModel` interface（§5.2）の裏に実装します。追加時は**本体だけでなく以下を必ず提出**してください（§5.5 Extension Rule）。

1. model manifest（[../nav2_diffusion_models/manifests/example_diffusion_local.yaml](../nav2_diffusion_models/manifests/example_diffusion_local.yaml) 参照、§5.4 全フィールド）
2. model card（[../nav2_diffusion_models/model_card_template.md](../nav2_diffusion_models/model_card_template.md)）
3. 最小 demo
4. benchmark 結果（MPPI/RPP と同一 scenario）
5. latency 結果（p95/p99）
6. safety gate 通過率
7. 失敗例（良くない例も公開する）
8. license 情報（model / data / code 分離）

benchmark 未通過のモデルは Model Zoo に入りません（§3.4）。

## Safety Filter / Scorer / Fallback を追加する

- Safety Filter は決定論的・GPU 非依存（[safety.md](safety.md) §8.1）。`nav2_diffusion_safety::SafetyFilter` を実装。
- Scorer は soft preference のみ（安全は別層）。`nav2_diffusion_core` の scoring を参照。
- いずれも costmap / 合成データでユニットテストを付けること。

## Benchmark を追加する

- scenario・metrics は再現可能に（seed 固定、[benchmarking.md](benchmarking.md) §9.5）。
- 新 metric は `nav2_diffusion_benchmarks` にユニットテスト付きで追加。

## PR チェックリスト

- [ ] `colcon build` / `colcon test` がローカルで通る
- [ ] 追加コードにユニットテスト
- [ ] 安全・挙動の変更は統合テストで確認
- [ ] docs / README を更新
- [ ] （モデルの場合）manifest + model card + benchmark + 失敗例

## 大きな設計変更

plugin contract / message schema / safety architecture の変更は、先に [rfcs/](../rfcs/) で提案・合意してから実装してください。
