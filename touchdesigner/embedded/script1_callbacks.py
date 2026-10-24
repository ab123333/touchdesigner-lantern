"""Hierarchical MediaPipe-to-Mixamo retargeting for the user's Y_Bot rig.

The module is dependency-free so the same code can be imported by TouchDesigner
2023's embedded Python and by the regression tests.  It deliberately solves
rotations only: the imported FBX keeps its authored bone lengths and hierarchy.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


EPS = 1e-8


LANDMARK_NAMES = (
    "nose", "left_eye_inner", "left_eye", "left_eye_outer",
    "right_eye_inner", "right_eye", "right_eye_outer", "left_ear",
    "right_ear", "mouth_left", "mouth_right", "left_shoulder",
    "right_shoulder", "left_elbow", "right_elbow", "left_wrist",
    "right_wrist", "left_pinky", "right_pinky", "left_index",
    "right_index", "left_thumb", "right_thumb", "left_hip",
    "right_hip", "left_knee", "right_knee", "left_ankle",
    "right_ankle", "left_heel", "right_heel", "left_foot_index",
    "right_foot_index",
)


# Values are taken from the imported Y_Bot FBX in test.4.toe.  They are the
# authored local rest rotations, not a guessed generic Mixamo pose.
MODEL_REST_EULER = {
    "mixamorig_Hips": (0.0, -0.000200894, 0.00502868),
    "mixamorig_Spine": (-6.96346, 0.0000434793, 0.000671252),
    "mixamorig_Spine1": (0.0224709, 0.0, -0.00106754),
    "mixamorig_Spine2": (6.61695, 0.000229479, 0.000390329),
    "mixamorig_Neck": (0.324032, 0.0, 0.0),
    "mixamorig_Head": (0.0, 0.0, 0.0),
    "mixamorig_LeftShoulder": (88.3918, 101.623, -2.7863),
    "mixamorig_LeftArm": (-1.20607, -0.0000253432, 11.6114),
    "mixamorig_LeftForeArm": (0.0, 0.0, 0.0),
    "mixamorig_LeftHand": (0.0, 0.0000204906, 0.0000136604),
    "mixamorig_RightShoulder": (88.3917, -101.623, 2.77234),
    "mixamorig_RightArm": (-1.20201, 0.0000257484, -11.6114),
    "mixamorig_RightForeArm": (0.0, 0.0, 0.0),
    "mixamorig_RightHand": (0.0, -0.0000204906, -0.0000136604),
    "mixamorig_LeftUpLeg": (-0.726505, -0.000167737, -179.66),
    "mixamorig_LeftLeg": (-2.07822, 0.00861278, -0.678671),
    "mixamorig_LeftFoot": (65.4691, -0.161368, 3.29573),
    "mixamorig_LeftToeBase": (26.4121, -3.22711, -2.56681),
    "mixamorig_RightUpLeg": (-0.725756, -0.000160291, 179.65),
    "mixamorig_RightLeg": (-2.0797, -0.00859721, 0.678671),
    "mixamorig_RightFoot": (65.4699, 0.161415, -3.29582),
    "mixamorig_RightToeBase": (26.4121, 3.18506, 2.54424),
}


PARENTS = {
    "mixamorig_Hips": None,
    "mixamorig_Spine": "mixamorig_Hips",
    "mixamorig_Spine1": "mixamorig_Spine",
    "mixamorig_Spine2": "mixamorig_Spine1",
    "mixamorig_Neck": "mixamorig_Spine2",
    "mixamorig_Head": "mixamorig_Neck",
    "mixamorig_LeftShoulder": "mixamorig_Spine2",
    "mixamorig_LeftArm": "mixamorig_LeftShoulder",
    "mixamorig_LeftForeArm": "mixamorig_LeftArm",
    "mixamorig_LeftHand": "mixamorig_LeftForeArm",
    "mixamorig_RightShoulder": "mixamorig_Spine2",
    "mixamorig_RightArm": "mixamorig_RightShoulder",
    "mixamorig_RightForeArm": "mixamorig_RightArm",
    "mixamorig_RightHand": "mixamorig_RightForeArm",
    "mixamorig_LeftUpLeg": "mixamorig_Hips",
    "mixamorig_LeftLeg": "mixamorig_LeftUpLeg",
    "mixamorig_LeftFoot": "mixamorig_LeftLeg",
    "mixamorig_LeftToeBase": "mixamorig_LeftFoot",
    "mixamorig_RightUpLeg": "mixamorig_Hips",
    "mixamorig_RightLeg": "mixamorig_RightUpLeg",
    "mixamorig_RightFoot": "mixamorig_RightLeg",
    "mixamorig_RightToeBase": "mixamorig_RightFoot",
}


# Maximum rotation away from the authored local rest pose.  This is a cone
# limit (quaternion angle), so it is independent of Euler wrapping.
MAX_DELTA_DEG = {
    "mixamorig_Hips": 95.0,
    "mixamorig_Spine": 30.0,
    "mixamorig_Spine1": 35.0,
    "mixamorig_Spine2": 40.0,
    "mixamorig_Neck": 55.0,
    "mixamorig_Head": 70.0,
    "mixamorig_LeftShoulder": 55.0,
    "mixamorig_RightShoulder": 55.0,
    "mixamorig_LeftArm": 175.0,
    "mixamorig_RightArm": 175.0,
    "mixamorig_LeftForeArm": 155.0,
    "mixamorig_RightForeArm": 155.0,
    "mixamorig_LeftHand": 90.0,
    "mixamorig_RightHand": 90.0,
    "mixamorig_LeftUpLeg": 135.0,
    "mixamorig_RightUpLeg": 135.0,
    "mixamorig_LeftLeg": 155.0,
    "mixamorig_RightLeg": 155.0,
    "mixamorig_LeftFoot": 80.0,
    "mixamorig_RightFoot": 80.0,
    "mixamorig_LeftToeBase": 55.0,
    "mixamorig_RightToeBase": 55.0,
}


def clamp(value, low, high):
    return min(high, max(low, value))


def add(a, b):
    return tuple(a[i] + b[i] for i in range(3))


def sub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def mul(v, scalar):
    return tuple(v[i] * scalar for i in range(3))


def dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def length(v):
    return math.sqrt(max(0.0, dot(v, v)))


def normalize(v, fallback=(0.0, 1.0, 0.0)):
    n = length(v)
    return tuple(c / n for c in v) if n > EPS else tuple(fallback)


def midpoint(a, b):
    return mul(add(a, b), 0.5)


def mat_mul(a, b):
    return tuple(tuple(sum(a[r][k] * b[k][c] for k in range(3)) for c in range(3)) for r in range(3))


def mat_transpose(m):
    return tuple(tuple(m[c][r] for c in range(3)) for r in range(3))


def mat_vec(m, v):
    return tuple(dot(row, v) for row in m)


def stable_limb_normal(first, second, fallback, state, key, dt):
    """Transport the bend plane across straight poses without a 180-degree flip.

    Cross products lose their direction as a limb straightens. Transport the
    last reliable plane with the upper limb, then use the observed plane only
    when there is a meaningful bend. Limit axial twist separately from swing.
    """
    axis = normalize(first)
    old_axis, old_normal = state.get(key, (axis, fallback))
    cos_angle = clamp(dot(old_axis, axis), -1.0, 1.0)
    if cos_angle > -0.999:
        q = quat_normalize((1.0 + cos_angle,) + cross(old_axis, axis))
        transported = mat_vec(quat_to_matrix(q), old_normal)
    else:
        transported = old_normal
    base_frame = frame_from_y_normal(axis, transported, fallback)
    base = tuple(row[2] for row in base_frame)
    bend = cross(axis, normalize(second))
    strength = clamp((length(bend) - 0.12) / 0.35, 0.0, 1.0)
    normal = base
    if strength > 0.0:
        observed = normalize(bend)
        if dot(observed, base) < 0.0:
            observed = mul(observed, -1.0)
        twist = math.atan2(dot(axis, cross(base, observed)), dot(base, observed))
        limit = math.radians(100.0) * dt
        twist = clamp(twist * strength, -limit, limit)
        normal = add(mul(base, math.cos(twist)), mul(cross(axis, base), math.sin(twist)))
    state[key] = (axis, normal)
    return normal


def euler_xyz_to_matrix(euler):
    """TouchDesigner default order: Rz * Ry * Rx, degrees."""
    x, y, z = (math.radians(v) for v in euler)
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    return (
        (cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx),
        (sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx),
        (-sy, cy * sx, cy * cx),
    )


def matrix_to_euler_xyz(m):
    y = math.asin(clamp(-m[2][0], -1.0, 1.0))
    cy = math.cos(y)
    if abs(cy) > 1e-6:
        x = math.atan2(m[2][1], m[2][2])
        z = math.atan2(m[1][0], m[0][0])
    else:
        x = math.atan2(-m[1][2], m[1][1])
        z = 0.0
    return tuple(math.degrees(v) for v in (x, y, z))


def quat_normalize(q):
    n = math.sqrt(sum(v * v for v in q))
    return tuple(v / n for v in q) if n > EPS else (1.0, 0.0, 0.0, 0.0)


def matrix_to_quat(m):
    trace = m[0][0] + m[1][1] + m[2][2]
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        q = (0.25 * s, (m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s)
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2.0
        q = ((m[2][1] - m[1][2]) / s, 0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s)
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2.0
        q = ((m[0][2] - m[2][0]) / s, (m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s)
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2.0
        q = ((m[1][0] - m[0][1]) / s, (m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s)
    return quat_normalize(q)


def quat_to_matrix(q):
    w, x, y, z = quat_normalize(q)
    return (
        (1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)),
        (2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)),
        (2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)),
    )


def quat_slerp(a, b, amount):
    a, b = quat_normalize(a), quat_normalize(b)
    cos_theta = sum(a[i] * b[i] for i in range(4))
    if cos_theta < 0.0:
        b = tuple(-v for v in b)
        cos_theta = -cos_theta
    amount = clamp(amount, 0.0, 1.0)
    if cos_theta > 0.9995:
        return quat_normalize(tuple(a[i] + amount * (b[i] - a[i]) for i in range(4)))
    theta = math.acos(clamp(cos_theta, -1.0, 1.0))
    sin_theta = math.sin(theta)
    wa = math.sin((1.0 - amount) * theta) / sin_theta
    wb = math.sin(amount * theta) / sin_theta
    return tuple(wa * a[i] + wb * b[i] for i in range(4))

def quat_multiply(a,b):
    w,x,y,z=a;v,i,j,k=b
    return (w*v-x*i-y*j-z*k,w*i+x*v+y*k-z*j,w*j-x*k+y*v+z*i,w*k+x*j-y*i+z*v)

def mirror_wrist_twist(q):
    """Reverse axial wrist twist about local +Y without changing hand aim.

    Anatomical hand bones point along local Y. Reflection of the camera palm
    roll must be handled in this bind-local frame, not by negating XYZ Euler
    angles or reflecting the whole skeleton a second time.
    """
    q=quat_normalize(q)
    twist=quat_normalize((q[0],0.,q[2],0.))
    inverse=(twist[0],-twist[1],-twist[2],-twist[3])
    swing=quat_multiply(q,inverse)
    return quat_normalize(quat_multiply(swing,inverse))

def assign_hand_sides(images,pose,labels):
    """Match the two detectors in their SAME mirrored image coordinates."""
    wrists={}
    if pose and len(pose)>=17:
        for side,j in (('Left',15),('Right',16)):
            p=pose[j]
            if p.get('visibility',0)>.35:wrists[side]=p
    costs=[]
    for i,points in enumerate(images[:2]):
        if len(points)!=21:continue
        for side,wrist in wrists.items():
            d=math.hypot(points[0]['x']-wrist['x'],points[0]['y']-wrist['y'])
            if math.isfinite(d) and d<.3:costs.append((d,i,side))
    # Two possible assignments; prioritize matching both, then total distance.
    assignments=[[]]+[[c] for c in costs]
    assignments += [[a,b] for a in costs for b in costs if a[1]<b[1] and a[2]!=b[2]]
    best=min(assignments,key=lambda rows:(-len(rows),sum(r[0] for r in rows)))
    result={i:side for _,i,side in best}
    for i in range(min(2,len(images))):
        if i in result:continue
        label=labels[i][0] if i<len(labels) and labels[i] else {}
        side=label.get('categoryName',label.get('displayName'))
        if side in ('Left','Right') and side not in result.values():result[i]=side
    return result


def quat_angle(a, b):
    value = abs(sum(quat_normalize(a)[i] * quat_normalize(b)[i] for i in range(4)))
    return 2.0 * math.acos(clamp(value, -1.0, 1.0))


def limit_rotation(q, max_degrees):
    identity = (1.0, 0.0, 0.0, 0.0)
    angle = quat_angle(identity, q)
    maximum = math.radians(max_degrees)
    return quat_slerp(identity, q, maximum / angle) if angle > maximum and angle > EPS else quat_normalize(q)

def constrain_arm_joint(q,bone,previous_twist=None):
    """Bind-local arm constraints; axial twist has a TOTAL 180 degree range.

    Hand orientation stays within 90 degrees of neutral. Forearm twist is
    limited to +/-90 without reducing its existing 155 degree elbow bend.
    Unwrap the measured twist BEFORE clamping, so +179 -> -179 cannot turn
    saturation at +90 into a sudden command to rotate toward -90.
    """
    q=quat_normalize(q)
    if q[0]<0:q=tuple(-v for v in q)
    if not bone.endswith(('Hand','ForeArm')):
        return limit_rotation(q,MAX_DELTA_DEG[bone]),previous_twist
    norm=math.hypot(q[0],q[2])
    if norm<1e-7:
        measured=previous_twist if previous_twist is not None else 0.
        # Twist is unobservable at a 180 degree swing. Transport the previous
        # twist instead of accepting an arbitrary frame normal.
        twist=(math.cos(math.radians(measured)/2),0.,math.sin(math.radians(measured)/2),0.)
    else:
        twist=(q[0]/norm,0.,q[2]/norm,0.)
        measured=math.degrees(2*math.atan2(twist[2],twist[0]))
        # Hysteresis only around the ambiguous half-turn. Never accumulate
        # full revolutions: a noisy detector must be able to return to neutral.
        if previous_twist is not None and abs(measured)>150:
            measured+=360*round((previous_twist-measured)/360)
    inverse=(twist[0],0.,-twist[2],0.)
    swing=quat_multiply(q,inverse)
    bounded=math.radians(clamp(measured,-90.,90.))/2
    result=quat_multiply(swing,(math.cos(bounded),0.,math.sin(bounded),0.))
    return limit_rotation(result,MAX_DELTA_DEG[bone]),clamp(measured,-210.,210.)


def frame_from_y_normal(y_axis, normal, fallback=None):
    y = normalize(y_axis)
    z = sub(normal, mul(y, dot(normal, y)))
    if length(z) < 1e-5 and fallback is not None:
        z = sub(fallback, mul(y, dot(fallback, y)))
    if length(z) < 1e-5:
        axis = (1.0, 0.0, 0.0) if abs(y[0]) < 0.8 else (0.0, 0.0, 1.0)
        z = cross(axis, y)
    z = normalize(z, (0.0, 0.0, 1.0))
    x = normalize(cross(y, z), (1.0, 0.0, 0.0))
    z = normalize(cross(x, y), z)
    # Columns are the local X/Y/Z axes in world coordinates.
    return tuple(tuple((x, y, z)[c][r] for c in range(3)) for r in range(3))


def palm_frame(points):
    """Landmark palm basis; does not depend on finger flexion or camera roll."""
    forward=sub(midpoint(points[5],points[17]),points[0])
    across=sub(points[5],points[17])
    if length(forward)<1e-6 or length(cross(across,forward))<1e-8:return None
    return frame_from_y_normal(forward,cross(across,forward))


def solve_thumb(points,bind_frame,rests):
    """Aim CMC/MCP/IP segments in rig palm space, retaining authored roll.

    Unlike an index finger, the thumb has an oblique metacarpal and opposition.
    A shortest-arc swing maps each real segment into its actual parent frame.
    Local rest-cone bounds prevent flipped joints without inventing Euler axes.
    """
    source=palm_frame(points)
    if source is None:return None
    mapping=mat_mul(bind_frame,mat_transpose(source))
    parent=((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))
    result=[]
    for j,maximum in enumerate((80.,85.,90.)):
        direction=mat_vec(mapping,sub(points[j+2],points[j+1]))
        if length(direction)<1e-6:return None
        rest=euler_xyz_to_matrix(rests[j])
        local=normalize(mat_vec(mat_transpose(mat_mul(parent,rest)),direction))
        axis=cross((0.,1.,0.),local)
        q=quat_normalize((1.+local[1],)+axis) if local[1]>-.99999 else (0.,1.,0.,0.)
        q=limit_rotation(q,maximum)
        rotation=mat_mul(rest,quat_to_matrix(q))
        result.append(matrix_to_quat(rotation))
        parent=mat_mul(parent,rotation)
    return result


def _frame_limb(a, b, c, fallback_normal):
    first, second = sub(b, a), sub(c, b)
    return frame_from_y_normal(first, cross(first, second), fallback_normal)


def _frame_segment(a, b, plane_normal, fallback_normal):
    return frame_from_y_normal(sub(b, a), plane_normal, fallback_normal)


def canonical_points():
    p = {name: (0.0, 0.0, 0.0) for name in LANDMARK_NAMES}
    p.update({
        "nose": (0.0, 0.92, -0.08), "left_ear": (0.08, 0.86, 0.0), "right_ear": (-0.08, 0.86, 0.0),
        "mouth_left": (0.035, 0.82, -0.055), "mouth_right": (-0.035, 0.82, -0.055),
        "left_shoulder": (0.24, 0.62, 0.0), "right_shoulder": (-0.24, 0.62, 0.0),
        "left_elbow": (0.52, 0.62, 0.0), "right_elbow": (-0.52, 0.62, 0.0),
        "left_wrist": (0.79, 0.62, 0.0), "right_wrist": (-0.79, 0.62, 0.0),
        "left_pinky": (0.88, 0.60, 0.0), "right_pinky": (-0.88, 0.60, 0.0),
        "left_index": (0.89, 0.64, 0.0), "right_index": (-0.89, 0.64, 0.0),
        "left_thumb": (0.84, 0.56, -0.02), "right_thumb": (-0.84, 0.56, -0.02),
        "left_hip": (0.13, 0.0, 0.0), "right_hip": (-0.13, 0.0, 0.0),
        "left_knee": (0.13, -0.43, 0.0), "right_knee": (-0.13, -0.43, 0.0),
        "left_ankle": (0.13, -0.85, 0.0), "right_ankle": (-0.13, -0.85, 0.0),
        "left_heel": (0.13, -0.88, 0.06), "right_heel": (-0.13, -0.88, 0.06),
        "left_foot_index": (0.13, -0.89, -0.19), "right_foot_index": (-0.13, -0.89, -0.19),
    })
    return p


def canonical_input_points(depth_scale=0.65):
    """Canonical T-pose expressed in the TD normalized-data coordinates.

    ``pose_tracking/math3`` has already converted MediaPipe's image-space y
    coordinate to y-up.  Depth still needs the camera-to-rig sign conversion.
    This helper is mainly for fixtures.
    """
    return {name: (point[0], point[1], -point[2] / depth_scale) for name, point in canonical_points().items()}


def pose_frames(p, limb_state=None, dt=1.0/60.0):
    hip = midpoint(p["left_hip"], p["right_hip"])
    shoulder = midpoint(p["left_shoulder"], p["right_shoulder"])
    torso_y = sub(shoulder, hip)
    pelvis_x = sub(p["right_hip"], p["left_hip"])
    shoulder_x = sub(p["right_shoulder"], p["left_shoulder"])
    pelvis = frame_from_y_normal(torso_y, cross(pelvis_x, torso_y))
    upper = frame_from_y_normal(torso_y, cross(shoulder_x, torso_y), tuple(row[2] for row in pelvis))
    pelvis_q, upper_q = matrix_to_quat(pelvis), matrix_to_quat(upper)
    frames = {
        "mixamorig_Hips": pelvis,
        "mixamorig_Spine": quat_to_matrix(quat_slerp(pelvis_q, upper_q, 0.28)),
        "mixamorig_Spine1": quat_to_matrix(quat_slerp(pelvis_q, upper_q, 0.55)),
        "mixamorig_Spine2": quat_to_matrix(quat_slerp(pelvis_q, upper_q, 0.82)),
    }
    torso_normal = tuple(row[2] for row in upper)
    ear = midpoint(p["left_ear"], p["right_ear"])
    neck = midpoint(shoulder, ear)
    head_y = sub(ear, neck)
    head_x = sub(p["right_ear"], p["left_ear"])
    head = frame_from_y_normal(head_y, cross(head_x, head_y), torso_normal)
    frames["mixamorig_Neck"] = quat_to_matrix(quat_slerp(upper_q, matrix_to_quat(head), 0.45))
    frames["mixamorig_Head"] = head

    for side in ("Left", "Right"):
        key = side.lower()
        s, e, w = p[f"{key}_shoulder"], p[f"{key}_elbow"], p[f"{key}_wrist"]
        upper_dir, lower_dir = sub(e, s), sub(w, e)
        if limb_state is not None:
            arm_normal = stable_limb_normal(upper_dir, lower_dir, torso_normal, limb_state, side + 'Arm', dt)
        else:
            arm_normal = torso_normal
        frames[f"mixamorig_{side}Shoulder"] = _frame_segment(shoulder, s, torso_normal, torso_normal)
        frames[f"mixamorig_{side}Arm"] = _frame_segment(s, e, arm_normal, torso_normal)
        frames[f"mixamorig_{side}ForeArm"] = _frame_segment(e, w, arm_normal, torso_normal)
        hand_center = midpoint(p[f"{key}_index"], p[f"{key}_pinky"])
        hand_x = sub(p[f"{key}_index"], p[f"{key}_pinky"])
        hand_y = sub(hand_center, w)
        frames[f"mixamorig_{side}Hand"] = frame_from_y_normal(hand_y, cross(hand_x, hand_y), arm_normal)

        h, k, a = p[f"{key}_hip"], p[f"{key}_knee"], p[f"{key}_ankle"]
        thigh, shin = sub(k, h), sub(a, k)
        leg_normal = cross(thigh, shin)
        if length(leg_normal) < 1e-5:
            leg_normal = torso_normal
        frames[f"mixamorig_{side}UpLeg"] = _frame_segment(h, k, leg_normal, torso_normal)
        frames[f"mixamorig_{side}Leg"] = _frame_segment(k, a, leg_normal, torso_normal)
        foot_center = midpoint(p[f"{key}_heel"], p[f"{key}_foot_index"])
        foot_dir = sub(foot_center, a)
        foot_normal = cross(shin, foot_dir)
        frames[f"mixamorig_{side}Foot"] = frame_from_y_normal(foot_dir, foot_normal, leg_normal)
        toe_dir = sub(p[f"{key}_foot_index"], p[f"{key}_heel"])
        frames[f"mixamorig_{side}ToeBase"] = frame_from_y_normal(toe_dir, foot_normal, leg_normal)
    return frames


@dataclass
class OneEuro:
    min_cutoff: float = 1.2
    beta: float = 0.22
    derivative_cutoff: float = 1.0
    time: float | None = None
    raw: float | None = None
    filtered: float | None = None
    derivative: float = 0.0

    @staticmethod
    def alpha(cutoff, dt):
        return 1.0 / (1.0 + 1.0 / (2.0 * math.pi * cutoff * dt))

    def update(self, value, time_s):
        if self.time is None:
            self.time, self.raw, self.filtered = time_s, value, value
            return value
        dt = clamp(time_s - self.time, 1.0 / 240.0, 0.25)
        derivative = (value - self.raw) / dt
        da = self.alpha(self.derivative_cutoff, dt)
        self.derivative += da * (derivative - self.derivative)
        cutoff = self.min_cutoff + self.beta * abs(self.derivative)
        self.filtered += self.alpha(cutoff, dt) * (value - self.filtered)
        self.time, self.raw = time_s, value
        return self.filtered


class YBotRetargeter:
    def __init__(self, *, min_cutoff=1.2, beta=0.22, depth_scale=0.65,
                 max_angular_speed=540.0, hold_seconds=0.25, fade_seconds=0.65,
                 wrist_mirror=False):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.depth_scale = depth_scale
        self.max_angular_speed = max_angular_speed
        self.hold_seconds = hold_seconds
        self.fade_seconds = fade_seconds
        self.wrist_mirror = wrist_mirror
        self.hand_bind_frames = {}
        self.filters = {}
        self.rest_human = pose_frames(canonical_points())
        self.last_points = None
        self.last_valid_time = None
        self.last_time = None
        self.previous_quat = {}
        self.joint_twist = {}
        self.limb_state = {}
        self.previous_euler = dict(MODEL_REST_EULER)
        self.model_rest_local = {name: euler_xyz_to_matrix(value) for name, value in MODEL_REST_EULER.items()}
        self.model_rest_global = {}
        for name in PARENTS:
            parent = PARENTS[name]
            self.model_rest_global[name] = self.model_rest_local[name] if parent is None else mat_mul(self.model_rest_global[parent], self.model_rest_local[name])
        self._update_alignment()

    def _update_alignment(self):
        # Bind offset lives in the human frame's LOCAL coordinates. Multiplying
        # this offset on the left rotates motion in the wrong world axes.
        self.alignment = {name: mat_mul(mat_transpose(self.rest_human[name]), self.model_rest_global[name]) for name in PARENTS}

    def calibrate(self, points=None):
        """Use a visible T-pose as the human rest frame; canonical rest is default."""
        points = points or self.last_points
        if not points:
            return False
        self.rest_human = pose_frames(points)
        self._update_alignment()
        self.previous_quat.clear()
        self.joint_twist.clear()
        self.limb_state.clear()
        self.previous_euler = dict(MODEL_REST_EULER)
        return True

    def _filter_points(self, points, time_s):
        converted = {}
        for name in LANDMARK_NAMES:
            point = points[name]
            # The input comes from pose_tracking/math3, whose ``*:y`` scope
            # already applies ``1-y``.  Flipping it again here made the model
            # move vertically in the opposite direction from the performer.
            x, y, z = float(point[0]), float(point[1]), -float(point[2]) * self.depth_scale
            converted[name] = tuple(self.filters.setdefault((name, axis), OneEuro(self.min_cutoff, self.beta)).update(value, time_s) for axis, value in enumerate((x, y, z)))
        # Remove translation and normalize scale.  Frames use directions, but this
        # also makes degeneracy thresholds stable for near/far camera positions.
        center = midpoint(converted["left_hip"], converted["right_hip"])
        shoulder_width = length(sub(converted["left_shoulder"], converted["right_shoulder"]))
        torso = length(sub(midpoint(converted["left_shoulder"], converted["right_shoulder"]), center))
        scale = max(shoulder_width, torso, 1e-4)
        return {name: mul(sub(point, center), 1.0 / scale) for name, point in converted.items()}

    @staticmethod
    def _unwrap(euler, previous):
        # XYZ has two equivalent Euler branches. Choose the nearest whole
        # triple, not just each principal angle, when crossing +/-90 pitch.
        x, y, z = euler
        alternatives = (euler, (x + 180.0, 180.0 - y, z + 180.0))
        candidates = [tuple(v + 360.0 * round((old - v) / 360.0) for v, old in zip(candidate, previous)) for candidate in alternatives]
        return min(candidates, key=lambda c: sum((v-old)**2 for v,old in zip(c,previous)))

    def _solve_frames(self, human_frames, time_s, blend=1.0, confidence=None):
        desired_global = {name: mat_mul(human_frames[name], self.alignment[name]) for name in PARENTS}
        for name,bind_frame in self.hand_bind_frames.items():
            # The mesh's actual MCP geometry defines its palm, not a guessed
            # T-pose normal. Both detectors already see the mirrored camera.
            desired_global[name]=mat_mul(human_frames[name],mat_transpose(bind_frame))
            forearm=PARENTS[name]
            relative=mat_mul(mat_transpose(desired_global[forearm]),desired_global[name])
            delta=matrix_to_quat(mat_mul(mat_transpose(self.model_rest_local[name]),relative))
            # Pronation/supination belongs primarily to the forearm. The old
            # elbow-plane-only forearm forced all palm roll into the wrist,
            # where its 90 degree bound turned a front palm into an edge palm.
            twist=quat_normalize((delta[0],0.,delta[2],0.))
            desired_global[forearm]=mat_mul(desired_global[forearm],quat_to_matrix(twist))
        result = {}
        dt = 1.0 / 60.0 if self.last_time is None else clamp(time_s - self.last_time, 1.0 / 240.0, 0.1)
        solved_global = {}
        for name, parent in PARENTS.items():
            parent_global = solved_global[parent] if parent else ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
            local = mat_mul(mat_transpose(parent_global), desired_global[name])
            delta = mat_mul(mat_transpose(self.model_rest_local[name]), local)
            delta_q=matrix_to_quat(delta)
            if self.wrist_mirror and name.endswith('Hand') and name not in self.hand_bind_frames:delta_q=mirror_wrist_twist(delta_q)
            limited_delta,twist=constrain_arm_joint(delta_q,name,self.joint_twist.get(name))
            if twist is not None:self.joint_twist[name]=twist
            target = matrix_to_quat(mat_mul(self.model_rest_local[name], quat_to_matrix(limited_delta)))
            rest_q = matrix_to_quat(self.model_rest_local[name])
            target = quat_slerp(rest_q, target, blend * (confidence or {}).get(name, 1.0))
            previous = self.previous_quat.get(name, rest_q)
            angle = quat_angle(previous, target)
            max_step = math.radians(self.max_angular_speed) * dt
            if angle > max_step and angle > EPS:
                target = quat_slerp(previous, target, max_step / angle)
                angle = max_step
            speed = math.degrees(angle) / max(dt, EPS)
            cutoff = 2.4 + 0.006 * speed
            alpha = 1.0 - math.exp(-2.0 * math.pi * cutoff * dt)
            output_q = quat_slerp(previous, target, alpha)
            # The final output must satisfy the joint constraint too, including
            # transitions from a previous pose/calibration near a boundary.
            if name.endswith(('Hand','ForeArm')):
                output_delta=matrix_to_quat(mat_mul(mat_transpose(self.model_rest_local[name]),quat_to_matrix(output_q)))
                output_delta,_=constrain_arm_joint(output_delta,name)
                output_q=matrix_to_quat(mat_mul(self.model_rest_local[name],quat_to_matrix(output_delta)))
            self.previous_quat[name] = output_q
            local_matrix = quat_to_matrix(output_q)
            solved_global[name] = mat_mul(parent_global, local_matrix)
            euler = self._unwrap(matrix_to_euler_xyz(local_matrix), self.previous_euler[name])
            self.previous_euler[name] = euler
            result[name] = euler
        self.last_time = time_s
        return result

    def update(self, points, time_s, visibility=None):
        """Return (absolute local Euler rotations, tracking status, quality)."""
        valid = bool(points) and all(name in points and all(math.isfinite(float(v)) for v in points[name][:3]) for name in LANDMARK_NAMES)
        if valid:
            filtered = self._filter_points(points, time_s)
            body_scale = length(sub(filtered["left_shoulder"], filtered["right_shoulder"]))
            valid = body_scale > 0.05
        if valid:
            self.last_points = filtered
            self.last_valid_time = time_s
            confidence = {}
            if visibility:
                def weight(names):
                    return clamp((min(visibility.get(n, 1.0) for n in names) - 0.20) / 0.40, 0.0, 1.0)
                torso = weight(('left_hip', 'right_hip', 'left_shoulder', 'right_shoulder'))
                for name in ('Hips', 'Spine', 'Spine1', 'Spine2'):
                    confidence['mixamorig_' + name] = torso
                for side in ('Left', 'Right'):
                    key = side.lower()
                    for bone, joints in (
                        ('Shoulder', ('shoulder',)), ('Arm', ('shoulder','elbow')),
                        ('ForeArm', ('elbow','wrist')), ('Hand', ('wrist','index','pinky')),
                        ('UpLeg', ('hip','knee')), ('Leg', ('knee','ankle')),
                        ('Foot', ('ankle','heel','foot_index')), ('ToeBase', ('heel','foot_index')),
                    ):
                        confidence['mixamorig_' + side + bone] = weight(tuple(key + '_' + j for j in joints))
                confidence['mixamorig_Head'] = confidence['mixamorig_Neck'] = weight(('left_ear','right_ear'))
            quality = sum(confidence.values()) / len(confidence) if confidence else 1.0
            dt = 1.0/60.0 if self.last_time is None else clamp(time_s-self.last_time, 1.0/240.0, 0.1)
            return self._solve_frames(pose_frames(filtered, self.limb_state, dt), time_s, confidence=confidence), "tracking", quality
        age = float("inf") if self.last_valid_time is None else max(0.0, time_s - self.last_valid_time)
        if self.previous_quat and age <= self.hold_seconds:
            return dict(self.previous_euler), "holding", 0.0
        fade = 0.0 if not math.isfinite(age) else clamp(1.0 - (age - self.hold_seconds) / self.fade_seconds, 0.0, 1.0)
        if fade<=0:self.joint_twist.clear()
        return self._solve_frames(self.rest_human, time_s, blend=fade), "lost" if fade <= 0.0 else "fading", 0.0


def rest_output():
    return dict(MODEL_REST_EULER)

"""Script CHOP callbacks for /project1/script1 in the user's Y_Bot project.

