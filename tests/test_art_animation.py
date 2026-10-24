import unittest,math
from tdmotion.art_animation import TurnAnimator,hand_angles,HandFilter
class ArtTests(unittest.TestCase):
    def test_turn_is_continuous_and_finishes(self):
        a=TurnAnimator();a.update(1,1/60);before=a.yaw
        a.update(-1,1/60)
        self.assertLess(abs(a.yaw-before),30)
        for _ in range(60):a.update(-1,1/60)
        self.assertAlmostEqual(a.yaw,-65,places=2)
    def test_rapid_reversal_does_not_spin(self):
        a=TurnAnimator()
        for i in range(200):
            last=a.yaw;a.update(1 if i%7 else -1,1/60)
            self.assertLess(abs(a.yaw-last),30)
            self.assertLessEqual(abs(a.yaw),65)
    def test_open_finger_angles(self):
        points=[(0,0,0)]*21
        for base,x in ((1,-2),(5,-1),(9,0),(13,1),(17,2)):
            for j in range(4):points[base+j]=(x,2+j,0)
        angles=hand_angles(points)
        self.assertAlmostEqual(angles['Index'][1],0)
        self.assertAlmostEqual(angles['Index'][2],0)
    def test_bent_finger_and_anatomical_limit(self):
        p=[(0,0,0)]*21
        for x,base in enumerate((1,5,9,13,17)):p[base:base+4]=[(x-2,1,0),(x-2,2,0),(x-2,2,-1),(x-2,1,-1)]
        a=hand_angles(p)
        self.assertAlmostEqual(a['Index'][1],90)
        self.assertLessEqual(a['Index'][2],80)
    def test_missing_hand_holds_then_relaxes(self):
        f=HandFilter();target={name:[70,80,60,0] for name in ('Thumb','Index','Middle','Ring','Pinky')}
        for i in range(60):f.update(target,1/60)
        held=f.angles['Index'][1];f.update(None,.1)
        self.assertAlmostEqual(f.angles['Index'][1],held)
        for _ in range(120):f.update(None,1/60)
        self.assertLess(f.angles['Index'][1],1)
    def test_nan_rejected(self):
        self.assertIsNone(hand_angles([(math.nan,0,0)]*21))
    def test_long_tracking_loss_snaps_to_exact_zero(self):
        f=HandFilter();f.angles['Index'][1]=90
        for _ in range(2000):f.update(None,1/60)
        self.assertEqual(f.angles['Index'][1],0.)
