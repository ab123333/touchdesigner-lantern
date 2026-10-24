import unittest
from tdmotion.dash_animation import DashVFX
from tdmotion.knight_game import Game,Input

class DashVFXTests(unittest.TestCase):
    def test_idle_is_hidden(self):
        self.assertEqual(DashVFX().update(False,0,0,0,0,1)['visible'],0)
    def test_active_then_tail_play_all_cells(self):
        v=DashVFX();frames=[]
        for i in range(8):frames.append(int(v.update(True,(i+.1)/8,i*.02,0,0,1)['frame']))
        for i in range(4):frames.append(int(v.update(False,0,.16+i*.02,0,0,1)['frame']))
        self.assertEqual(frames,list(range(12)))
        self.assertEqual(v.update(False,0,.241,0,0,1)['visible'],0)
    def test_tail_does_not_flip_or_follow_turn(self):
        v=DashVFX();v.update(True,.9,1,2,1,-1)
        v.update(False,0,1.01,1.9,1,-1)
        result=v.update(False,0,1.03,2.1,1,1)
        self.assertEqual(result['face'],-1);self.assertEqual(result['x'],1.9)
    def test_recook_at_same_game_time_does_not_speed_up(self):
        v=DashVFX();a=v.update(True,.4,1,0,0,1)
        for _ in range(50):self.assertEqual(a,v.update(True,.4,1,0,0,1))
    def test_repeat_dash_restarts_and_uses_new_direction(self):
        v=DashVFX();v.update(True,.9,1,0,0,1);v.update(False,0,1.01,0,0,1)
        r=v.update(True,0,1.03,0,0,-1)
        self.assertEqual(r['frame'],0);self.assertEqual(r['face'],-1)
    def test_invalid_data_and_reset_hide_old_effect(self):
        v=DashVFX();v.update(True,.9,5,0,0,1);v.update(False,0,5.01,0,0,1)
        self.assertEqual(v.update(False,0,0,0,0,1)['visible'],0)
        self.assertEqual(v.update(True,float('nan'),1,0,0,1)['visible'],0)
    def test_physics_exposes_phase_without_changing_dash(self):
        g=Game();values=[]
        for _ in range(20):
            g.advance(1/120,Input(dash=True));c=g.channels()
            if c['dash']:values.append(c['dash_phase'])
        self.assertEqual(values,sorted(values));self.assertGreater(values[-1],.8)
        self.assertEqual(g.channels()['dash'],0)
if __name__=='__main__':unittest.main()
