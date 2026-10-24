import unittest
from tdmotion.slash_animation import slash_frame
class SlashTests(unittest.TestCase):
    def test_inactive_and_windup_are_invisible(self):
        for active,phase in ((0,.5),(1,0),(1,.15),(1,1),(1,float('nan'))):
            self.assertEqual(slash_frame(active,phase)['visible'],0)
    def test_all_twelve_cells_in_order(self):
        frames=[int(slash_frame(1,.16+.84*(i+.1)/12)['frame']) for i in range(12)]
        self.assertEqual(frames,list(range(12)))
    def test_last_cell_never_wraps_to_first(self):
        result=slash_frame(1,.99999)
        self.assertEqual(result['frame'],11)
        self.assertEqual(result['next_frame'],11)
        self.assertLess(result['fade'],.01)
    def test_attack_restart_starts_from_first_cell(self):
        self.assertEqual(slash_frame(1,.16)['frame'],0)
        self.assertGreater(slash_frame(1,.8)['frame'],0)
        self.assertEqual(slash_frame(1,.16)['frame'],0)
    def test_monotonic_and_bounded(self):
        previous=0
        for i in range(160,1000):
            result=slash_frame(1,i/1000)
            self.assertGreaterEqual(result['frame'],previous);previous=result['frame']
            self.assertTrue(0<=result['blend']<=1 and 0<=result['fade']<=1)
if __name__=='__main__':unittest.main()
