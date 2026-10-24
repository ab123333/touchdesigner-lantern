import math
import unittest
from tdmotion.rig_retarget import (
    YBotRetargeter,constrain_arm_joint,canonical_input_points,
    matrix_to_quat,quat_to_matrix,euler_xyz_to_matrix,mat_mul,
    mat_transpose,quat_angle,mat_vec,
)

IDENTITY=(1.,0.,0.,0.)
def quaternion(x=0,y=0,z=0):return matrix_to_quat(euler_xyz_to_matrix((x,y,z)))
def twist_degrees(q):
    if q[0]<0:q=tuple(-x for x in q)
    return math.degrees(2*math.atan2(q[2],q[0]))

class JointLimitTests(unittest.TestCase):
    def test_total_twist_range_is_180_for_both_hands_and_forearms(self):
        for side in ('Left','Right'):
            for part in ('Hand','ForeArm'):
                name='mixamorig_'+side+part
                a,_=constrain_arm_joint(quaternion(y=-150),name)
                b,_=constrain_arm_joint(quaternion(y=150),name)
                self.assertAlmostEqual(twist_degrees(a),-90)
                self.assertAlmostEqual(twist_degrees(b),90)
                self.assertAlmostEqual(math.degrees(quat_angle(a,b)),180)

    def test_half_turn_boundary_does_not_flip_saturation(self):
        for direction in (-1,1):
            previous=None
            for degrees in range(0,196,3):
                q,previous=constrain_arm_joint(quaternion(y=direction*degrees),'mixamorig_LeftHand',previous)
                expected=direction*min(90,degrees)
                self.assertAlmostEqual(twist_degrees(q),expected,places=5)
            for degrees in range(195,-1,-3):
                q,previous=constrain_arm_joint(quaternion(y=direction*degrees),'mixamorig_LeftHand',previous)
            self.assertLess(quat_angle(q,IDENTITY),1e-6)

    def test_detector_full_turn_history_cannot_latch_neutral(self):
        for history in (-720,-360,360,720):
            q,state=constrain_arm_joint(quaternion(y=15),'mixamorig_LeftHand',history)
            self.assertAlmostEqual(twist_degrees(q),15)
            self.assertAlmostEqual(state,15)

    def test_hand_swing_has_90_degree_neutral_cone(self):
        for x in (-170,-95,0,95,170):
            for y in (-170,-95,0,95,170):
                for z in (-110,0,110):
                    q,_=constrain_arm_joint(quaternion(x,y,z),'mixamorig_RightHand')
                    self.assertLessEqual(math.degrees(quat_angle(q,IDENTITY)),90.00001)
                    self.assertLessEqual(abs(twist_degrees(q)),90.00001)

    def test_forearm_preserves_elbow_flexion_beyond_90(self):
        q,_=constrain_arm_joint(quaternion(x=140),'mixamorig_LeftForeArm')
        self.assertAlmostEqual(math.degrees(quat_angle(q,IDENTITY)),140)
        q,_=constrain_arm_joint(quaternion(x=179),'mixamorig_LeftForeArm')
        self.assertLessEqual(math.degrees(quat_angle(q,IDENTITY)),155.00001)

    def test_opposite_quaternion_sign_has_same_constraint(self):
        q=quaternion(20,140,10)
        a,_=constrain_arm_joint(q,'mixamorig_LeftHand')
        b,_=constrain_arm_joint(tuple(-v for v in q),'mixamorig_LeftHand')
        self.assertLess(quat_angle(a,b),1e-6)

    def test_final_filtered_output_remains_bounded_and_continuous(self):
        for part in ('Hand','ForeArm'):
            solver=YBotRetargeter();name='mixamorig_Left'+part;previous=IDENTITY
            for i,degrees in enumerate(range(0,541,3)):
                frames=dict(solver.rest_human)
                desired=mat_mul(solver.model_rest_global[name],euler_xyz_to_matrix((0,degrees,0)))
                frames[name]=mat_mul(desired,mat_transpose(solver.alignment[name]))
                rotations=solver._solve_frames(frames,i/60)
                delta=matrix_to_quat(mat_mul(mat_transpose(solver.model_rest_local[name]),euler_xyz_to_matrix(rotations[name])))
                self.assertLessEqual(abs(twist_degrees(delta)),90.0001)
                self.assertLess(math.degrees(quat_angle(previous,delta)),10.)
                previous=delta
            self.assertAlmostEqual(twist_degrees(previous),90,places=2)

    def test_tracking_loss_and_calibration_reset_turn_history(self):
        solver=YBotRetargeter();solver.joint_twist['mixamorig_LeftHand']=720
        solver.update(None,4)
        self.assertLess(abs(solver.joint_twist.get('mixamorig_LeftHand',0)),1e-3)
        solver.update(canonical_input_points(),5)
        solver.calibrate()
        self.assertEqual(solver.joint_twist,{})

if __name__=='__main__':unittest.main()