The Text DAT loads this external file on project start.  Keeping the substantial
implementation in a Python file makes the node auditable without changing the
runtime design: the Script CHOP remains the cook/retarget/output authority.
"""
from pathlib import Path
import json
import math
import sys
import time

ROOT = Path(project.folder)
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


_last_report = 0.0
_active_solver = None
tracking_status = 'waiting'


def _solver(script_op):
    global _active_solver
    solver = _active_solver
    if solver is None:
        solver = YBotRetargeter(
            min_cutoff=1.2,
            beta=0.22,
            depth_scale=0.65,
            max_angular_speed=540.0,
            hold_seconds=0.25,
            fade_seconds=0.65,
        )
        _active_solver = solver
        if 'op' in globals():
            geometry=op('/project1/hand_geometry')
            if geometry is not None:
                solver.hand_bind_frames=json.loads(geometry.text)['palm_frames']
    return solver


def _sample(channel):
    return float(channel[0])


def _read_points(chop):
    if chop is None:
        return None
    result = {}
    try:
        for index, name in enumerate(LANDMARK_NAMES):
            point = tuple(_sample(chop[name + ":" + axis]) for axis in "xyz")
            if not all(math.isfinite(v) for v in point):
                return None
            # When visibility exists, reject only very uncertain articulated
            # joints.  Older MediaPipe TD components expose xyz only.
            visibility = 1.0
            for channel_name in (name + ":visibility", name + ":presence", "visibility" + str(index)):
                channel = chop[channel_name]
                if channel is not None:
                    visibility = min(visibility, _sample(channel))
            if visibility < 0.20 and name in {
                "left_shoulder", "right_shoulder",
            }:
                return None
            result[name] = point
    except Exception:
        return None
    return result


def _read_visibility(chop):
    result = {}
    if chop is None:
        return result
    for index, name in enumerate(LANDMARK_NAMES):
        values = []
        for key in (name + ':visibility', name + ':presence', 'visibility' + str(index)):
            channel = chop[key]
            if channel is not None:
                value = _sample(channel)
                values.append(value if math.isfinite(value) else 0.0)
        result[name] = min(values) if values else 1.0
    return result

def _refine_palms(points,source,visibility=None):
    """Hand MCPs are more stable than Pose's approximate finger tips."""
    if points is None or source is None:return
    arrived=source.fetch('hand_pose_arrived',None)
    if arrived is None or not 0<=time.monotonic()-arrived<.35:return
    try:
        packet=json.loads(source.op('hand_results').text)
        data=packet.get('handResults',packet.get('gestureResults',{}))
        images=data.get('landmarks',[]);worlds=data.get('worldLandmarks',[]);labels=data.get('handednesses',data.get('handedness',[]))
        poses=json.loads(source.op('pose_results').text).get('poseResults',{}).get('landmarks',[])
        for i,side in assign_hand_sides(images,poses[0] if poses else [],labels).items():
            label=labels[i][0] if i<len(labels) and labels[i] else {}
            if float(label.get('score',0))<.55:continue
            hp=images[i];key=side.lower();anchor=points[key+'_wrist']
            # World hand coordinates are isotropic. Image x/y are normalized
            # by different dimensions and cannot be mixed as metric axes.
            metric=i<len(worlds) and len(worlds[i])==21
            if metric:hp=worlds[i]
            base=hp[0]
            aspect=packet.get('resolution',{}).get('width',1280)/max(1,packet.get('resolution',{}).get('height',720))
            scale=.9 if metric else 1.
            for name,j in (('index',5),('pinky',17)):
                p=hp[j]
                # Undo solver's legacy depth compression for these metric offsets.
                v=(anchor[0]+scale*(p['x']-base['x']),anchor[1]-scale*(p['y']-base['y'])/(1 if metric else aspect),anchor[2]+scale*(p['z']-base['z'])/.65)
                if all(math.isfinite(x) for x in v):points[key+'_'+name]=v
            if visibility is not None:
                for name in ('wrist','index','pinky'):visibility[key+'_'+name]=max(visibility.get(key+'_'+name,0),float(label['score']))
    except (ValueError,KeyError,TypeError,IndexError):return


