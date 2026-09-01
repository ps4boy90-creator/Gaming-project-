#!/usr/bin/env python3
"""
Validate the scene files against each other and against the deduction chain.

The failure modes this catches are the ones that are invisible until a player
is stuck: a door pointing at a scene that does not exist, a spawn id nothing
provides, a clue flag no deduction listens for, and -- worst of all -- a
deduction that can never fire because its evidence is behind a door that its
own flag unlocks.

    python3 tools/check_scenes.py
"""

import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENES_DIR = os.path.join(ROOT, 'src', 'scenes')

problems = []
warnings = []


def load_manifest():
    src = open(os.path.join(SCENES_DIR, 'manifest.js')).read()
    block = src[src.index('export const SCENES'):src.index('};', src.index('export const SCENES'))]
    return re.findall(r"(\w+):\s*'([^']+)'", block)


def load_deductions():
    src = open(os.path.join(ROOT, 'src', 'game', 'deductions.js')).read()
    out = []
    for chunk in src.split('  {\n    id:')[1:]:
        did = re.match(r"\s*'([^']+)'", chunk).group(1)
        req = re.search(r"requires:\s*\[([^\]]*)\]", chunk).group(1)
        requires = re.findall(r"'([^']+)'", req)
        needed = re.search(r"needed:\s*(\d+)", chunk)
        sets = re.search(r"setsFlag:\s*'([^']*)'", chunk)
        out.append({
            'id': did,
            'requires': requires,
            'needed': int(needed.group(1)) if needed else len(requires),
            'setsFlag': sets.group(1) if sets else '',
        })
    return out


def main():
    manifest = load_manifest()
    deductions = load_deductions()

    scenes = {}
    for sid, path in manifest:
        full = os.path.join(ROOT, path)
        if not os.path.exists(full):
            problems.append(f'manifest points at a missing file: {path}')
            continue
        scenes[sid] = json.load(open(full))

    sets_flag = defaultdict(list)     # flag -> [scene]
    reads_flag = defaultdict(list)
    spawns = defaultdict(set)

    for sid, data in scenes.items():
        if data.get('id') != sid:
            problems.append(f"{sid}: internal id is '{data.get('id')}'")
        for e in data.get('entities', []):
            p = e.get('props', {})
            if e['type'] == 'player_start':
                spawns[sid].add(p.get('id', ''))
            if p.get('setsFlag'):
                sets_flag[p['setsFlag']].append(sid)
            if p.get('itemFlag'):
                sets_flag[p['itemFlag']].append(sid)
            if p.get('requiresFlag'):
                reads_flag[p['requiresFlag']].append(sid)

    for d in deductions:
        if d['setsFlag']:
            sets_flag[d['setsFlag']].append('deduction:' + d['id'])

    # doors point somewhere real, at a spawn that exists
    for sid, data in scenes.items():
        for e in data.get('entities', []):
            if e['type'] != 'door':
                continue
            to = e['props'].get('to')
            if to not in scenes:
                problems.append(f"{sid}/{e['id']}: door targets unknown scene '{to}'")
                continue
            spawn = e['props'].get('spawn')
            if spawn not in spawns[to]:
                problems.append(f"{sid}/{e['id']}: door targets '{to}' spawn '{spawn}', "
                                f"which has {sorted(spawns[to])}")

    # every gate is openable by something
    for flag, readers in reads_flag.items():
        if flag not in sets_flag:
            problems.append(f"flag '{flag}' gates {readers} but nothing sets it")

    # every clue a deduction wants is actually placed
    for d in deductions:
        placed = [f for f in d['requires'] if f in sets_flag]
        if len(placed) < d['needed']:
            problems.append(f"deduction '{d['id']}' needs {d['needed']} of its clues but only "
                            f"{len(placed)} are placed anywhere: missing "
                            f"{sorted(set(d['requires']) - set(placed))}")
        elif len(placed) < len(d['requires']):
            warnings.append(f"deduction '{d['id']}': {sorted(set(d['requires']) - set(placed))} "
                            f"not placed (still satisfiable with {len(placed)})")

    # a deduction must not gate the room its own evidence is in
    gate_of = {}
    for sid, data in scenes.items():
        for e in data.get('entities', []):
            if e['type'] == 'door' and e['props'].get('requiresFlag'):
                gate_of.setdefault(e['props']['to'], set()).add(e['props']['requiresFlag'])
    for d in deductions:
        if not d['setsFlag']:
            continue
        blocked = [s for s, gates in gate_of.items() if d['setsFlag'] in gates]
        for scene_id in blocked:
            here = [f for f in d['requires'] if scene_id in sets_flag.get(f, [])]
            if len(set(d['requires']) - set(here)) < d['needed']:
                problems.append(f"deduction '{d['id']}' gates '{scene_id}', but too much of its "
                                f"evidence is inside it: {here}")

    # clue flags nothing listens for
    listened = {f for d in deductions for f in d['requires']}
    for flag, where in sets_flag.items():
        if flag.startswith('clue_') and flag not in listened:
            warnings.append(f"clue flag '{flag}' (set in {where}) feeds no deduction")

    for w in warnings:
        print(f'  warn   {w}')
    for p in problems:
        print(f'  ERROR  {p}')

    print(f'\n{len(scenes)} scenes, {sum(len(s.get("entities", [])) for s in scenes.values())} entities, '
          f'{len(deductions)} deductions, {len(sets_flag)} flags')
    if problems:
        print(f'{len(problems)} problem(s).')
        return 1
    print('All scene checks passed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
