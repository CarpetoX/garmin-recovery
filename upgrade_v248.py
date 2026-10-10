#!/usr/bin/env python3
"""Garmin Recovery V2.4.8: safe, idempotent patch of checked-in sources.

Run from repository root inside GitHub Actions. No private keys and no
physiological recovery/readiness score thresholds are modified.
"""
from pathlib import Path


def exact_replace(path, old, new, title):
    path = Path(path)
    content = path.read_text(encoding='utf-8')
    if new in content:
        print(f'Already applied: {title}')
        return
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f'{title}: expected exactly one anchor, found {count} ({path})')
    path.write_text(content.replace(old, new, 1), encoding='utf-8')
    print(f'Applied: {title}')


def patch_sync():
    exact_replace(
        '.github/workflows/sync.yml',
        'on:\n  workflow_dispatch:\n\n  schedule:',
        'on:\n  workflow_dispatch:\n'
        '  # Backup independently triggered by Apps Script, once its Code.gs is configured.\n'
        '  repository_dispatch:\n    types: [garmin-sync]\n\n  schedule:',
        'Allow Apps Script repository_dispatch without removing manual or scheduled runs',
    )


def patch_report_clock():
    exact_replace(
        'report_delivery_gate.py',
        "SLOTS = ((8, 30, '0830', '08:45'), (16, 45, '1645', '17:00'), (22, 45, '2245', '23:00'))",
        "SLOTS = ((8, 30, '0830', '09:05'), (16, 45, '1645', '17:10'), (22, 45, '2245', '23:10'))",
        'Align base gate report targets with 09:05 / 17:10 / 23:10',
    )


def patch_night_shift_sleep():
    p = 'morning_sleep_gate.py'
    exact_replace(
        p,
        '    age_minutes=round((now-end).total_seconds()/60,1) if confirmed else None\n    fresh_sleep=',
        '    age_minutes=round((now-end).total_seconds()/60,1) if confirmed else None\n'
        '    # After a night shift, a 03:00-05:00 episode can precede the main sleep.\n'
        '    # Do not declare a definitive morning report from an episode ending before 07:00.\n'
        '    early_post_shift_episode=bool(post_night_shift and confirmed and end.hour<7)\n'
        '    fresh_sleep=',
        'Protect early post-TN sleep fragments',
    )
    exact_replace(
        p,
        '    if confirmed:\n        if age_minutes<30:',
        "    if confirmed:\n        if early_post_shift_episode:\n            state='post_night_shift_early_sleep_pending'\n        elif age_minutes<30:",
        'Keep early post-TN sleep provisional',
    )
    exact_replace(
        p,
        "        'possible_sleep_in_progress':not confirmed,\n        'wake_confirmed':confirmed,\n        'post_night_shift':post_night_shift,",
        "        'possible_sleep_in_progress':not confirmed or early_post_shift_episode,\n"
        "        'wake_confirmed':confirmed and not early_post_shift_episode,\n"
        "        'episode_end_confirmed':confirmed,\n"
        "        'post_night_shift':post_night_shift,\n"
        "        'early_post_shift_episode':early_post_shift_episode,",
        'Separate confirmed sleep episode from definitive wake-up',
    )
    exact_replace(
        p,
        "          'post_night_shift_sleep_pending':'Posible sueño diurno o fragmentado tras turno de noche; no asumir despertar.',",
        "          'post_night_shift_sleep_pending':'Posible sueño diurno o fragmentado tras turno de noche; no asumir despertar.',\n"
        "          'post_night_shift_early_sleep_pending':'Episodio temprano tras TN confirmado; puede faltar el descanso principal.',",
        'Add explicit post-TN pending message',
    )


