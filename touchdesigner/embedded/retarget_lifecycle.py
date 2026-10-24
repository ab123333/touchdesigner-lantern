"""Startup and frame-end health reporting, outside Script CHOP cooking."""
import json
import time
from pathlib import Path

_last_report = 0.0
_last_port = None

def onStart():
    Path(project.folder, '.runtime').mkdir(exist_ok=True)
    op('/project1/Y_Bot/exportAnim').export = False
    source = op('/project1/MediaPipe')
    source.unstore('retarget_pose_arrived')
    raw = source.op('pose_results')
    raw.text = '{"poseResults":{"landmarks":[],"worldLandmarks":[]},"resolution":{"width":1280,"height":720}}'
    op('/project1/script1').cook(force=True)
    run("op('/project1/MediaPipe/webBrowser1/webrender1').par.reloadsrc.pulse()", delayFrames=30)

def onFrameEnd(frame):
    global _last_report, _last_port
    # The camera is an asynchronous Web Render source. Demand it even when its
    # viewer is closed, otherwise a headless rig can keep reading stale JSON.
    renderer = op('/project1/MediaPipe/webBrowser1/webrender1')
    if not renderer.cookedThisFrame:
        renderer.cook(force=True)
    # Autoport in the bundled MediaPipe component updated the server but left
    # the browser URL on the saved port. Keep all three endpoints consistent.
    source = op('/project1/MediaPipe')
    port = int(source.op('webserver1').par.port.eval())
    if port != _last_port:
        from urllib.parse import urlsplit, urlunsplit
        browser = source.op('webBrowser1')
        old = urlsplit(str(browser.par.Address.eval()))
        url = urlunsplit(('http', 'localhost:' + str(port), old.path, old.query, ''))
        source.par.Mediapipeport = port
        source.op('current_url').text = url
        browser.par.Address = url
        _last_port = port
    now = time.monotonic()
    if now - _last_report < 2:
        return
    _last_report = now
    script = op('/project1/script1')
    root = op('/project1')
    report = {
        'timestamp': time.time(), 'project': project.name,
        'status': op('/project1/script1_callbacks').module.tracking_status,
        'channels': script.numChans, 'cook_ms': script.cpuCookTime,
        'errors': root.errors(recurse=True), 'warnings': root.warnings(recurse=True),
        'script_errors': root.scriptErrors(recurse=True),
        'pose_packet_received': source.fetch('retarget_pose_arrived', None) is not None,
    }
    try:
        Path(project.folder, '.runtime', 'retarget_health.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    except OSError:
        pass