def _write_rotation(script_op, bone, rotation):
    for axis, value in zip("xyz", rotation):
        script_op.appendChan(bone + "_r" + axis)[0] = float(value)


def _collect_diagnostics(parent_op):
    """Collect TD diagnostics without allowing monitoring to break cooking."""
    result = {}
    for output_name, method_name in (
        ("errors", "errors"),
        ("warnings", "warnings"),
        ("script_errors", "scriptErrors"),
    ):
        method = getattr(parent_op, method_name, None)
        try:
            result[output_name] = method(recurse=True) if callable(method) else ""
        except Exception:
            result[output_name] = ""
    return result


def _write_health(script_op, status, rotations):
    """Small heartbeat used to verify the saved project in TouchPlayer."""
    global _last_report
    now = time.monotonic()
    if now - _last_report < 1.0:
        return
    _last_report = now
    report = {
        "timestamp_ms": int(time.time() * 1000),
        "status": status,
        "bones": len(rotations),
        "channels": int(script_op.numChans),
        "td_build": str(app.build),
    }
    report.update(_collect_diagnostics(script_op.parent()))
    path = ROOT / ".runtime" / "yb_td_health.json"
    temporary = ROOT / ".runtime" / "yb_td_health.tmp"
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        temporary.replace(path)
    except PermissionError:
        pass