def patch_sensor_freshness():
    p = 'report_sleep_integration.py'
    exact_replace(
        p,
        'def build(chain, file_times, now):\n',
        '''def live_sensor_summary(provenance, now):
    """Audit age of actual HR/Body Battery samples; NEVER alter recovery scores."""
    details = {}
    for key in ('heart_rate_live', 'body_battery_live'):
        source = provenance.get(key) if isinstance(provenance, dict) else None
        source = source if isinstance(source, dict) else {}
        measured = _parse(source.get('measured_at'))
        minutes = round((now - measured).total_seconds() / 60, 1) if measured else None
        if minutes is None:
            state = 'unknown'
        elif minutes < -2:
            state = 'invalid_future_measurement'
        elif minutes > 90 or source.get('state') in ('delayed', 'old_measurement'):
            state = 'delayed'
        else:
            state = 'recent'
        details[key] = {
            'state': state,
            'measured_at': source.get('measured_at'),
            'age_minutes_at_report': minutes,
            'source_state': source.get('state'),
        }
    attention = [key for key, item in details.items()
                 if item['state'] in ('delayed', 'invalid_future_measurement', 'unknown')]
    return {
        'live_measurements': details,
        'not_confirmed_recent': attention,
        'interpretation': 'caution' if attention else 'available_recent',
        'note': ('Data generation time never proves a new sensor reading. '
                 'Sleep HRV is measured during sleep, not continuously.'),
    }


def build(chain, file_times, now):
''',
        'Audit live sensor freshness with actual sample timestamps',
    )
    exact_replace(
        p,
        "    cert['gate_version'] = '2.4.7'",
        "    cert['gate_version'] = '2.4.8'\n"
        "    cert['live_sensor_quality'] = live_sensor_summary(\n"
        "        cert.get('measurement_provenance', {}), now)",
        'Expose sample-age audit in readiness certificate',
    )
    exact_replace(
        p,
        "    data['morning_sleep'] = cert.get('morning_sleep', {})\n",
        "    data['morning_sleep'] = cert.get('morning_sleep', {})\n"
        "    data['live_sensor_quality'] = cert.get('live_sensor_quality', {})\n",
        'Store source freshness in historical report snapshot',
    )


