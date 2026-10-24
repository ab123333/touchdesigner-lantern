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

ROOT = Path(project.folder) if 'project' in globals() else Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from tdmotion.rig_retarget import LANDMARK_NAMES, MODEL_REST_EULER, YBotRetargeter, assign_hand_sides

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
    (ROOT / ".runtime").mkdir(exist_ok=True)
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
