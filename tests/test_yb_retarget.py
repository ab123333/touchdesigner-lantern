import math
import unittest

from tdmotion.rig_retarget import (
    LANDMARK_NAMES,
    MODEL_REST_EULER,
    YBotRetargeter,
    canonical_input_points,
    canonical_points,
    euler_xyz_to_matrix,
    matrix_to_euler_xyz,
    mat_mul,
    mat_transpose,
)


class YBotRetargetTests(unittest.TestCase):
    def test_startup_without_camera_reports_lost_not_tracking(self):
        pose, status, quality = YBotRetargeter().update(None, 0.0)
        self.assertEqual(status, 'lost')
        self.assertEqual(quality, 0)
        self.assertEqual(set(pose), set(MODEL_REST_EULER))

    def test_hidden_legs_return_to_rest_while_visible_arm_tracks(self):
        solver = YBotRetargeter(max_angular_speed=100000)
        points = canonical_input_points()
        points['left_wrist'] = (0.52,0.34,0.03/solver.depth_scale)
        visibility = {name: 1.0 for name in LANDMARK_NAMES}
        for side in ('left', 'right'):
            for joint in ('hip', 'knee', 'ankle', 'heel', 'foot_index'):
                visibility[side + '_' + joint] = 0.01
        for frame in range(60):
            pose, status, quality = solver.update(points, frame/60, visibility=visibility)
        self.assertEqual(status, 'tracking')
        self.assertLess(quality, 1)
        self.assertGreater(max(abs(v) for v in pose['mixamorig_LeftForeArm']), 5)
        for bone in ('mixamorig_LeftLeg','mixamorig_RightLeg'):
            for actual, expected in zip(pose[bone], MODEL_REST_EULER[bone]):
                self.assertAlmostEqual(actual, expected, places=3)

    def test_euler_roundtrip_preserves_rotation(self):
        for angles in ((0, 0, 0), (20, -15, 45), (-80, 35, 170)):
            matrix = euler_xyz_to_matrix(angles)
            rebuilt = euler_xyz_to_matrix(matrix_to_euler_xyz(matrix))
            for row in range(3):
                for col in range(3):
                    self.assertAlmostEqual(matrix[row][col], rebuilt[row][col], places=6)

    def test_canonical_pose_reproduces_authored_rest_pose(self):
        solver = YBotRetargeter(max_angular_speed=100000)
        pose, status, quality = solver.update(canonical_input_points(), 0.0)
        self.assertEqual(status, "tracking")
        self.assertEqual(quality, 1.0)
        for bone, expected in MODEL_REST_EULER.items():
            actual_matrix = euler_xyz_to_matrix(pose[bone])
            expected_matrix = euler_xyz_to_matrix(expected)
            error = mat_mul(mat_transpose(expected_matrix), actual_matrix)
            self.assertAlmostEqual(error[0][0] + error[1][1] + error[2][2], 3.0, places=4, msg=bone)

    def test_touchdesigner_normalized_y_is_already_up(self):
        """pose_tracking/math3 has already converted MediaPipe y to 1-y."""
        solver = YBotRetargeter(max_angular_speed=100000)
        td_points = {
            name: (point[0], point[1], -point[2] / solver.depth_scale)
            for name, point in canonical_points().items()
        }
        pose, status, _ = solver.update(td_points, 0.0)
        self.assertEqual(status, "tracking")
        for bone, expected in MODEL_REST_EULER.items():
            actual_matrix = euler_xyz_to_matrix(pose[bone])
            expected_matrix = euler_xyz_to_matrix(expected)
            error = mat_mul(mat_transpose(expected_matrix), actual_matrix)
            self.assertAlmostEqual(error[0][0] + error[1][1] + error[2][2], 3.0, places=4, msg=bone)

    def test_bending_left_elbow_drives_forearm_not_other_side(self):
        solver = YBotRetargeter(max_angular_speed=100000)
        solver.update(canonical_input_points(), 0.0)
        moved_world = canonical_points()
        moved_world["left_wrist"] = (0.52, 0.34, -0.03)
        moved_world["left_index"] = (0.53, 0.24, -0.03)
        moved_world["left_pinky"] = (0.49, 0.24, -0.03)
        moved = {name: (point[0], point[1], -point[2] / solver.depth_scale) for name, point in moved_world.items()}
        pose, status, _ = solver.update(moved, 1.0 / 30.0)
        self.assertEqual(status, "tracking")
        left_change = max(abs(pose["mixamorig_LeftForeArm"][i] - MODEL_REST_EULER["mixamorig_LeftForeArm"][i]) for i in range(3))
        right_change = max(abs(pose["mixamorig_RightForeArm"][i] - MODEL_REST_EULER["mixamorig_RightForeArm"][i]) for i in range(3))
        self.assertGreater(left_change, 5.0)
        self.assertLess(right_change, 1.0)

    def test_nonfinite_input_holds_then_returns_toward_rest(self):
        solver = YBotRetargeter(max_angular_speed=100000, hold_seconds=0.2, fade_seconds=0.3)
        solver.update(canonical_input_points(), 0.0)
        invalid = canonical_input_points()
        invalid["nose"] = (math.nan, 0.0, 0.0)
        _, status, _ = solver.update(invalid, 0.1)
        self.assertEqual(status, "holding")
        _, status, _ = solver.update(None, 0.35)
        self.assertEqual(status, "fading")
        pose, status, _ = solver.update(None, 0.7)
        self.assertEqual(status, "lost")
        self.assertEqual(set(pose), set(MODEL_REST_EULER))

    def test_output_is_finite_for_representative_motion(self):
        solver = YBotRetargeter()
        for frame in range(120):
            p_world = canonical_points()
            phase = frame / 119.0 * math.pi * 2.0
            p_world["left_elbow"] = (0.48, 0.62 + 0.18 * math.sin(phase), 0.1 * math.cos(phase))
            p_world["left_wrist"] = (0.70, 0.55 + 0.28 * math.sin(phase), 0.16 * math.cos(phase))
            p_world["left_index"] = (0.79, p_world["left_wrist"][1] + 0.02, p_world["left_wrist"][2])
            p_world["left_pinky"] = (0.79, p_world["left_wrist"][1] - 0.02, p_world["left_wrist"][2])
            p = {name: (point[0], point[1], -point[2] / solver.depth_scale) for name, point in p_world.items()}
            out, _, _ = solver.update(p, frame / 60.0)
            self.assertTrue(all(math.isfinite(value) for angles in out.values() for value in angles))


if __name__ == "__main__":
    unittest.main()