def patch_strength():
    p = Path('muscle_load.py')
    source = p.read_text(encoding='utf-8')
    if 'def equipment_for(exercise):' in source:
        print('Already applied: strength exercise patterns / equipment provenance')
    else:
        begin = source.find('PATTERNS = {\n')
        end = source.find('\ndef num(v):', begin)
        if begin < 0 or end < 0 or "'horizontal_push': ('bench press'" not in source[begin:end]:
            raise RuntimeError('muscle_load.py pattern block differs from audited V2.4.7')
        new_block = '''PATTERNS = {
    'hinge': ('peso muerto', 'deadlift', 'rdl', 'romanian deadlift', 'good morning', 'kettlebell swing'),
    'squat': ('sentadilla', 'squat', 'thruster', 'wall ball', 'goblet squat'),
    'chest_isolation': ('aperturas de pecho', 'chest fly', 'pec deck', 'crossover'),
    'triceps_isolation': ('tríceps', 'triceps', 'pressdown', 'extensión de codo'),
    'horizontal_push': ('bench press', 'press banca', 'press de pecho', 'press inclinado',
                        'press superinclinado', 'chest press', 'push-up', 'flexion',
                        'floor press', 'fondos de pecho', 'chest dips'),
    'vertical_push': ('shoulder press', 'strict press', 'push press', 'press militar', 'jerk'),
    'vertical_pull': ('pull-up', 'dominada', 'chest-to-bar', 'toes-to-bar'),
    'horizontal_pull': ('remo', 'bent-over row', 'barbell row', 'dumbbell row'),
    'olympic_lift': ('clean', 'snatch', 'arrancada', 'cargada'),
    'single_leg': ('lunge', 'zancada', 'split squat', 'step-up'),
    'core': ('sit-up', 'situp', 'plank', 'plancha', 'abdominales', 'hollow'),
}

def equipment_for(exercise):
    """Separate free-weight, selectorized-machine, and bodyweight measures."""
    unit = str(exercise.get('load_unit') or '').casefold()
    if unit == 'kg_total_dos_mancuernas': return 'dumbbell_pair'
    if unit == 'kg_total_barra': return 'barbell'
    if unit == 'kg_total_dos_lados': return 'plate_loaded_machine'
    if unit == 'kg_indicado_maquina': return 'machine_stack'
    if unit == 'peso_corporal': return 'bodyweight'
    return 'unspecified'
'''
        p.write_text(source[:begin] + new_block + source[end:], encoding='utf-8')
        print('Applied: strength exercise patterns / equipment provenance')

    exact_replace(
        p,
        '                pattern = classify(name)\n                known_volume',
        '                pattern = classify(name)\n'
        '                equipment = equipment_for(exercise)\n'
        "                external_expected = equipment != 'bodyweight'\n"
        '                known_volume',
        'Classify resistance modality for each exercise',
    )
    exact_replace(
        p,
        "                        'exercise':name, 'movement_pattern':pattern,\n                        'verified_volume_kg'",
        "                        'exercise':name, 'movement_pattern':pattern,\n"
        "                        'equipment':equipment, 'load_unit':exercise.get('load_unit'),\n"
        "                        'external_load_applicable':external_expected,\n"
        "                        'verified_volume_kg'",
        'Preserve units and equipment in per-exercise records',
    )
    exact_replace(
        p,
        "                        'volume_complete':known_sets == total_sets,\n                        'estimated_1rm_kg'",
        "                        'volume_complete':(known_sets == total_sets) if external_expected else None,\n"
        "                        'volume_status':('complete' if known_sets == total_sets else 'partial')\n"
        "                                         if external_expected else 'bodyweight_no_external_load',\n"
        "                        'estimated_1rm_kg'",
        'Stop classifying bodyweight sessions as missing kilograms',
    )
    exact_replace(
        p,
        "    windows = {}\n    for days in (7, 28):",
        "    windows = {}\n    equipment_windows = {}\n    for days in (7, 28):",
        'Add separate 7/28 day equipment summaries',
    )
    exact_replace(
        p,
        '''        groups = defaultdict(lambda: {'verified_volume_kg':0.0,'known_sets':0,'total_sets':0,'sessions':0})
        for s in relevant:
            g = groups[s['movement_pattern']]
            g['sessions'] += 1
            g['known_sets'] += s['known_sets']
            g['total_sets'] += s['total_sets']
            g['verified_volume_kg'] += s['verified_volume_kg'] or 0
''',
        '''        groups = defaultdict(lambda: {'verified_volume_kg':0.0,'known_sets':0,'total_sets':0,'sessions':0})
        separate = defaultdict(lambda: {'verified_volume_kg':0.0,'known_sets':0,
                                        'external_sets_expected':0,'total_sets':0,'sessions':0})
        for s in relevant:
            g = groups[s['movement_pattern']]
            g['sessions'] += 1
            g['known_sets'] += s['known_sets']
            g['total_sets'] += s['total_sets']
            g['verified_volume_kg'] += s['verified_volume_kg'] or 0
            key = s['movement_pattern'] + ':' + s['equipment']
            x = separate[key]
            x['sessions'] += 1
            x['known_sets'] += s['known_sets']
            x['total_sets'] += s['total_sets']
            x['external_sets_expected'] += s['total_sets'] if s['external_load_applicable'] else 0
            x['verified_volume_kg'] += s['verified_volume_kg'] or 0
''',
        'Separate external load by resistance modality',
    )
    exact_replace(
        p,
        "                'volume_complete':v['known_sets']==v['total_sets']} for k,v in groups.items()}\n",
        "                'volume_complete':v['known_sets']==v['total_sets'],\n"
        "                'mixed_equipment_caution':True} for k,v in groups.items()}\n"
        "        equipment_windows[str(days)+'d'] = {\n"
        "            k: {**v,'verified_volume_kg':round(v['verified_volume_kg'],1),\n"
        "                'volume_complete':v['known_sets']==v['external_sets_expected']}\n"
        "            for k,v in separate.items()}\n",
        'Expose comparable breakdown without changing previous totals',
    )
    exact_replace(
        p,
        "            key = s['exercise'].casefold()",
        "            key = (s['exercise'].casefold(), s['equipment'])",
        'Do not compare 1RM estimates across different machines/implements',
    )
    exact_replace(
        p,
        "                best[key] = {'exercise':s['exercise'],'date':s['date'],\n                    'estimated_1rm_kg':s['estimated_1rm_kg']}",
        "                best[key] = {'exercise':s['exercise'],'equipment':s['equipment'],\n"
        "                    'load_unit':s['load_unit'],'date':s['date'],\n"
        "                    'estimated_1rm_kg':s['estimated_1rm_kg']}",
        'Attach equipment provenance to estimated personal bests',
    )
    exact_replace(
        p,
        "        'strength_exercises':sessions, 'movement_pattern_load':windows,\n",
        "        'strength_exercises':sessions, 'movement_pattern_load':windows,\n"
        "        'movement_pattern_load_by_equipment':equipment_windows,\n",
        'Publish equipment-separated historical loading',
    )
    exact_replace(
        p,
        "          'Patterns are exercise categories, not isolated muscle-group loads',\n",
        "          'Patterns are exercise categories, not isolated muscle-group loads',\n"
        "          'Mixed-equipment totals are not directly comparable; use load_by_equipment',\n"
        "          'Bodyweight sets do not imply external weight-volume',\n"
        "          'Machine-stack loads are not comparable to barbell loads',\n",
        'Declare limitations of equipment comparison',
    )


def patch_monitor():
    exact_replace(
        'monitor_v231.py',
        "        alerts.append({'severity': 'info', 'code': 'cron_missed_dispatch_recovered',\n                       'slots': slots.get('recovered'),",
        "        severity = 'warning' if slots.get('recovered_by_manual') else 'info'\n"
        "        alerts.append({'severity': severity, 'code': 'cron_missed_dispatch_recovered',\n"
        "                       'slots': slots.get('recovered'),",
        'Mark manual recovery as an automation warning, not a full success',
    )


def main():
    patch_sync()
    patch_report_clock()
    patch_night_shift_sleep()
    patch_sensor_freshness()
    patch_strength()
    patch_monitor()
    print('Garmin Recovery V2.4.8 patches complete; physiological scoring unchanged.')


if __name__ == '__main__':
    main()
