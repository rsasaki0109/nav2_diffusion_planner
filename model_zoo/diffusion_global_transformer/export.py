#!/usr/bin/env python3
# Copyright 2026 nav2_experimental_planner contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Reproduce the curated costmap-conditioned *transformer* Mode B path model here.

This trains nav2_diffusion_training.path_planners.CostmapPathTransformerPlanner
(a DETR-style set-prediction decoder that cross-attends over tokenized costmap
patch cells) on the combined one-sided-obstacle + off-centre-gap dataset, and
exports `costmap_transformer.onnx`. Unlike the flow Mode B model in
../diffusion_global, attention over explicit costmap tokens lets this model
**route through an off-centre gap** (detour to the slot, then to the goal) — the
ceiling the flow model could not cross even when trained on the same gap data
(docs/generative_limits.md).

Trains on the GPU when available; always exports on CPU for a portable artifact.
Deterministic CPU rebuild:

    PYTHONPATH=../../nav2_diffusion_training CUDA_VISIBLE_DEVICES= python3 export.py

Mode B PathModel ONNX contract (consumed by nav2_diffusion_onnx::OnnxPathModel):

    context [1, 2] = [goal_distance, 0]
    costmap [1, 1, 24, 24]            (goal-aligned patch; row -> fwd x, col -> +y)
    ->  paths [1, 5, 12, 2]           (x, y in the goal-aligned frame)
"""

import os

from nav2_diffusion_training.path_planners import train_and_export_costmap_path

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'costmap_transformer.onnx')

# Curated hyperparameters. recon_loss is a direct MSE onto the smooth routing
# expert, plus a jerk penalty, so paths stay smooth without flow-step tuning. The
# 'both' dataset mixes one-sided obstacles (pick the free side) and off-centre
# gaps (route through the slot) so the model handles both. Documented in
# model_card.md.
NUM_SAMPLES = 192
EPOCHS = 3000
LR = 0.01
DEVICE = 'cuda' if torch.cuda.is_available() else None

if __name__ == '__main__':
    loss = train_and_export_costmap_path(
        OUT, num_samples=NUM_SAMPLES, epochs=EPOCHS, lr=LR,
        kind='transformer', dataset='both', device=DEVICE)
    sidecar = OUT + '.data'
    if os.path.exists(sidecar):
        os.remove(sidecar)
    print('exported %s on %s (final loss %.4f, %d bytes)' % (
        OUT, DEVICE or 'cpu', loss, os.path.getsize(OUT)))
