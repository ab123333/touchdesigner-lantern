import math
import unittest
from tdmotion.knight_game import Game,Input,segment_distance

class LimbTests(unittest.TestCase):
    def game(self):
        g=Game();g.x=0;g.y=0;g.enemy_hp=[0,0];g.boss_contact_enabled=False
        return g
    def test_segment_geometry_cross_parallel_and_degenerate(self):
        self.assertEqual(segment_distance((-1,0),(1,0),(0,-1),(0,1))[0],0)
        self.assertAlmostEqual(segment_distance((0,0),(1,0),(0,2),(1,2))[0],2)
        self.assertAlmostEqual(segment_distance((0,0),(0,0),(3,4),(3,4))[0],5)
    def test_each_limb_can_damage_without_torso_overlap(self):
        for name in ('upper_arm_l','forearm_r','thigh_l','shin_r','palm_l','foot_r'):
            g=self.game();g.boss_limb_step(.016,{name:((-.3,.5),(.3,.5),.1)},False)
            self.assertEqual(g.hp,4);self.assertEqual(g.last_limb_hit,name)
    def test_capsule_does_not_hit_outside_radius(self):
        g=self.game();g.boss_limb_step(.016,{'arm':((.8,0),(.8,1),.1)},True)
        self.assertEqual(g.hp,5)
    def test_horizontal_swept_attack_does_not_tunnel(self):
        for sign in (-1,1):
            g=self.game();g.boss_limb_step(.1,{'arm':((-sign*.6,.4),(-sign*.6,.9),.08)},True)
            self.assertEqual(g.hp,5)
            g.boss_limb_step(.1,{'arm':((sign*.6,.4),(sign*.6,.9),.08)},True)
            self.assertEqual(g.hp,4);self.assertGreater(g.knockback_x*sign,0)
    def test_downward_hit_pushes_down_not_up(self):
        g=self.game();g.y=2
        g.boss_limb_step(.1,{'foot':((-.15,3.8),(.15,3.8),.08)},True)
        g.boss_limb_step(.1,{'foot':((-.15,2.8),(.15,2.8),.08)},True)
        self.assertEqual(g.hp,4);self.assertLess(g.vy,0)
    def test_no_reacquire_teleport_or_hidden_joint_swept_hit(self):
        for mode in ('reacquire','teleport','hidden'):
            g=self.game();x=2 if mode=='teleport' else .6
            g.boss_limb_step(.016,{'arm':((-x,.4),(-x,.9),.08)},mode!='reacquire',set() if mode=='hidden' else None)
            g.boss_limb_step(.016,{'arm':((x,.4),(x,.9),.08)},True)
            self.assertEqual(g.hp,5)
    def test_contact_once_for_multiple_limbs_and_invulnerable_dash(self):
        for immune in (False,True):
            g=self.game();g.invulnerable=.1 if immune else 0
            g.boss_limb_step(.016,{str(i):((-.3,.5),(.3,.5),.1) for i in range(12)},True)
            self.assertEqual(g.hp,5 if immune else 4)
    def test_dead_disabled_and_invalid_segments_are_safe(self):
        for mode in ('dead','disabled','invalid'):
            g=self.game();segments={'arm':((-.3,.5),(.3,.5),.1)}
            if mode=='dead':g.boss_hp=0
            if mode=='disabled':g.boss_limb_enabled=False
            if mode=='invalid':segments['arm']=((math.nan,.5),(.3,.5),.1)
            g.boss_limb_step(.016,segments,True)
            self.assertEqual(g.hp,5)

if __name__=='__main__':unittest.main()
