#!/usr/bin/env python3
"""YAM forward kinematics: the tool frame (i2rt's `grasp_site`) in the robot base.

The glove labels' tool frame is this site. build_dataset turns a glove pose M (tile world -> ball
body) into an IK target F = inv(T_world_base) . M . inv(T_flange_body) for `grasp_site`, and
slam.labels stores T_ref_tool = T_ref_cam . T_cam_body . inv(T_flange_body) (evaluate.load_tool_offset).
So for teleop data the same tool pose is simply FK(q)[grasp_site], with no extra offset.

This is i2rt's own model and FK, exactly as build_dataset and evaluate_yam use them:
    Kinematics(combine_arm_and_gripper_xml(ArmType.YAM, GripperType.NO_GRIPPER), "grasp_site").fk(q)
i2rt is imported from I2RT_DIR (third_party/i2rt, commit 0b475453 = v1.4.1), as build_dataset
imports ~/co/i2rt. Its robots.utils imports the CAN drivers, so the env needs python-can, tyro and
crcmod-plus besides mujoco and mink (all in the lerobot env since 2026-11-10). yam.xml,
no_gripper.xml and the yam block of no_gripper.yml are unchanged since v1.3.6 (2026-09-17).

  fk = YamFK(); T = fk(q)          # q (6,) or (N, 6) joint1..joint6 in rad -> (4, 4) or (N, 4, 4)
  python -m slam.robot_fk          # FK at a few joint vectors
"""
import os
import sys
from pathlib import Path

import numpy as np

I2RT_DIR = Path(os.environ.get("I2RT_DIR", "/home/student/yuanliu-hawaii/third_party/i2rt"))
SITE = "grasp_site"


def _i2rt():
    if str(I2RT_DIR) not in sys.path:
        sys.path.insert(0, str(I2RT_DIR))
    from i2rt.robots.kinematics import Kinematics
    from i2rt.robots.utils import ArmType, GripperType, combine_arm_and_gripper_xml
    return Kinematics, combine_arm_and_gripper_xml(ArmType.YAM, GripperType.NO_GRIPPER)


class YamFK:
    def __init__(self, site=SITE):
        Kinematics, xml = _i2rt()
        self.kin = Kinematics(xml, site)
        self.site = site
        self.model = self.kin._configuration.model
        if self.model.nq != 6:
            raise ValueError(f"expected 6 joints, model has nq={self.model.nq}")

    def __call__(self, q):
        q = np.asarray(q, float)
        one = q.ndim == 1
        Q = q[None] if one else q
        out = np.stack([self.kin.fk(qi[:6], self.site) for qi in Q])
        return out[0] if one else out


def main():
    fk = YamFK()
    print(f"i2rt YAM + no_gripper from {I2RT_DIR}: nq={fk.model.nq}, site {SITE!r}")
    np.set_printoptions(precision=5, suppress=True)
    for q in (np.zeros(6), np.array([0.3, 0.8, 0.9, -0.4, 0.2, 0.5])):
        print("q =", q)
        print(fk(q))


if __name__ == "__main__":
    main()
