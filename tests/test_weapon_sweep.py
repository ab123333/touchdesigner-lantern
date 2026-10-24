import math,unittest
from tdmotion.art_animation import attack_weapon_pose
class WeaponSweepTests(unittest.TestCase):
    def test_mid_swing_matches_all_aim_directions(self):
        for face in (-1,1):
            for aim in (-1,0,1):
                p=attack_weapon_pose(.47,face,aim,0,0);a=math.radians(p['weapon_angle'])
                direction=(-math.sin(a),math.cos(a))
                expected=(face,0) if not aim else (0,aim)
                for x,y in zip(direction,expected):self.assertAlmostEqual(x,y,places=6)
    def test_sweep_is_continuous_and_does_not_reverse(self):
        for face in (-1,1):
            last=attack_weapon_pose(0,face,0,0,0)['weapon_angle']
            for i in range(1,101):
                value=attack_weapon_pose(i/100,face,0,0,0)['weapon_angle']
                self.assertLessEqual((value-last)*face,1e-6)
                self.assertLess(abs(value-last),4)
                last=value
    def test_aim_rotates_socket_as_well_as_blade(self):
        for face in (-1,1):
            up=attack_weapon_pose(.47,face,1,0,0);down=attack_weapon_pose(.47,face,-1,0,0)
            self.assertAlmostEqual(up['weapon_x'],0);self.assertAlmostEqual(down['weapon_x'],0)
            self.assertGreater(up['weapon_y'],down['weapon_y'])
if __name__=='__main__':unittest.main()
