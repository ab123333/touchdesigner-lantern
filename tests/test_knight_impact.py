import math
import unittest
from tdmotion.knight_game import Game, Input


class ImpactTests(unittest.TestCase):
    def game(self):
        g=Game();g.enemy_hp=[0,0]
        return g

    def test_contact_hurts_and_pushes_away_on_both_sides(self):
        for side in (-1,1):
            g=self.game();g.x=g.boss_x+side*.7
            g.advance(1/120,Input())
            self.assertEqual(g.hp,4)
            self.assertGreater(g.knockback_x*side,0)
            self.assertFalse(g.grounded)

    def test_contact_shares_invulnerability_with_sweep(self):
        g=self.game();g.x=g.boss_x-.5
        g.advance(1/120,Input());self.assertEqual(g.hp,4)
        g.boss_phase=2;g.boss_timer=.2
        g.boss_step(.016,True,(0,1),(1,1))
        self.assertEqual(g.hp,4)
        for _ in range(45):
            g.x=g.boss_x-.5;g.y=0;g.advance(1/60,Input())
        self.assertEqual(g.hp,4)

    def test_dead_boss_disabled_contact_and_overhead_are_safe(self):
        for mode in ('dead','disabled','above'):
            g=self.game();g.x=g.boss_x
            if mode=='dead':g.boss_hp=0
            if mode=='disabled':g.boss_contact_enabled=False
            if mode=='above':g.y=4
            g.advance(1/60,Input())
            self.assertEqual(g.hp,5)

    def test_dash_through_contact(self):
        g=self.game();g.x=g.boss_x-.8
        for _ in range(8):g.advance(1/60,Input(move=1,dash=True))
        self.assertEqual(g.hp,5)

    def test_input_cannot_cancel_recoil_or_jump_cut(self):
        g=self.game();g.x=0;g.y=3
        g.take_hit(1,(-6,5.5));start=g.x
        g.advance(.1,Input(move=1,jump=True,dash=True,attack=True))
        self.assertLess(g.x,start-.35)
        self.assertEqual(g.attack_time,0);self.assertEqual(g.dash_time,0)
        self.assertAlmostEqual(g.vy,5.5-g.gravity*.1)

    def test_release_jump_does_not_cut_initial_recoil(self):
        g=self.game();g.y=4;g.take_hit(1,(-6,5.5))
        g.advance(1/120,Input())
        self.assertGreater(g.vy,5)

    def test_attack_velocity_controls_strength_direction_and_is_bounded(self):
        magnitudes=[]
        for velocity in ((3,0),(9,0),(-9,0),(10000,10000)):
            g=self.game();g.x=g.boss_x-1.5
            g.boss_phase=2;g.boss_timer=.2;g.boss_attack_velocity=velocity
            g.boss_step(.016,True,(0,1),(1,1))
            self.assertEqual(g.hp,4)
            self.assertLessEqual(abs(g.knockback_x),8)
            self.assertLessEqual(g.vy,6)
            self.assertGreater(g.knockback_x*velocity[0],0)
            magnitudes.append(abs(g.knockback_x))
        self.assertGreater(magnitudes[1],magnitudes[0])

    def test_windup_retains_momentum_after_hands_stop(self):
        g=self.game();g.boss_step(1/60,True,(0,1),(0,1))
        g.boss_step(1/60,True,(.15,1),(.15,1))
        self.assertEqual(g.boss_phase,1)
        stored=g.boss_attack_velocity
        for _ in range(10):g.boss_step(1/60,True,(.15,1),(.15,1))
        self.assertEqual(g.boss_attack_velocity,stored)

    def test_loss_reacquire_and_invalid_tracking_do_not_strike(self):
        g=self.game();g.x=g.boss_x-1.5
        g.boss_phase=2;g.boss_timer=.2
        g.boss_step(.016,False,(0,0),(0,0))
        g.boss_step(.016,True,(10,10),(-10,-10))
        self.assertEqual(g.boss_phase,0);self.assertEqual(g.hp,5)
        g.boss_step(.016,True,(math.nan,1),(0,1))
        self.assertFalse(g.boss_tracking)
        self.assertTrue(all(math.isfinite(v) for v in g.channels().values()))

    def test_recoil_respects_walls_and_floor(self):
        g=self.game();g.x=8.6;g.y=1.;g.take_hit(7,(8,3))
        for _ in range(120):g.advance(1/120,Input())
        self.assertLessEqual(g.x,8.77+1e-6)
        self.assertGreaterEqual(g.y,0)

    def test_recoil_fixed_step_consistency_and_reset(self):
        results=[]
        for fps in (30,60,120):
            g=self.game();g.x=0;g.y=4;g.take_hit(1,(-6,5))
            for _ in range(fps//2):g.advance(1/fps,Input())
            results.append((g.x,g.y,g.knockback_x))
        for result in results[1:]:
            for a,b in zip(results[0],result):self.assertAlmostEqual(a,b,places=6)
        g.advance(1/60,Input(reset=True))
        self.assertEqual(g.knockback_x,0);self.assertEqual(g.hurt_time,0)
        self.assertEqual(g.boss_attack_velocity,(0,0));self.assertEqual(g.hp,5)


if __name__=='__main__':unittest.main()
