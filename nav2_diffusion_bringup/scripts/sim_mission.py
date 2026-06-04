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
In-launch mission node for the headless Gazebo closed-loop benchmark.

Runs *inside* the simulation launch (so it shares the launch's DDS graph and does
not depend on external-process discovery, which is unreliable in restricted
sandboxes — see docs/simulation.md section 10.5). It waits for the Nav2
``navigate_to_pose`` action, drives the robot to a goal with whatever FollowPath
controller the params file loaded (here DiffusionController), records the executed
odometry, and writes a Markdown result file. The result file — not a ROS topic —
is the artifact, so the run is verifiable without joining the DDS graph.
"""

import math
import time

from action_msgs.msg import GoalStatus

from geometry_msgs.msg import Quaternion

from nav2_msgs.action import NavigateToPose

from nav_msgs.msg import Odometry

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node


def yaw_to_quaternion(yaw):
    """Planar yaw [rad] -> geometry_msgs/Quaternion."""
    q = Quaternion()
    q.z = math.sin(yaw * 0.5)
    q.w = math.cos(yaw * 0.5)
    return q


class SimMission(Node):
    """Send one NavigateToPose goal, record odometry, write a result file."""

    def __init__(self):
        super().__init__('sim_mission')
        self.declare_parameter('goal_x', 0.0)
        self.declare_parameter('goal_y', -0.5)
        self.declare_parameter('goal_yaw', 0.0)
        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('timeout_sec', 120.0)
        self.declare_parameter('server_wait_sec', 60.0)
        self.declare_parameter('odom_topic', '/odom')
        self.declare_parameter('label', 'Diffusion (Mode A) in Gazebo')
        self.declare_parameter('results_file', '/tmp/sim_mission_result.md')

        self.goal_x = self.get_parameter('goal_x').value
        self.goal_y = self.get_parameter('goal_y').value
        self.goal_yaw = self.get_parameter('goal_yaw').value
        self.frame_id = self.get_parameter('frame_id').value
        self.timeout_sec = self.get_parameter('timeout_sec').value
        self.server_wait_sec = self.get_parameter('server_wait_sec').value
        self.label = self.get_parameter('label').value
        self.results_file = self.get_parameter('results_file').value

        self.path_len = 0.0
        self.steps = 0
        self.last_xy = None
        self.cur_xy = None
        self.sub = self.create_subscription(
            Odometry, self.get_parameter('odom_topic').value, self.on_odom, 10)
        self.client = ActionClient(self, NavigateToPose, 'navigate_to_pose')

    def on_odom(self, msg):
        p = msg.pose.pose.position
        xy = (p.x, p.y)
        if self.last_xy is not None:
            self.path_len += math.hypot(xy[0] - self.last_xy[0], xy[1] - self.last_xy[1])
        self.last_xy = xy
        self.cur_xy = xy
        self.steps += 1

    def _wait_for_odom(self, timeout):
        deadline = time.time() + timeout
        while rclpy.ok() and self.cur_xy is None and time.time() < deadline:
            rclpy.spin_once(self, timeout_sec=0.2)
        return self.cur_xy is not None

    def run(self):
        """Block until the goal completes / times out, then write the result."""
        if not self.client.wait_for_server(timeout_sec=self.server_wait_sec):
            return self._finish(False, 'navigate_to_pose action server unavailable')
        if not self._wait_for_odom(self.server_wait_sec):
            return self._finish(False, 'no odometry received')
        start_xy = self.cur_xy

        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = self.frame_id
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = float(self.goal_x)
        goal.pose.pose.position.y = float(self.goal_y)
        goal.pose.pose.orientation = yaw_to_quaternion(float(self.goal_yaw))

        self.get_logger().info(
            'sending goal ({:.2f}, {:.2f}) in {}'.format(
                self.goal_x, self.goal_y, self.frame_id))
        wall_start = time.time()
        send_future = self.client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future)
        handle = send_future.result()
        if handle is None or not handle.accepted:
            return self._finish(False, 'goal rejected by server', wall_start, start_xy)

        result_future = handle.get_result_async()
        deadline = wall_start + self.timeout_sec
        while rclpy.ok() and not result_future.done():
            rclpy.spin_once(self, timeout_sec=0.2)
            if time.time() > deadline:
                handle.cancel_goal_async()
                rclpy.spin_once(self, timeout_sec=0.5)
                return self._finish(False, 'timeout', wall_start, start_xy)

        status = result_future.result().status
        reached = status == GoalStatus.STATUS_SUCCEEDED
        note = 'succeeded' if reached else 'action status {}'.format(status)
        self._finish(reached, note, wall_start, start_xy)

    def _finish(self, reached, note, wall_start=None, start_xy=None):
        elapsed = (time.time() - wall_start) if wall_start else 0.0
        gx, gy = float(self.goal_x), float(self.goal_y)
        final = self.cur_xy or (float('nan'), float('nan'))
        dist_to_goal = math.hypot(final[0] - gx, final[1] - gy)
        lines = [
            '# Gazebo closed-loop mission result',
            '',
            '> Auto-generated by `sim_mission` (in-launch). One NavigateToPose goal '
            'driven by the FollowPath controller in a headless TB3 Gazebo sim. '
            'See [simulation.md](simulation.md) section 10.5.',
            '',
            '| Run | Reached goal | Wall time [s] | Path length [m] | '
            'Odom samples | Final dist to goal [m] | Note |',
            '|---|:-:|--:|--:|--:|--:|---|',
            '| {} | {} | {:.1f} | {:.2f} | {} | {:.3f} | {} |'.format(
                self.label, 'yes' if reached else 'no', elapsed, self.path_len,
                self.steps, dist_to_goal, note),
            '',
            '- Goal: ({:.2f}, {:.2f}) in `{}`; start odom: {}'.format(
                gx, gy, self.frame_id,
                '({:.2f}, {:.2f})'.format(*start_xy) if start_xy else 'n/a'),
            '- Path length is the executed odometry distance; "reached" is the Nav2 '
            'action result (goal checker in the map frame).',
        ]
        text = '\n'.join(lines) + '\n'
        try:
            with open(self.results_file, 'w') as handle:
                handle.write(text)
            self.get_logger().info('wrote result to ' + self.results_file)
        except OSError as exc:
            self.get_logger().error('failed to write result: {}'.format(exc))
        self.get_logger().info('MISSION DONE reached={} note={}'.format(reached, note))


def main():
    rclpy.init()
    node = SimMission()
    try:
        node.run()
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
