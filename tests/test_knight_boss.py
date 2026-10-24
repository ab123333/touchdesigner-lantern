import unittest
from tdmotion.knight_game import Game,Input
class BossTests(unittest.TestCase):
    def test_missing_tracking_never_attacks(self):
        g=Game()
        for _ in range(120):g.advance(1/60,Input());g.boss_step(1/60,False,(-2,1),(2,1))
        self.assertEqual(g.boss_phase,0)
    def test_swing_telegraphs_before_damage(self):
        g=Game();g.x=g.boss_x-1.5
        g.boss_step(.016,True,(-.5,2),(.5,2))
        g.boss_step(.016,True,(-1.6,2),(1.6,2))
        self.assertEqual(g.boss_phase,1);self.assertEqual(g.hp,5)
        for _ in range(40):g.boss_step(.016,True,(-1.6,2),(1.6,2))
        self.assertLess(g.hp,5)
    def test_player_strike_damages_boss_once(self):
        g=Game();g.x=g.boss_x-.9
        for _ in range(30):g.advance(1/60,Input(attack=True));g.boss_step(1/60,False,(0,0),(0,0))
        self.assertEqual(g.boss_hp,29)
    def test_dash_invulnerability(self):
        g=Game();g.x=g.boss_x-1.;g.boss_phase=2;g.boss_timer=.2;g.invulnerable=.5
        g.boss_step(.016,True,(-1,1),(1,1));self.assertEqual(g.hp,5)