def onSetupParameters(scriptOp):
    page = scriptOp.appendCustomPage("Retarget") if not scriptOp.customPages else scriptOp.customPages[0]
    if getattr(scriptOp.par, 'Calibrate', None) is None:
        page.appendPulse("Calibrate", label="Calibrate visible T-pose")
    return


def onPulse(par):
    if par.name == "Calibrate":
        ok = _solver(par.owner).calibrate()
        par.owner.store("calibration_status", "manual" if ok else "no valid pose")
    return


def onCook(scriptOp):
    global tracking_status
    scriptOp.clear()
    scriptOp.numSamples = 1
    points = _read_points(scriptOp.inputs[0] if scriptOp.inputs else None)
    # Persisted CHOP samples are not evidence of a live camera. The WebSocket
    # callback records actual pose packet arrival using a monotonic clock.
    source=None
    if 'op' in globals():
        source = op('/project1/MediaPipe')
        arrived = source.fetch('retarget_pose_arrived', None) if source else None
        if arrived is None or not 0<=time.monotonic()-arrived<=.5:
            points = None
    timestamp = float(absTime.seconds)
    visibility = _read_visibility(scriptOp.inputs[0] if scriptOp.inputs else None)
    _refine_palms(points,source,visibility)
    solver=_solver(scriptOp)
    solver.wrist_mirror=bool(getattr(getattr(scriptOp,'par',None),'Wristmirror',False))
    rotations, status, quality = solver.update(points, timestamp, visibility=visibility)
    for bone in MODEL_REST_EULER:
        _write_rotation(scriptOp, bone, rotations[bone])
    scriptOp.appendChan("tracking")[0] = 1.0 if status == "tracking" else 0.0
    scriptOp.appendChan("holding")[0] = 1.0 if status == "holding" else 0.0
    scriptOp.appendChan("quality")[0] = quality
    tracking_status = status
    # Never inspect numChans, parent errors or dependent bones while this CHOP
    # is cooking: those reads can recursively request this very cook.
    # Diagnostics run in the separate Execute DAT after cooking completes.
    return
