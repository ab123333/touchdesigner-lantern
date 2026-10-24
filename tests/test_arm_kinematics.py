"""Check physical bone directions, not just Euler channel existence."""
import math
import unittest
from tdmotion.rig_retarget import (
    YBotRetargeter, PARENTS, canonical_points, euler_xyz_to_matrix,
    mat_mul, mat_vec, normalize, sub, dot, matrix_to_quat, quat_angle,
)


def input_pose(p):
    return {name: (v[0], v[1], -v[2]/0.65) for name,v in p.items()}


def forward_rotations(pose):
    result = {}
    for bone, parent in PARENTS.items():
        local = euler_xyz_to_matrix(pose[bone])
        result[bone] = mat_mul(result[parent],local) if parent else local
    return result


class ArmKinematicsTests(unittest.TestCase):
    def test_both_upper_arms_can_drop_vertically(self):
        p = canonical_points()
        for side, x in (('left',0.24),('right',-0.24)):
            p[side+'_elbow'] = (x,0.34,0)
            p[side+'_wrist'] = (x,0.07,0)
            p[side+'_index'] = (x,0.0,-0.01)
            p[side+'_pinky'] = (x,0.0,0.01)
        solver = YBotRetargeter()
        for frame in range(180):
            pose,_,_ = solver.update(input_pose(p),frame/60)
        world = forward_rotations(pose)
        for side in ('Left','Right'):
            for segment in ('Arm','ForeArm'):
                direction = mat_vec(world['mixamorig_'+side+segment],(0,1,0))
                self.assertGreater(dot(direction,(0,-1,0)),0.99,(side,segment,direction))

    def test_near_straight_elbow_noise_does_not_flip(self):
        solver = YBotRetargeter()
        previous = None
        peak = 0
        for frame in range(240):
            p = canonical_points()
            noise = 0.0001 if frame%2 else -0.0001
            p['left_wrist'] = (0.79,0.62+noise,noise)
            pose,_,_ = solver.update(input_pose(p),frame/60)
            q = matrix_to_quat(euler_xyz_to_matrix(pose['mixamorig_LeftForeArm']))
            if previous:
                peak=max(peak,math.degrees(quat_angle(q,previous)))
            previous=q
        self.assertLess(peak,1.0)

    def test_euler_branch_at_pitch_90_preserves_small_motion(self):
        previous=(20.0,89.0,30.0)
        # Principal XYZ solution of (20,91,30).
        unwrapped=YBotRetargeter._unwrap((-160,89,-150),previous)
        self.assertLess(max(abs(a-b) for a,b in zip(unwrapped,previous)),3)

    def test_bending_arm_points_toward_observed_wrist(self):
        p=canonical_points()
        p['left_elbow']=(0.24,0.34,0)
        p['left_wrist']=(0.24,0.34,-0.27)
        p['left_index']=(0.25,0.34,-0.36)
        p['left_pinky']=(0.23,0.34,-0.36)
        solver=YBotRetargeter()
        for frame in range(240):
            pose,_,_=solver.update(input_pose(p),frame/60)
        world=forward_rotations(pose)
        for bone,a,b in (('LeftArm','left_shoulder','left_elbow'),('LeftForeArm','left_elbow','left_wrist')):
            direction=mat_vec(world['mixamorig_'+bone],(0,1,0))
            self.assertGreater(dot(direction,normalize(sub(p[b],p[a]))),0.98,(bone,direction))


if __name__=='__main__':
    unittest.main()
