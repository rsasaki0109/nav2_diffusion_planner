# nav2_diffusion_models

model manifest examples and lightweight test models。

**Status: 未実装（スケルトン）。**

CI とサンプル用の軽量モデルと、model manifest の例を置く。大きなバイナリは置かない（[../.gitignore](../.gitignore) でモデル拡張子を除外し、配布は release asset / model registry 経由 — [../docs/deployment.md](../docs/deployment.md) §11.4）。

## 内容

- `manifests/example_diffusion_local.yaml`: Model Manifest の例（[../docs/architecture.md](../docs/architecture.md) §5.4 の全 field）
- `model_card_template.md`: model card テンプレート（§5.5 Extension Rule）
- （TODO）shape / checksum 検証用の tiny test model

Model Zoo 一覧は [../docs/model_zoo.md](../docs/model_zoo.md) を参照。

## ルール

Model Zoo / 同梱モデルは **benchmark 通過済み** でなければならない（architecture §3.4）。
