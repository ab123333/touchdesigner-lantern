import unittest
from tdmotion.knight_game import Game, Input, deadzone

def run(game,seconds,controls=Input(),fps=60):
    for _ in range(round(seconds*fps)):game.advance(1/fps,controls)

class KnightGameTests(unittest.TestCase):
    def test_idle_does_not_drift_or_sink(self):
        g=Game();run(g,3)
        self.assertEqual((g.x,g.y),(-7,0));self.assertTrue(g.grounded)
    def test_deadzone(self):
        self.assertEqual(deadzone(.1),0)
        self.assertEqual(deadzone(-1),-1)
    def test_jump_and_land(self):
        g=Game();run(g,.2,Input(jump=True));self.assertGreater(g.y,0.8)
        run(g,2);self.assertAlmostEqual(g.y,0);self.assertTrue(g.grounded)
    def test_variable_jump_height(self):
        short=Game();high=Game()
        run(short,.05,Input(jump=True));run(short,.20)
        run(high,.25,Input(jump=True))
        self.assertGreater(high.y,short.y+.2)
    def test_dash_cooldown_and_air_charge(self):
        g=Game();g.advance(1/60,Input(dash=True));self.assertGreater(g.dash_time,0)
        run(g,.3,Input(dash=True));self.assertEqual(g.dash_time,0)
        self.assertGreater(g.dash_cooldown,0)
    def test_platform_collision_stops_dash(self):
        g=Game();g.x=-5.2;g.y=1.;g.grounded=False
        run(g,.12,Input(move=1,dash=True))
        self.assertLessEqual(g.x,-5.03+1e-6)
    def test_attack_hits_once_per_swing(self):
        g=Game();g.x=1.6
        run(g,.3,Input(attack=True))
        self.assertEqual(g.hits,1);self.assertEqual(g.enemy_hp[0],3)
    def test_frame_rate_independence(self):
        a=Game();b=Game()
        run(a,1,Input(move=-1),30);run(b,1,Input(move=-1),120)
        self.assertAlmostEqual(a.x,b.x,places=6)
    def test_disconnect_releases_motion(self):
        g=Game();run(g,.3,Input(move=-1));run(g,1,Input())
        self.assertEqual(g.vx,0)

if __name__=='__main__':unittest.main()
