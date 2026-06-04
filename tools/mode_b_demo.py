"""Render a Mode B (global planner) demo from the real generative PathFlowPlanner.

Visualises the shipped Mode B pipeline propose -> validate -> select: the
generative path model proposes K start->goal global paths; each is checked
against the costmap obstacle (the same lethal-cell rule the C++
DiffusionGlobalPlanner uses) and the shortest collision-free one is selected. As
the obstacle sweeps across the corridor, the chosen path switches to route
around it. Colours: best = green, other safe = blue, rejected = red.

Uses the shipped ``PathFlowPlanner`` (flow matching) as the proposer; the
costmap-conditioned ``CostmapPathFlowPlanner`` plugs into the very same
PathModel seam (see nav2_diffusion_onnx::OnnxPathModel). Writes
/tmp/gifdata/mode_b_demo.gif. This renders the real model, not a mock-up.

Reproduce::

    source /opt/ros/jazzy/setup.bash
    source install/setup.bash
    pip install torch imageio matplotlib
    python3 tools/mode_b_demo.py
"""

import math

import imageio.v2 as imageio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402

from nav2_diffusion_training.path_planners import (  # noqa: E402
    make_path_dataset, PathFlowPlanner)

GOAL_D = 5.0          # goal at (5, 0)
ROBOT_R = 0.18        # collision radius [m]
OBST_X0, OBST_X1 = 2.0, 3.4   # obstacle extent ahead [m]
OBST_HALF_W = 0.30    # obstacle half-width [m]
MODEL_CACHE = '/tmp/gifdata/mode_b_model.pt'


def hits_obstacle(path, center_y):
    """True if any path point is within ROBOT_R of the obstacle rectangle."""
    for x, y in path:
        if OBST_X0 - ROBOT_R <= x <= OBST_X1 + ROBOT_R and \
                abs(y - center_y) <= OBST_HALF_W + ROBOT_R:
            return True
    return False


def path_length(path):
    return sum(math.hypot(path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1])
               for i in range(1, len(path)))


def train():
    """Train the shipped generative path model (fast MLP flow matching)."""
    import os
    torch.manual_seed(0)
    model = PathFlowPlanner(steps=4)
    if os.path.exists(MODEL_CACHE):
        model.load_state_dict(torch.load(MODEL_CACHE))
        model.eval()
        return model
    ctx, tg = make_path_dataset(64)
    opt = torch.optim.Adam(model.parameters(), lr=0.012)
    for _ in range(220):
        opt.zero_grad()
        loss = model.flow_loss(ctx, tg)
        out = model(ctx[:8])
        jerk = out[:, :, 2:, :] - 2 * out[:, :, 1:-1, :] + out[:, :, :-2, :]
        (loss + 2.0 * (jerk ** 2).mean()).backward()
        opt.step()
    model.eval()
    torch.save(model.state_dict(), MODEL_CACHE)
    return model


def render(model):
    """Sweep the obstacle and draw the proposed/validated/selected paths."""
    ctx = torch.tensor([[GOAL_D, 0.0]])
    with torch.no_grad():
        cands = model(ctx)[0].numpy()  # [K, H, 2] -- fixed proposals (context-only)
    paths = [[(float(p[0]), float(p[1])) for p in cands[k]] for k in range(cands.shape[0])]

    # Sweep the obstacle across the left and right sides (skipping the dead
    # centre band, where a single bowed path cannot reach the goal around it).
    centers = (list(np.linspace(1.2, 0.5, 6)) + list(np.linspace(-0.5, -1.2, 6)) +
               list(np.linspace(-1.2, -0.5, 6)) + list(np.linspace(0.5, 1.2, 6)))
    images = []
    for cy in centers:
        safe = [(i, p) for i, p in enumerate(paths) if not hits_obstacle(p, cy)]
        best_i = min(safe, key=lambda ip: path_length(ip[1]))[0] if safe else -1

        fig, ax = plt.subplots(figsize=(4.6, 5.2), dpi=80)
        ax.add_patch(plt.Rectangle(
            (-(cy + OBST_HALF_W), OBST_X0), 2 * OBST_HALF_W, OBST_X1 - OBST_X0,
            color='#8b1a1a', alpha=0.85, zorder=1))
        for i, p in enumerate(paths):
            xs = [pt[0] for pt in p]
            ys = [-pt[1] for pt in p]   # negate so +y (left) is on the left
            if i == best_i:
                ax.plot(ys, xs, color='#3fb950', lw=3.0, zorder=4)
            elif not hits_obstacle(p, cy):
                ax.plot(ys, xs, color='#2f81f7', lw=1.5, zorder=3)
            else:
                ax.plot(ys, xs, color='#d9534f', lw=1.2, alpha=0.7, zorder=2)
        ax.plot(0, 0, marker='o', color='#9aa7b2', markersize=9, zorder=5)
        ax.plot(0, GOAL_D, marker='*', color='#f0c000', markersize=16, zorder=5)
        ax.set_xlim(2.6, -2.6)
        ax.set_ylim(-0.3, GOAL_D + 0.3)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title('Mode B: generative global paths, costmap validates & selects\n'
                     '(best=green / safe=blue / rejected=red)', fontsize=8)
        fig.tight_layout(pad=0.3)
        fig.canvas.draw()
        w, h = fig.canvas.get_width_height()
        img = np.asarray(fig.canvas.buffer_rgba()).reshape(h, w, 4)[:, :, :3].copy()
        images.append(img)
        plt.close(fig)
    imageio.mimsave('/tmp/gifdata/mode_b_demo.gif', images, duration=0.1, loop=0)
    print('wrote /tmp/gifdata/mode_b_demo.gif frames=%d' % len(images))


if __name__ == '__main__':
    render(train())
