import math,unittest
from tdmotion.rig_retarget import *

def rig_hand(side):
    sign=1 if side=='Left' else -1
    p=[(0.,0.,0.)]*21
    p[5]=(-2.82204*sign,12.2666,.231825)
    p[9]=(0.,12.7755,0.)
    p[17]=(4.72583*sign,10.9082,.226132)
    rests=[(27.3117,-12.9209*sign,23.4132*sign),(0,0,0),(0,0,0)]
    p[1]=(-3.00297*sign,3.78881,2.16715)
    parent=euler_xyz_to_matrix(rests[0])
    for j,d in enumerate((4.74497,4.382,3.459)):
        p[j+2]=add(p[j+1],mat_vec(parent,(0,d,0)))
    return p,rests

class PalmGeometryTests(unittest.TestCase):
    def test_authored_open_thumb_returns_bind_pose(self):
        for side in ('Left','Right'):
            p,rests=rig_hand(side)
            solved=solve_thumb(p,palm_frame(p),rests)
            for q,rest in zip(solved,rests):self.assertLess(quat_angle(q,matrix_to_quat(euler_xyz_to_matrix(rest))),1e-6)

    def test_camera_roll_translation_scale_do_not_curl_thumb(self):
        p,rests=rig_hand('Left');basis=palm_frame(p)
        for angles in ((40,90,15),(-90,50,170),(0,180,0)):
            rotation=euler_xyz_to_matrix(angles)
            moved=[add(mul(mat_vec(rotation,x),.015),(.2,.5,-.1)) for x in p]
            solved=solve_thumb(moved,basis,rests)
            for q,r in zip(solved,rests):self.assertLess(quat_angle(q,matrix_to_quat(euler_xyz_to_matrix(r))),1e-6)

    def test_thumb_segments_follow_actual_local_direction(self):
        for side in ('Left','Right'):
            p,rests=rig_hand(side);basis=palm_frame(p)
            parent=((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))
            wanted=[]
            for j in range(3):
                local=mat_mul(euler_xyz_to_matrix(rests[j]),euler_xyz_to_matrix((25+10*j,0,0)))
                parent=mat_mul(parent,local);wanted.append(mat_vec(parent,(0,1,0)))
                p[j+2]=add(p[j+1],mul(wanted[-1],4.))
            parent=((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))
            for q,d in zip(solve_thumb(p,basis,rests),wanted):
                parent=mat_mul(parent,quat_to_matrix(q))
                self.assertGreater(dot(mat_vec(parent,(0,1,0)),d),.999)

    def test_thumb_degenerate_palm_rejected(self):
        self.assertIsNone(solve_thumb([(0,0,0)]*21,((1,0,0),(0,1,0),(0,0,1)),[(0,0,0)]*3))

    def test_geometric_palm_uses_actual_mesh_basis_without_second_mirror(self):
        for side in ('Left','Right'):
            p,_=rig_hand(side);name='mixamorig_'+side+'Hand'
            solver=YBotRetargeter(wrist_mirror=True);solver.hand_bind_frames[name]=palm_frame(p)
            frames=dict(solver.rest_human)
            expected=mat_mul(solver.model_rest_global[name],euler_xyz_to_matrix((0,45,0)))
            frames[name]=mat_mul(expected,palm_frame(p))
            for i in range(180):out=solver._solve_frames(frames,i/60)
            world={}
            for bone,parent in PARENTS.items():
                local=euler_xyz_to_matrix(out[bone]);world[bone]=mat_mul(world[parent],local) if parent else local
            self.assertLess(quat_angle(matrix_to_quat(world[name]),matrix_to_quat(expected)),1e-5)
            self.assertLess(abs(out[name][1]),2.)

    def test_front_side_back_palm_share_roll_with_forearm_within_limits(self):
        for side in ('Left','Right'):
            p,_=rig_hand(side);name='mixamorig_'+side+'Hand';forearm=PARENTS[name]
            for degrees in (-170,-90,0,90,170):
                solver=YBotRetargeter();solver.hand_bind_frames[name]=palm_frame(p)
                frames=dict(solver.rest_human)
                expected=mat_mul(solver.model_rest_global[name],euler_xyz_to_matrix((0,degrees,0)))
                frames[name]=mat_mul(expected,palm_frame(p))
                for i in range(180):out=solver._solve_frames(frames,i/60)
                world={}
                for bone,parent in PARENTS.items():
                    local=euler_xyz_to_matrix(out[bone]);world[bone]=mat_mul(world[parent],local) if parent else local
                self.assertLess(math.degrees(quat_angle(matrix_to_quat(world[name]),matrix_to_quat(expected))),.1,(side,degrees))
                for bone in (name,forearm):
                    q=matrix_to_quat(mat_mul(mat_transpose(solver.model_rest_local[bone]),euler_xyz_to_matrix(out[bone])))
                    if q[0]<0:q=tuple(-v for v in q)
                    self.assertLessEqual(abs(math.degrees(2*math.atan2(q[2],q[0]))),90.001)

if __name__=='__main__':unittest.main()
