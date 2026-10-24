import math
import unittest
from tdmotion.rig_retarget import (mirror_wrist_twist,euler_xyz_to_matrix,matrix_to_quat,quat_to_matrix,mat_vec,quat_angle,assign_hand_sides,YBotRetargeter,canonical_input_points)

class WristMirrorTests(unittest.TestCase):
    def test_twist_direction_reversed(self):
        q=matrix_to_quat(euler_xyz_to_matrix((0,55,0)))
        expected=matrix_to_quat(euler_xyz_to_matrix((0,-55,0)))
        self.assertLess(quat_angle(mirror_wrist_twist(q),expected),1e-6)
    def test_swing_and_hand_pointing_direction_preserved(self):
        for angles in ((25,55,-30),(-40,-70,15),(0,0,0),(179,40,-50)):
            q=matrix_to_quat(euler_xyz_to_matrix(angles))
            reflected=mirror_wrist_twist(q)
            a=mat_vec(quat_to_matrix(q),(0,1,0));b=mat_vec(quat_to_matrix(reflected),(0,1,0))
            for x,y in zip(a,b):self.assertAlmostEqual(x,y,places=6)
            self.assertLess(quat_angle(q,mirror_wrist_twist(reflected)),1e-6)
    def test_other_bones_unchanged_and_outputs_finite(self):
        plain=YBotRetargeter();mirror=YBotRetargeter(wrist_mirror=True)
        p=canonical_input_points()
        p['left_index']=(.88,.63,-.03);p['left_pinky']=(.88,.60,.03)
        for i in range(120):
            a,_,_=plain.update(p,i/60);b,_,_=mirror.update(p,i/60)
            self.assertTrue(all(math.isfinite(v) for values in b.values() for v in values))
        for name in a:
            if not name.endswith('Hand'):self.assertEqual(a[name],b[name])
    def test_two_hands_assignment_never_uses_same_side(self):
        poses=[dict(x=0,y=0,visibility=1) for _ in range(33)]
        poses[15]['x']=.45;poses[16]['x']=.6
        images=[[dict(x=x,y=0) for _ in range(21)] for x in (.48,.50)]
        result=assign_hand_sides(images,poses,[])
        self.assertEqual(result,{0:'Left',1:'Right'})
    def test_mirrored_image_assignment_keeps_pose_labels(self):
        poses=[dict(x=0,y=.5,visibility=1) for _ in range(33)]
        poses[15]['x']=.8;poses[16]['x']=.2
        images=[[dict(x=x,y=.5) for _ in range(21)] for x in (.2,.8)]
        self.assertEqual(assign_hand_sides(images,poses,[]),{0:'Right',1:'Left'})

if __name__=='__main__':unittest.main()
