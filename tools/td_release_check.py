"""Embedded Execute DAT: verify portable assets after a cold project start."""
import json
import time
from pathlib import Path


def onStart():
    Path(project.folder, '.runtime').mkdir(exist_ok=True)
    run("op('/project1/release_check').module.check()", delayFrames=150)


def check():
    root = op('/project1')
    game = root.op('knight_game')
    base = Path(project.folder)
    assets = []
    missing = []
    external = []
    for node in [root] + root.findChildren():
        for par in node.pars():
            if str(par.style) not in ('File', 'Folder'):
                continue
            if par.name in ('externaltox', 'externaltoxpath'):
                continue
            try:
                value = str(par.eval())
            except Exception:
                continue
            if not value or value.startswith(('vfs:', 'http:', 'https:', 'ws:', 'wss:')):
                continue
            path = Path(tdu.expandPath(value))
            if not path.is_absolute():
                path = base / path
            path = path.resolve()
            if str(path).lower().startswith(str(Path(app.installFolder)).lower()):
                continue
            # Disabled file readers with locked geometry are not loaded at runtime.
            record = {'node': node.path, 'parameter': par.name, 'path': value, 'exists': path.exists()}
            assets.append(record)
            if not path.exists():
                if getattr(node, 'lock', False):
                    record['embedded_geometry'] = True
                else:
                    missing.append(record)
            elif not path.is_relative_to(base.resolve()):
                external.append(record)
    game.op('OUT_GAME').cook(force=True)
    report = {'project': project.name, 'td_build': str(app.build), 'time': time.time(),
              'errors': root.errors(recurse=True), 'script_errors': root.scriptErrors(recurse=True),
              'warnings': root.warnings(recurse=True), 'assets': assets, 'missing': missing,
              'outside_bundle': external,
              'slash_size': [game.op('slash_atlas').width, game.op('slash_atlas').height],
              'dash_size': [game.op('dash_atlas').width, game.op('dash_atlas').height],
              'weapon_points': game.op('equipped_weapon/imported_blade').numPoints,
              'weapon_visible_idle': bool(game.op('equipped_weapon').par.render),
              'output_size': [game.op('OUT_GAME').width, game.op('OUT_GAME').height]}
    (base / '.runtime' / 'release_check.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    game.op('OUT_GAME').save(str(base / '.runtime' / 'game_preview.png'))
