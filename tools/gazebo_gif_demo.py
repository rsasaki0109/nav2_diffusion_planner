#!/usr/bin/env python3
# Copyright 2026 Nav2PlannerBattle contributors
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
Record README GIFs from real Gazebo Sim course worlds.

Loads each ``nav2_diffusion_sim`` course in gz-sim (TB3 waffle + overhead camera),
animates the robot along a footprint-valid A* route on the course occupancy grid, and
writes GIFs. This replaces the matplotlib stand-ins in ``battle_gif_demo.py`` and
``gazebo_courses_demo.py`` for README visuals.

Requirements: ROS 2 Jazzy, Gazebo Sim, ``ros_gz_image``, TB3 models on
``GZ_SIM_RESOURCE_PATH``.

Usage::

    PYTHONPATH=generative/nav2_diffusion_sim python3 tools/gazebo_gif_demo.py
    # writes docs/battle_race.gif, battle_maze.gif, battle_duel.gif, sim_courses.gif
"""

from __future__ import annotations

import argparse
import atexit
import math
import os
import subprocess
import sys
import time

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, '..', 'docs')
PKG = os.path.join(HERE, '..', 'generative', 'nav2_diffusion_sim')
ROS_SETUP = '/opt/ros/jazzy/setup.bash'
sys.path.insert(0, PKG)


def _ensure_ros_env():
    """Load ROS 2 paths so ``rclpy`` / ``ros_gz_image`` work outside a sourced shell."""
    if not os.path.isfile(ROS_SETUP):
        return
    env = subprocess.check_output(
        ['bash', '-c', 'source {} && env'.format(ROS_SETUP)], text=True)
    for line in env.splitlines():
        if '=' not in line:
            continue
        key, _, val = line.partition('=')
        if key in ('PYTHONPATH', 'LD_LIBRARY_PATH', 'PATH', 'AMENT_PREFIX_PATH',
                   'ROS_DISTRO', 'ROS_VERSION'):
            os.environ[key] = val
    ros_py = '/opt/ros/jazzy/lib/python3.12/site-packages'
    if ros_py not in sys.path:
        sys.path.insert(0, ros_py)

from nav2_diffusion_sim import gen_courses  # noqa: E402
import gazebo_courses_demo as grid_demo  # noqa: E402

TB3_SDF = '/opt/ros/jazzy/share/turtlebot3_gazebo/models/turtlebot3_waffle/model.sdf'
CAM_W = CAM_H = 640
FRAME_STEPS = 24
POSE_SETTLE_SEC = 0.35
SIM_WARMUP_SEC = 9.0

# README outputs: (gif filename, course, overlay title)
README_JOBS = [
    ('battle_race.gif', 'gap', 'Mode A course · gap (Gazebo)'),
    ('battle_maze.gif', 'micro_mouse_easy', 'Micro-mouse easy (Gazebo)'),
    ('battle_duel.gif', 'slalom', 'Mode B course · slalom (Gazebo)'),
]

SIM_COURSES_ORDER = list(grid_demo.ORDER)


def _tb3_resource_path():
    base = '/opt/ros/jazzy/share/turtlebot3_gazebo/models'
    return base if os.path.isdir(base) else ''


def _camera_block(cx, cy, height):
    fov = 1.05 if height < 16 else 0.95
    return (
        '    <model name="overhead_camera">\n'
        '      <static>true</static>\n'
        '      <pose>{cx} {cy} {cz} 0 1.57079632679 0</pose>\n'
        '      <link name="link">\n'
        '        <sensor name="camera" type="camera">\n'
        '          <camera>\n'
        '            <horizontal_fov>{fov}</horizontal_fov>\n'
        '            <image><width>{w}</width><height>{h}</height>'
        '<format>R8G8B8</format></image>\n'
        '            <clip><near>0.1</near><far>80</far></clip>\n'
        '          </camera>\n'
        '          <always_on>1</always_on>\n'
        '          <update_rate>12</update_rate>\n'
        '          <visualize>false</visualize>\n'
        '          <topic>overhead/image</topic>\n'
        '        </sensor>\n'
        '      </link>\n'
        '    </model>\n'
    ).format(cx=cx, cy=cy, cz=height, fov=fov, w=CAM_W, h=CAM_H)


def _goal_marker(gx, gy):
    return (
        '    <model name="goal_marker">\n'
        '      <static>true</static>\n'
        '      <pose>{gx} {gy} 0.04 0 0 0</pose>\n'
        '      <link name="link">\n'
        '        <visual name="visual">\n'
        '          <geometry><cylinder><radius>0.18</radius><length>0.06</length></cylinder></geometry>\n'
        '          <material><ambient>0.95 0.75 0.1 1</ambient>'
        '<diffuse>1.0 0.85 0.15 1</diffuse></material>\n'
        '        </visual>\n'
        '      </link>\n'
        '    </model>\n'
    ).format(gx=gx, gy=gy)


def _recording_sdf(course):
    """Build the course SDF and inject an overhead camera + goal marker."""
    # ``world_sdf`` is headless-ready (no GUI scene broadcaster) — no xacro pass needed.
    sdf = gen_courses.world_sdf(course)
    spec = gen_courses.COURSE_SPECS[course]
    xmin, xmax, ymin, ymax = spec['extent']
    cx, cy = (xmin + xmax) / 2.0, (ymin + ymax) / 2.0
    span = max(xmax - xmin, ymax - ymin)
    goal = spec['goals'][0]
    extras = _camera_block(cx, cy, span * 2.15)
    extras += _goal_marker(goal[1], goal[2])
    return sdf.replace('  </world>', extras + '  </world>')


def _route_poses(course):
    """Return Nx3 array (x, y, yaw) subsampled along the grid A* route."""
    route = grid_demo._route(course)
    if len(route) < 2:
        raise RuntimeError("no route for course '{}'".format(course))
    idx = np.linspace(0, len(route) - 1, FRAME_STEPS).astype(int)
    pts = route[idx]
    yaws = []
    for i in range(len(pts)):
        j = min(i + 1, len(pts) - 1)
        dx, dy = pts[j, 0] - pts[i, 0], pts[j, 1] - pts[i, 1]
        if abs(dx) + abs(dy) < 1e-6 and i > 0:
            dx = pts[i, 0] - pts[i - 1, 0]
            dy = pts[i, 1] - pts[i - 1, 1]
        yaws.append(math.atan2(dy, dx))
    return np.column_stack([pts[:, 0], pts[:, 1], yaws])


def _overlay_title(frame, title):
    """Add a dark title bar (battle-style) on a captured RGB frame."""
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, img.width, 34), fill=(10, 18, 42))
    try:
        font = ImageFont.truetype('DejaVuSans-Bold.ttf', 16)
    except OSError:
        font = ImageFont.load_default()
    draw.text((10, 8), title, fill=(232, 236, 255), font=font)
    return np.asarray(img)


class GazeboRecorder:
    """One gz-sim session with ROS image bridge for frame capture."""

    def __init__(self):
        self._gz = None
        self._bridge = None
        self._node = None
        self._latest = None
        self._rclpy = None
        self._ros_image = None
        self._env = os.environ.copy()
        ros_setup = '/opt/ros/jazzy/setup.bash'
        if os.path.isfile(ros_setup):
            bash_env = subprocess.check_output(
                ['bash', '-c', 'source {} && env'.format(ros_setup)],
                text=True)
            for line in bash_env.splitlines():
                if '=' in line:
                    key, _, val = line.partition('=')
                    self._env[key] = val
        ros_py = '/opt/ros/jazzy/lib/python3.12/site-packages'
        if os.path.isdir(ros_py):
            self._env['PYTHONPATH'] = ros_py + os.pathsep + self._env.get(
                'PYTHONPATH', '')
        res = _tb3_resource_path()
        if res:
            self._env['GZ_SIM_RESOURCE_PATH'] = res
        self._env.setdefault('FASTDDS_BUILTIN_TRANSPORTS', 'UDPv4')

    def _cleanup(self):
        for proc in (self._bridge, self._gz):
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    proc.kill()
        if self._node is not None:
            self._node.destroy_node()
            self._rclpy.shutdown()
            self._node = None

    def start(self, sdf_text):
        atexit.register(self._cleanup)
        tmp = '/tmp/nav2_gazebo_gif_world.sdf'
        with open(tmp, 'w') as fh:
            fh.write(sdf_text)
        self._gz = subprocess.Popen(
            ['gz', 'sim', '-r', '-s', tmp],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=self._env)
        time.sleep(SIM_WARMUP_SEC)

        import rclpy
        from rclpy.node import Node
        from sensor_msgs.msg import Image as RosImage

        self._rclpy = rclpy
        self._ros_image = RosImage
        rclpy.init()
        recorder = self

        class Cap(Node):
            def __init__(self):
                super().__init__('gazebo_gif_capture')
                self.create_subscription(
                    RosImage, '/overhead/image', recorder._on_image, 10)

        self._node = Cap()
        self._bridge = subprocess.Popen(
            ['ros2', 'run', 'ros_gz_image', 'image_bridge', '/overhead/image'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=self._env)
        time.sleep(3.0)
        subprocess.run(
            ['gz', 'topic', '-t', '/overhead/image/enable_streaming',
             '-m', 'gz.msgs.Boolean', '-p', 'data: 1'],
            capture_output=True, env=self._env)

    def _on_image(self, msg):
        self._latest = msg

    def spawn_tb3(self, x, y, yaw):
        qz, qw = math.sin(yaw / 2.0), math.cos(yaw / 2.0)
        req = (
            'sdf_filename: "{}" name: "tb3" pose: {{ position: {{ x: {} y: {} z: 0.01 }} '
            'orientation: {{ z: {} w: {} }} }}'
        ).format(TB3_SDF, x, y, qz, qw)
        subprocess.run(
            ['gz', 'service', '-s', '/world/default/create',
             '--reqtype', 'gz.msgs.EntityFactory', '--reptype', 'gz.msgs.Boolean',
             '--timeout', '8000', '--req', req],
            capture_output=True, text=True, env=self._env)

    def set_pose(self, x, y, yaw):
        qz, qw = math.sin(yaw / 2.0), math.cos(yaw / 2.0)
        req = (
            'name: "tb3" position: {{ x: {} y: {} z: 0.01 }} '
            'orientation: {{ z: {} w: {} }}'
        ).format(x, y, qz, qw)
        subprocess.run(
            ['gz', 'service', '-s', '/world/default/set_pose',
             '--reqtype', 'gz.msgs.Pose', '--reptype', 'gz.msgs.Boolean',
             '--timeout', '3000', '--req', req],
            capture_output=True, env=self._env)
        time.sleep(POSE_SETTLE_SEC)

    def capture(self):
        self._latest = None
        for _ in range(40):
            self._rclpy.spin_once(self._node, timeout_sec=0.12)
            if self._latest is not None:
                msg = self._latest
                return np.frombuffer(
                    msg.data, dtype=np.uint8).reshape(
                        msg.height, msg.width, 3).copy()
        raise RuntimeError('timed out waiting for /overhead/image')

    def reload_world(self, sdf_text):
        """Tear down and restart gz-sim for the next course."""
        self._cleanup()
        atexit.unregister(self._cleanup)
        self.__init__()
        self.start(sdf_text)

    def record_course(self, course, title):
        sdf = _recording_sdf(course)
        poses = _route_poses(course)
        if self._gz is None:
            self.start(sdf)
        else:
            self.reload_world(sdf)
        self.spawn_tb3(poses[0, 0], poses[0, 1], poses[0, 2])
        time.sleep(1.0)
        frames = []
        for x, y, yaw in poses:
            self.set_pose(x, y, yaw)
            frames.append(_overlay_title(self.capture(), title))
        for _ in range(5):
            frames.append(frames[-1])
        return frames


def _write_gif(path, frames, duration=0.09):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    imageio.mimsave(path, frames, duration=duration, loop=0)
    print('wrote {} ({} frames)'.format(os.path.normpath(path), len(frames)))


def main():
    _ensure_ros_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--only', choices=['all', 'battle', 'sim'], default='all',
        help='which GIF set to render (default: all)')
    args = parser.parse_args()

    if not os.path.isfile(TB3_SDF):
        raise SystemExit('TB3 model not found at {}'.format(TB3_SDF))

    rec = GazeboRecorder()
    try:
        if args.only in ('all', 'battle'):
            for fname, course, title in README_JOBS:
                frames = rec.record_course(course, title)
                _write_gif(os.path.join(DOCS, fname), frames)

        if args.only in ('all', 'sim'):
            montage = []
            for course in SIM_COURSES_ORDER:
                title = 'Gazebo · {}'.format(course)
                montage.extend(rec.record_course(course, title))
            _write_gif(os.path.join(DOCS, 'sim_courses.gif'), montage, duration=0.08)
    finally:
        rec._cleanup()


if __name__ == '__main__':
    main()
