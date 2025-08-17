#!/usr/bin/env python3
import json
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped
from tf2_ros import Buffer, TransformListener
from builtin_interfaces.msg import Duration

# MoveIt 2 python API
from moveit_commander.move_group import MoveGroupCommander
from moveit_commander.robot import RobotCommander
from moveit_commander.planning_scene_interface import PlanningSceneInterface
from moveit_msgs.msg import Constraints, OrientationConstraint

# your pydantic schema
from schema.schema import Command, Step, Constraints as MyConstraints

class NLBridge(Node):
    def __init__(self):
        super().__init__("nl_moveit_bridge")
        # MoveIt setup
        self.robot = RobotCommander()
        self.arm = MoveGroupCommander("manipulator")     # group name from your SRDF
        self.arm.set_max_velocity_scaling_factor(0.5)
        self.arm.set_max_acceleration_scaling_factor(0.3)
        self.scene = PlanningSceneInterface()
        # TF2
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # IO
        self.sub = self.create_subscription(String, "/nl_task_json", self.on_json, 10)
        self.pub = self.create_publisher(String, "/nl_task_result", 10)

        # (optional) Gripper hook — replace with your gripper driver
        # self.gripper_pub = self.create_publisher(std_msgs/Float64, "/gripper/command", 10)

        self.get_logger().info("NL→MoveIt bridge ready.")

    def on_json(self, msg: String):
        try:
            raw = json.loads(msg.data)
            cmd = Command.model_validate(raw)  # pydantic v2
        except Exception as e:
            self._emit_error(f"schema_error: {e}")
            return

        # apply globals
        self.arm.set_max_velocity_scaling_factor(cmd.globals_.vel_scale)
        self.arm.set_max_acceleration_scaling_factor(cmd.globals_.accel_scale)

        for i, step in enumerate(cmd.steps):
            ok, err = self.execute_step(step)
            if not ok:
                self._emit_error(f"step_{i}:{err}")
                return

        self._emit_ok("done")

    # ----------------- step executors -----------------

    def execute_step(self, step: Step):
        if step.action == "move_ee":
            return self._do_move(step)
        if step.action == "pick":
            return self._do_pick(step)
        if step.action == "place":
            return self._do_place(step)
        return False, f"unknown_action:{step.action}"

    def _do_move(self, step: Step):
        try:
            pose = self._pose_from_step(step)
            self._apply_constraints(step.constraints)
            self.arm.set_start_state_to_current_state()
            self.arm.set_pose_target(pose)
            plan = self.arm.plan()
            if not plan or len(plan.joint_trajectory.points) == 0:
                return False, "plan_failed"
            self.arm.execute(plan, wait=True)
            self.arm.clear_pose_targets()
            self._clear_constraints()
            return True, None
        except Exception as e:
            return False, f"move_exception:{e}"

    def _do_pick(self, step: Step):
        # Simple pick: move to pregrasp above object frame, descend cartesian, (close gripper), lift
        try:
            # 1) pregrasp
            pre = self._pose_above_object(step.object, step.grasp.pregrasp_m if step.grasp else 0.08)
            self._apply_constraints(step.constraints)
            self.arm.set_start_state_to_current_state()
            self.arm.set_pose_target(pre)
            plan = self.arm.plan()
            if not plan or len(plan.joint_trajectory.points) == 0:
                self._clear_constraints()
                return False, "pregrasp_plan_failed"
            self.arm.execute(plan, wait=True)

            # 2) descend cartesian
            descend = PoseStamped()
            descend.header = pre.header
            descend.pose = pre.pose
            descend.pose.position.z -= (step.grasp.pregrasp_m if step.grasp else 0.08) - 0.01  # touch down
            (cartesian_path, frac) = self.arm.compute_cartesian_path([descend.pose], 0.01, 0.0)
            if frac < 0.99:
                self._clear_constraints()
                return False, "cartesian_descend_failed"
            self.arm.execute(cartesian_path, wait=True)

            # 3) close gripper (placeholder)
            # self._gripper_close()

            # 4) lift a bit
            lift = descend
            lift.pose.position.z += 0.10
            (path_up, frac2) = self.arm.compute_cartesian_path([lift.pose], 0.01, 0.0)
            if frac2 < 0.99:
                self._clear_constraints()
                return False, "cartesian_lift_failed"
            self.arm.execute(path_up, wait=True)

            self._clear_constraints()
            return True, None
        except Exception as e:
            self._clear_constraints()
            return False, f"pick_exception:{e}"

    def _do_place(self, step: Step):
        # Simple place: move above target, descend, open gripper, retreat
        try:
            offset = step.offset_xyz if step.offset_xyz else [0.0, 0.0, 0.10]
            pose = self._pose_at_target(step.target, offset)
            self._apply_constraints(step.constraints)
            self.arm.set_start_state_to_current_state()
            self.arm.set_pose_target(pose)
            plan = self.arm.plan()
            if not plan or len(plan.joint_trajectory.points) == 0:
                self._clear_constraints()
                return False, "place_plan_failed"
            self.arm.execute(plan, wait=True)

            # open gripper (placeholder)
            # self._gripper_open()

            self._clear_constraints()
            return True, None
        except Exception as e:
            self._clear_constraints()
            return False, f"place_exception:{e}"

    # ----------------- helpers -----------------

    def _pose_from_step(self, step: Step) -> PoseStamped:
        """
        Build a PoseStamped using either:
         - step.pose_xyzrpy in a given frame (step.frame or base)
         - or a frame+offset (for object/target)
        """
        if step.pose_xyzrpy:
            frame = step.frame or "base_link"
            return self._pose_from_xyzrpy(frame, step.pose_xyzrpy)

        # fallback: if only frame & offset provided
        if step.frame and step.offset_xyz:
            base = self._lookup_frame(step.frame)
            base.pose.position.x += step.offset_xyz[0]
            base.pose.position.y += step.offset_xyz[1]
            base.pose.position.z += step.offset_xyz[2]
            return base

        raise RuntimeError("pose_missing")

    def _pose_above_object(self, obj_name: str, dz: float) -> PoseStamped:
        p = self._lookup_frame(obj_name)          # assumes TF frame per object
        p.pose.position.z += dz
        return p

    def _pose_at_target(self, target_name: str, offset):
        p = self._lookup_frame(target_name)
        p.pose.position.x += offset[0]
        p.pose.position.y += offset[1]
        p.pose.position.z += offset[2]
        return p

    def _pose_from_xyzrpy(self, frame_id: str, xyzrpy):
        ps = PoseStamped()
        ps.header.frame_id = frame_id
        ps.header.stamp = self.get_clock().now().to_msg()
        from tf_transformations import quaternion_from_euler
        import math
        ps.pose.position.x, ps.pose.position.y, ps.pose.position.z = xyzrpy[:3]
        qx, qy, qz, qw = quaternion_from_euler(xyzrpy[3], xyzrpy[4], xyzrpy[5])
        ps.pose.orientation.x, ps.pose.orientation.y, ps.pose.orientation.z, ps.pose.orientation.w = qx, qy, qz, qw
        return ps

    def _lookup_frame(self, frame_id: str) -> PoseStamped:
        # gets geometry of a TF frame as a PoseStamped in that frame itself
        ps = PoseStamped()
        try:
            # transform from frame to base_link to get absolute pose (adjust target frame as needed)
            t = self.tf_buffer.lookup_transform("base_link", frame_id, rclpy.time.Time())
            ps.header.frame_id = "base_link"
            ps.header.stamp = t.header.stamp
            ps.pose.position.x = t.transform.translation.x
            ps.pose.position.y = t.transform.translation.y
            ps.pose.position.z = t.transform.translation.z
            ps.pose.orientation = t.transform.rotation
            return ps
        except Exception as e:
            raise RuntimeError(f"tf_lookup_failed:{frame_id}:{e}")

    def _apply_constraints(self, cons: MyConstraints | None):
        self.arm.clear_path_constraints()
        if not cons:
            return
        if cons.keep_vertical:
            oc = OrientationConstraint()
            oc.link_name = self.arm.get_end_effector_link()
            oc.header.frame_id = "base_link"
            oc.orientation.w = 1.0  # identity (EE “upright” in base_link)
            oc.absolute_x_axis_tolerance = 0.17  # ~10 deg
            oc.absolute_y_axis_tolerance = 0.17
            oc.absolute_z_axis_tolerance = 3.14
            oc.weight = 1.0
            c = Constraints()
            c.orientation_constraints.append(oc)
            self.arm.set_path_constraints(c)

    def _clear_constraints(self):
        self.arm.clear_path_constraints()

    def _emit_ok(self, msg: str):
        self.pub.publish(String(data=json.dumps({"status":"ok","msg":msg})))

    def _emit_error(self, msg: str):
        self.pub.publish(String(data=json.dumps({"status":"error","msg":msg})))

def main():
    rclpy.init()
    node = NLBridge()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == "__main__":
    main()
