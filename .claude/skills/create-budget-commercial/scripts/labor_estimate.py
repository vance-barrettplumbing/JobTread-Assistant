#!/usr/bin/env python3
"""Barrett Plumbing commercial labor-hours estimator (mirrors BP_Commercial_Estimator_v3.1.xlsx).

Reproduces the workbook's labor math (PIPE ESTIMATE, FIXTURE ESTIMATE incl. hangers, CMU drops,
SLEEVE SCHEDULE, DEMO ESTIMATE = every line of SUMMARY "LABOR HOURS SUMMARY"), then splits the
hours into the JobTread phases (Demo / Underground / Rough-In / Finish) and lists the takeoff
quantities (pipe LF, hangers, rod, beam clamps, sleeves) used for material lines.

All rates and constants are read live from the workbook, and the wiring (which takeoff row uses
which LABOR TABLES row, which fixture uses which Table D/E hours, hanger spacing) is parsed from
the sheet's own formulas, so when Vance edits the workbook the script follows automatically.
Older v3 copies (e.g. a filled-in estimate Vance sends) still work; their known quirks are reproduced
for the sheet totals and flagged in the warnings.

Usage:
  python3 labor_estimate.py config.json [--xlsx PATH] [--format md|json]
  python3 labor_estimate.py --from-xlsx FILLED.xlsx [--format md|json]   # inputs from a filled copy
Config keys (all optional) are listed in DEFAULTS; row names accept a short unambiguous prefix.
  pipe:          {"dwv"|"cold"|"hot"|"recirc"|"air": {"4\\"": [ug_lf, in_wall_lf, ceiling_lf]}}
                 (or {"ug":..,"wall":..,"ceiling":..,"override": final_lf})
  fixtures:      {"<FIXTURE SCHEDULE row>": qty}          e.g. {"Water Closet (Flush": 6}
  qty_overrides: {"<FIXTURE ESTIMATE row>": qty}          the sheet's blue override cells
  sleeves:       [{"size": "2\\"", "wall": "CMU"|"Tilt-Up"|"Custom", "qty": n}]
  demo_pipe:     {"<DEMO ESTIMATE pipe row>": total_lf or [ug, wall, ceiling]}
  demo_fixtures: {"<DEMO ESTIMATE fixture row>": qty or {"qty": n, "cap": "Y"}}
  phase_overrides: {"hangers"|"cmu"|"sleeves"|"<FIXTURE ESTIMATE row>": "UG"|"RI"|"FIN"|"DEMO"}
  extra_hours:   [{"item": "Showers SH-1 x2", "phase": "RI", "hours": 6}]   work the sheet has no row for
                 (hours from Vance only); added to the phases, not to the sheet SUMMARY
"""
import argparse, json, math, os, re, sys
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_XLSX = os.path.join(HERE, '..', 'BP_Commercial_Estimator_v3.1.xlsx')
DEFAULTS = dict(complexity='Normal', wall_type='CMU Block', slab_on_grade='Y', crew_size=2, shift_hours=8,
                hanger_type='Single Clevis Hanger', water_material='Type L Copper',
                pipe={}, fixtures={}, qty_overrides={}, cmu_drops=0, sleeves=[],
                demo_pipe={}, demo_fixtures={}, phase_overrides={}, extra_hours=[])
PHASES = ('DEMO', 'UG', 'RI', 'FIN')
PHASE_NAMES = {'DEMO': 'Demo', 'UG': 'Underground', 'RI': 'Rough-In', 'FIN': 'Finish'}
# Phase for FIXTURE ESTIMATE hours that LABOR TABLES does not already split into "— Rough-In" /
# "— Final Set". 'UG*' = Underground when slab on grade, else Rough-In. Unlisted rows -> Finish.
PHASE_MAP = [('floor drain', 'UG*'), ('floor sink', 'UG*'), ('cleanout', 'UG*'),
             ('grease interceptor (exterior', 'UG'), ('grease interceptor (indoor', 'RI'),
             ('hose bib', 'RI'), ('wall hydrant', 'RI'), ('roof drain', 'RI'), ('trap primer', 'RI'),
             ('prv station', 'RI'), ('rpz backflow', 'RI')]
SYSTEM_NAMES = {'dwv': 'DWV', 'cold': 'Cold water', 'hot': 'Hot water', 'recirc': 'HW recirc', 'air': 'Compressed air'}
EPS = 1e-9
EM = '—'


def norm(s):
    s = str(s).lower().replace('”', '"').replace('“', '"').replace(EM, '-').replace('–', '-')
    return re.sub(r'\s+', ' ', s).strip()


def size_key(s):
    return norm(s).replace('"', '').replace(' ', '')


def match(name, labels, what):
    n = norm(name)
    hits = [l for l in labels if norm(l) == n] or [l for l in labels if norm(l).startswith(n)] or \
           [l for l in labels if n in norm(l)]
    if len(hits) != 1:
        raise ValueError(f'{what} "{name}" matched {len(hits)} rows: {hits or list(labels)}')
    return hits[0]


def ceil(x):
    return math.ceil(round(x, 9))


def phase_key(p):
    p = norm(p)
    for k, v in PHASE_NAMES.items():
        if p in (k.lower(), norm(v), norm(v).replace('-', '')):
            return k
    raise ValueError(f'Unknown phase "{p}" (use UG, RI, FIN or DEMO)')


class Book:
    def __init__(self, path):
        self.f = openpyxl.load_workbook(path)                   # formulas
        self.v = openpyxl.load_workbook(path, data_only=True)   # values cached by Excel

    def formula(self, sh, ref):
        x = self.f[sh][ref].value
        return x.replace('$', '') if isinstance(x, str) and x.startswith('=') else None

    def val(self, sh, ref):
        x = self.f[sh][ref].value
        if isinstance(x, str) and x.startswith('='):
            cached = self.v[sh][ref].value
            if cached is None:   # no cached value: evaluate plain arithmetic or a single-cell link
                f = x.replace('$', '')
                m = re.fullmatch(r"=(?:(?:'([^']+)'|(\w+))!)?([A-Z]+\d+)", f)
                if re.fullmatch(r'=[\d.\s+\-*/()]+', f):
                    cached = eval(f[1:])   # e.g. "=66.14 + 42"
                elif m:
                    cached = self.val(m.group(1) or m.group(2) or sh, m.group(3))
            return cached
        return x

    def num(self, sh, ref):
        x = self.val(sh, ref)
        return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else 0.0

    def rows(self, sh):
        return range(1, self.f[sh].max_row + 1)

    def find(self, sh, text, col='A'):
        for r in self.rows(sh):
            a = self.val(sh, f'{col}{r}')
            if isinstance(a, str) and norm(a).startswith(norm(text)):
                return r
        raise KeyError(f'{sh}: row "{text}" not found')


def load_tables(bk):
    T = {'complexity': {}, 'contingency': {}}
    for r in bk.rows('SETTINGS'):
        a = bk.val('SETTINGS', f'A{r}')
        if a in ('Normal', 'High', 'Very High') and isinstance(bk.val('SETTINGS', f'B{r}'), (int, float)):
            T['complexity'][a] = bk.num('SETTINGS', f'B{r}')
        elif isinstance(a, str) and a.startswith('Contingency'):
            T['contingency'][a.split(EM)[-1].replace('Confidence %', '').strip()] = bk.num('SETTINGS', f'B{r}')
    T['blended_rate'] = bk.num('SETTINGS', 'B11') or sum(bk.num('SETTINGS', f'B{m}') * bk.num('SETTINGS', f'B{r}')
                                                      for m, r in ((8, 5), (9, 6), (10, 7)))
    # pipe systems and takeoff rows (PIPE TAKEOFF)
    T['systems'], cur = {}, None
    for r in bk.rows('PIPE TAKEOFF'):
        a = bk.val('PIPE TAKEOFF', f'A{r}')
        if not isinstance(a, str) or bk.formula('PIPE TAKEOFF', f'A{r}'):
            continue
        u = a.upper()
        if u.startswith('SYSTEM:'):
            cur = ('recirc' if 'RECIRC' in u else 'air' if 'AIR' in u else 'dwv' if 'DWV' in u
                   else 'cold' if '(COLD)' in u else 'hot' if '(HOT)' in u else norm(a))
            T['systems'][cur] = []
        elif u.startswith('TOTAL'):
            cur = None
        elif cur and a != 'Pipe Size':
            T['systems'][cur].append(dict(row=r, size=a.strip()))
    # labor rate per takeoff row, parsed from PIPE ESTIMATE columns C/D/E
    # {material: rate}; key None = default. v3.1 water rows point at TABLE B2, whose cells pick the
    # Type L / Type K / PEX-B row from INPUT E12 with an IF chain; v3 points straight at Type L.
    def rate_options(ref):
        f = bk.formula('LABOR TABLES', ref)
        if not f:
            return {None: bk.num('LABOR TABLES', ref)}
        opts = {mat: bk.num('LABOR TABLES', r) for mat, r in re.findall(r'INPUT!E12="([^"]+)",([A-Z]+\d+)', f)}
        m = re.search(r',([A-Z]+\d+)\)+$', f)
        opts[None] = bk.num('LABOR TABLES', m.group(1)) if m else bk.num('LABOR TABLES', ref)
        return opts
    T['pipe_rates'] = {}
    for r in bk.rows('PIPE ESTIMATE'):
        for col, tcol in zip('CDE', 'BCD'):
            f = bk.formula('PIPE ESTIMATE', f'{col}{r}') or ''
            m = re.search(rf"'PIPE TAKEOFF'!{tcol}(\d+)\*'LABOR TABLES'!([A-Z]+\d+)", f)
            if m:
                T['pipe_rates'].setdefault(int(m.group(1)), {})[tcol] = rate_options(m.group(2))
    T['material_aware'] = any(len(o) > 1 for rt in T['pipe_rates'].values() for o in rt.values())
    # hangers (FIXTURE ESTIMATE hanger block)
    hr = {k: bk.find('FIXTURE ESTIMATE', k) for k in ('Single Clevis', 'Trapeze Assembly (2', 'Trapeze Assembly (3',
                                                       'Threaded Rod', 'Beam Clamp')}
    f48 = bk.formula('FIXTURE ESTIMATE', f"B{hr['Single Clevis']}")
    T['hanger_spacing'] = {int(t): float(s) for t, s in re.findall(r"CEILING\('PIPE TAKEOFF'!D(\d+)/([\d.]+),1\)", f48)}
    T['hanger_hrs'] = {k: bk.num('FIXTURE ESTIMATE', f'C{r}') for k, r in hr.items()}
    T['hanger_labels'] = {k: bk.val('FIXTURE ESTIMATE', f'A{hr[k]}') for k in ('Single Clevis', 'Trapeze Assembly (2', 'Trapeze Assembly (3')}

    def tail(key, pat, default):
        m = re.search(pat, bk.formula('FIXTURE ESTIMATE', f'B{hr[key]}') or '')
        return [float(g) for g in m.groups()] if m else default
    T['trap_div'] = {'Trapeze Assembly (2': tail('Trapeze Assembly (2', r'\)/([\d.]+),1\),0\)$', [2])[0],
                     'Trapeze Assembly (3': tail('Trapeze Assembly (3', r'\)/([\d.]+),1\),0\)$', [3])[0]}
    T['rod_per_point'] = tail('Threaded Rod', r'\*([\d.]+),0\)$', [4])[0]
    T['clamps_per_point'] = tail('Beam Clamp', r',([\d.]+),([\d.]+)\),0\)$', [1, 2])   # [single clevis, trapeze]
    # fixture schedule rows and fixture estimate rows (wired by formula)
    T['sched'] = {r: bk.val('FIXTURE SCHEDULE', f'A{r}') for r in bk.rows('FIXTURE SCHEDULE')
                  if (bk.formula('FIXTURE SCHEDULE', f'G{r}') or '').startswith('=SUM(B')}
    T['fix_rows'], end = [], bk.find('FIXTURE ESTIMATE', 'FIXTURE & SPECIALTY LABOR TOTAL')
    for r in range(1, end):
        c = bk.formula('FIXTURE ESTIMATE', f'C{r}') or ''
        comps = [(bk.val('LABOR TABLES', f'H{i}'), bk.num('LABOR TABLES', f'I{i}')) for i in re.findall(r"'LABOR TABLES'!I(\d+)", c)]
        if not comps:
            continue
        b = bk.formula('FIXTURE ESTIMATE', f'B{r}')
        m = re.search(r"'FIXTURE SCHEDULE'!G(\d+)", b or '')
        T['fix_rows'].append(dict(row=r, label=bk.val('FIXTURE ESTIMATE', f'A{r}'), comps=comps,
                                  sched=int(m.group(1)) if m else None,
                                  fixed=None if b else bk.num('FIXTURE ESTIMATE', f'B{r}')))
    # CMU block wall drops (PIPE TAKEOFF row whose A cell is =INPUT!B18)
    cr = next(r for r in bk.rows('PIPE TAKEOFF') if bk.formula('PIPE TAKEOFF', f'A{r}') == '=INPUT!B18')
    m = re.search(r'INPUT!B18="([^"]+)"', bk.formula('PIPE TAKEOFF', f'D{cr}') or '')
    T['cmu'] = dict(row=cr, hrs=bk.num('PIPE TAKEOFF', f'C{cr}'), wall=m.group(1) if m else 'CMU Block')
    # sleeves
    T['sleeves'], s0 = [], bk.find('SLEEVE SCHEDULE', 'Sleeve Size')
    for r in range(s0 + 1, bk.find('SLEEVE SCHEDULE', 'SLEEVE TOTALS')):
        if bk.val('SLEEVE SCHEDULE', f'A{r}') is None:
            continue
        kind = 'CMU' if bk.formula('SLEEVE SCHEDULE', f'B{r}') else str(bk.val('SLEEVE SCHEDULE', f'B{r}'))
        T['sleeves'].append(dict(row=r, size=bk.val('SLEEVE SCHEDULE', f'A{r}'), kind=kind,
                                 unit_cost=bk.num('SLEEVE SCHEDULE', f'D{r}'), install=bk.num('SLEEVE SCHEDULE', f'F{r}'),
                                 visits=bk.num('SLEEVE SCHEDULE', f'H{r}'), per_visit=bk.num('SLEEVE SCHEDULE', f'I{r}')))
    # demolition
    pe, fd, fe = (bk.find('DEMO ESTIMATE', t) for t in ('PIPE DEMO TOTAL', 'FIXTURE DEMOLITION', 'FIXTURE DEMO TOTAL'))
    T['demo_pipe'] = [dict(row=r, label=bk.val('DEMO ESTIMATE', f'A{r}'), rate=bk.num('DEMO ESTIMATE', f'F{r}'))
                      for r in range(1, pe) if bk.formula('DEMO ESTIMATE', f'G{r}') and
                      isinstance(bk.val('DEMO ESTIMATE', f'F{r}'), (int, float))]
    T['demo_fix'] = [dict(row=r, label=bk.val('DEMO ESTIMATE', f'A{r}'), hrs=bk.num('DEMO ESTIMATE', f'C{r}'),
                          cap=bk.num('DEMO ESTIMATE', f'G{r}'))
                     for r in range(fd, fe) if bk.formula('DEMO ESTIMATE', f'D{r}')]
    # how the sheet's PIPE DEMO TOTAL (G) adds up: {pipe row: times counted}. v3's SUM(G9:G34) also
    # covers the Cast Iron / PVC / Copper subtotal rows, so those rows are counted twice (v3.1 fixed).
    pipe_rows = {t['row'] for t in T['demo_pipe']}

    def counted(r, depth=0):
        if r in pipe_rows:
            return {r: 1}
        acc = {}
        for a, b in re.findall(r'G(\d+)(?::G(\d+))?', bk.formula('DEMO ESTIMATE', f'G{r}') or '') if depth < 4 else []:
            for x in range(int(a), int(b or a) + 1):
                for k, v in counted(x, depth + 1).items():
                    acc[k] = acc.get(k, 0) + v
        return acc
    T['demo_sheet_count'] = counted(pe)
    # v3 left cap/stub hours out of the fixture demo hours (D); v3.1 adds them there
    T['demo_cap_in_hours'] = any(re.search(rf"G{t['row']}\b", bk.formula('DEMO ESTIMATE', f"D{t['row']}") or '')
                                 for t in T['demo_fix'])
    # v3 crew-days (SETTINGS B32) summed some SUMMARY lines; v3.1 uses the SUMMARY total
    T['crew_days_from_total'] = 'SUMMARY' in (bk.formula('SETTINGS', 'B32') or '')
    return T


def inputs_from_config(cfg, T):
    c = {**DEFAULTS, **cfg}
    inp = {k: c[k] for k in ('complexity', 'wall_type', 'slab_on_grade', 'crew_size', 'shift_hours',
                             'hanger_type', 'water_material', 'cmu_drops')}
    inp['pipe'] = {}
    for sysname, sizes in c['pipe'].items():
        key = match(sysname, list(T['systems']), 'Pipe system')
        rows = {size_key(t['size']): t['row'] for t in T['systems'][key]}
        for size, v in sizes.items():
            if size_key(size) not in rows:
                raise ValueError(f'{key} size "{size}" not in PIPE TAKEOFF (have {[t["size"] for t in T["systems"][key]]})')
            if isinstance(v, dict):
                v = (v.get('ug', 0), v.get('wall', 0), v.get('ceiling', 0), v.get('override'))
            elif isinstance(v, (int, float)):
                v = (0, 0, v, None)
            inp['pipe'][rows[size_key(size)]] = (float(v[0] or 0), float(v[1] or 0), float(v[2] or 0),
                                                 v[3] if len(v) > 3 else None)
    labels = {v: r for r, v in T['sched'].items()}
    inp['sched'] = {labels[match(k, list(labels), 'Fixture')]: float(sum(v) if isinstance(v, list) else v)
                    for k, v in c['fixtures'].items()}
    est = {row['label']: row['row'] for row in T['fix_rows']}
    inp['est_override'] = {est[match(k, list(est), 'FIXTURE ESTIMATE row')]: float(v) for k, v in c['qty_overrides'].items()}
    inp['sleeves'] = {}
    items = c['sleeves'].items() if isinstance(c['sleeves'], dict) else [(s['size'], s) for s in c['sleeves']]
    for size, s in items:
        s = s if isinstance(s, dict) else {'qty': s}
        w = norm(s.get('wall', 'CMU'))
        kind = 'Tilt-Up' if 'tilt' in w else 'Other' if w in ('custom', 'other') else 'CMU'
        hits = [t for t in T['sleeves'] if t['kind'] == kind and (kind == 'Other' or size_key(t['size']).startswith(size_key(size)))]
        if len(hits) != 1:
            raise ValueError(f'Sleeve {size} / {kind} matched {len(hits)} SLEEVE SCHEDULE rows')
        inp['sleeves'][hits[0]['row']] = inp['sleeves'].get(hits[0]['row'], 0) + float(s['qty'])
    dp = {t['label']: t['row'] for t in T['demo_pipe']}
    inp['demo_pipe'] = {dp[match(k, list(dp), 'Demo pipe row')]: float(sum(v) if isinstance(v, list) else v)
                        for k, v in c['demo_pipe'].items()}
    df = {t['label']: t['row'] for t in T['demo_fix']}
    inp['demo_fix'] = {}
    for k, v in c['demo_fixtures'].items():
        v = v if isinstance(v, dict) else {'qty': v}
        inp['demo_fix'][df[match(k, list(df), 'Demo fixture row')]] = (float(v['qty']), str(v.get('cap', 'N')).upper())
    inp['phase_overrides'] = c['phase_overrides']
    inp['extra_hours'] = c['extra_hours']
    return inp


def inputs_from_workbook(bk, T):
    g = lambda sh, ref: bk.val(sh, ref)
    inp = dict(complexity=g('INPUT', 'E10') or 'Normal', wall_type=g('INPUT', 'B18'), slab_on_grade=g('INPUT', 'B19') or 'Y',
               crew_size=bk.num('INPUT', 'E5') or 2, shift_hours=bk.num('INPUT', 'E7') or 8,
               hanger_type=g('PIPE ESTIMATE', 'B3') or '', water_material=g('INPUT', 'E12') or '',
               cmu_drops=bk.num('PIPE TAKEOFF', f"B{T['cmu']['row']}"), phase_overrides={}, extra_hours=[])
    inp['pipe'] = {}
    for rows in T['systems'].values():
        for t in rows:
            r = t['row']
            ovr = g('PIPE TAKEOFF', f'F{r}')
            inp['pipe'][r] = (bk.num('PIPE TAKEOFF', f'B{r}'), bk.num('PIPE TAKEOFF', f'C{r}'), bk.num('PIPE TAKEOFF', f'D{r}'),
                              ovr if isinstance(ovr, (int, float)) else None)
    inp['sched'] = {r: sum(bk.num('FIXTURE SCHEDULE', f'{c}{r}') for c in 'BCDEF') for r in T['sched']}
    inp['est_override'] = {}   # literal B cells are already captured as row['fixed']
    inp['sleeves'] = {t['row']: bk.num('SLEEVE SCHEDULE', f"C{t['row']}") for t in T['sleeves']}
    inp['demo_pipe'] = {t['row']: sum(bk.num('DEMO ESTIMATE', f"{c}{t['row']}") for c in 'BCD') for t in T['demo_pipe']}
    inp['demo_fix'] = {t['row']: (bk.num('DEMO ESTIMATE', f"B{t['row']}"), str(g('DEMO ESTIMATE', f"F{t['row']}") or 'N').upper())
                       for t in T['demo_fix']}
    return inp


def estimate(inp, T):
    warnings, comps = [], []   # comps: (phase, hours, description)
    adders = T['complexity']
    cx = 1 + adders.get(inp['complexity'], adders.get('Normal', 0))
    po = {norm(k): phase_key(v) for k, v in (inp.get('phase_overrides') or {}).items()}
    slab = str(inp['slab_on_grade']).upper().startswith('Y')
    mat = norm(inp.get('water_material') or '')

    def pick(opts):
        if not opts:
            return 0.0
        for k, v in opts.items():
            if k and mat and (norm(k) == mat or norm(k).startswith(mat)):
                return v
        return opts[None]

    def fixture_phase(label, comp_label):
        n = norm(label)
        for k, v in po.items():
            if n.startswith(k):
                return v
        cl = norm(comp_label)
        if cl.endswith('- rough-in'):
            return 'RI'
        if cl.endswith('- final set'):
            return 'FIN'
        for prefix, p in PHASE_MAP:
            if n.startswith(prefix):
                return ('UG' if slab else 'RI') if p == 'UG*' else p
        return 'FIN'

    # --- pipe (PIPE ESTIMATE) + hanger points ---
    sys_hrs, mats_pipe, hanger_pts = {}, {}, {}
    for key, rows in T['systems'].items():
        tot = 0.0
        for t in rows:
            ug, wall, clg, ovr = inp['pipe'].get(t['row'], (0, 0, 0, None))
            rt = T['pipe_rates'].get(t['row'], {})
            h_ug = ug * pick(rt.get('B')) * cx
            h_ab = wall * pick(rt.get('C')) * cx + clg * pick(rt.get('D')) * cx
            tot += h_ug + h_ab
            if h_ug:
                comps.append(('UG', h_ug, f"{SYSTEM_NAMES.get(key, key)} pipe {t['size']} underground"))
            if h_ab:
                comps.append(('RI', h_ab, f"{SYSTEM_NAMES.get(key, key)} pipe {t['size']} in-wall/ceiling"))
            final = ovr if ovr is not None else ug + wall + clg
            if final or ug or wall or clg:
                mats_pipe.setdefault(key, []).append(dict(size=t['size'], ug_lf=ug, in_wall_lf=wall, ceiling_lf=clg,
                                                          final_lf=final, override=ovr is not None))
            if t['row'] in T['hanger_spacing'] and clg:
                hanger_pts.setdefault(key, {})[t['size']] = ceil(clg / T['hanger_spacing'][t['row']])
            if (ug or wall or clg) and not rt:
                warnings.append(f'{SYSTEM_NAMES.get(key, key)} LF has no labor in this workbook (PIPE ESTIMATE has no '
                                f'section for it; added in v3.1) - hours exclude it; material is still listed.')
        sys_hrs[key] = tot
    # --- hangers (FIXTURE ESTIMATE hanger block) ---
    ht, L = inp['hanger_type'] or '', T['hanger_labels']
    n_pts = sum(sum(v.values()) for v in hanger_pts.values())
    single = n_pts if ht == L['Single Clevis'] else 0
    trap2 = ceil(n_pts / T['trap_div']['Trapeze Assembly (2']) if ht == L['Trapeze Assembly (2'] else 0
    trap3 = ceil(n_pts / T['trap_div']['Trapeze Assembly (3']) if ht == L['Trapeze Assembly (3'] else 0
    points = single + trap2 + trap3
    rod = points * T['rod_per_point'] if ht else 0
    clamps = points * (T['clamps_per_point'][0] if ht == L['Single Clevis'] else T['clamps_per_point'][1]) if ht else 0
    H = T['hanger_hrs']
    hanger_hrs = (single * H['Single Clevis'] * cx + trap2 * H['Trapeze Assembly (2'] * cx + trap3 * H['Trapeze Assembly (3'] * cx
                  + rod * H['Threaded Rod'] * cx + clamps * H['Beam Clamp'] * cx)
    if hanger_hrs:
        comps.append((po.get('hangers', 'RI'), hanger_hrs, f'Hangers ({ht})'))
    # --- fixtures & specialty (FIXTURE ESTIMATE rows) ---
    fix_hrs, fix_lines, sched_use = 0.0, [], {}
    for row in T['fix_rows']:
        if row['row'] in inp['est_override']:
            qty = inp['est_override'][row['row']]
        elif row['sched']:
            qty = inp['sched'].get(row['sched'], 0)
        else:
            qty = row['fixed'] or 0
        if not qty:
            continue
        if row['sched'] and row['row'] not in inp['est_override']:
            sched_use.setdefault(row['sched'], []).append(row['label'])
        each = sum(h for _, h in row['comps']) * cx
        fix_hrs += qty * each
        fix_lines.append(dict(item=row['label'], qty=qty, hrs_each=round(each, 3), hrs=round(qty * each, 3)))
        for comp_label, h in row['comps']:
            if h:
                desc = (row['label'].split(' ' + EM + ' ')[0] + ' [' + comp_label.split(EM)[-1].strip() + ']'
                        if len(row['comps']) > 1 else row['label'])
                comps.append((fixture_phase(row['label'], comp_label), qty * h * cx, desc))
    for srow, labels in sched_use.items():
        if len(labels) > 1:
            warnings.append(f'FIXTURE SCHEDULE "{T["sched"][srow]}" feeds {len(labels)} estimate rows ({"; ".join(labels)}) - '
                            f'the sheet counts every unit in each; zero the one that does not apply with qty_overrides.')
    # --- CMU drops, sleeves ---
    cmu_hrs = inp['cmu_drops'] * T['cmu']['hrs'] * cx if inp['wall_type'] == T['cmu']['wall'] else 0.0
    if inp['cmu_drops'] and inp['wall_type'] != T['cmu']['wall']:
        warnings.append(f'{inp["cmu_drops"]:g} CMU drops entered but wall type is "{inp["wall_type"]}" - the sheet only '
                        f'charges CMU drop hours when wall type = "{T["cmu"]["wall"]}".')
    if cmu_hrs:
        comps.append((po.get('cmu', 'RI'), cmu_hrs, f"CMU block wall drops ({inp['cmu_drops']:g})"))
    slv_hrs, mats_slv = 0.0, []
    for t in T['sleeves']:
        q = inp['sleeves'].get(t['row'], 0)
        if q:
            slv_hrs += q * t['install'] * cx + q * t['visits'] * t['per_visit'] * cx
            wall = inp['wall_type'] if t['kind'] == 'CMU' else t['kind']
            mats_slv.append(dict(size=t['size'], wall=wall, qty=q, unit_cost_ref=t['unit_cost']))
    if slv_hrs:
        comps.append((po.get('sleeves', 'RI'), slv_hrs, 'Masonry sleeves (install + site-visit coordination)'))
    # --- demolition ---
    demo_pipe = sum(inp['demo_pipe'].get(t['row'], 0) * t['rate'] * cx for t in T['demo_pipe'])
    sheet_demo_pipe = sum(inp['demo_pipe'].get(t['row'], 0) * t['rate'] * cx * T['demo_sheet_count'].get(t['row'], 0)
                          for t in T['demo_pipe'])
    if abs(sheet_demo_pipe - demo_pipe) > EPS:
        warnings.append(f'Sheet PIPE DEMO TOTAL shows {sheet_demo_pipe:.2f} hrs because its SUM range also picks up the '
                        f'Cast Iron / PVC / Copper subtotal rows (double count); Demo labor here uses each row once = '
                        f'{demo_pipe:.2f} hrs.')
    demo_fix = cap = 0.0
    for t in T['demo_fix']:
        q, flag = inp['demo_fix'].get(t['row'], (0, 'N'))
        demo_fix += q * t['hrs'] * cx
        if flag == 'Y':
            cap += q * t['cap'] * cx
    for h, d in ((demo_pipe, 'Pipe demolition'), (demo_fix, 'Fixture demolition'), (cap, 'Cap/stub at removed fixtures')):
        if h:
            comps.append(('DEMO', h, d))
    if cap and not T['demo_cap_in_hours']:
        warnings.append(f'{cap:g} cap/stub hrs are costed by this v3 sheet (DEMO ESTIMATE H) but left out of its hour '
                        f'total (D68); they are included in Demo labor here.')
    for x in inp.get('extra_hours') or []:
        comps.append((phase_key(x['phase']), float(x['hours']), f"{x['item']} (added)"))
    if mat and 'type l' not in mat and not T['material_aware'] and (sys_hrs.get('cold') or sys_hrs.get('hot')):
        warnings.append(f'Water pipe is "{inp["water_material"]}" but this v3 sheet always uses the Type L copper '
                        f'labor rates for water piping (v3.1 follows the material).')
    # --- roll up: summary mirrors the workbook's SUMMARY sheet; phases are what goes into JobTread ---
    summary = dict(dwv=sys_hrs.get('dwv', 0), cold=sys_hrs.get('cold', 0), hot=sys_hrs.get('hot', 0),
                   recirc=sys_hrs.get('recirc', 0), air=sys_hrs.get('air', 0), cmu=cmu_hrs, fixtures=fix_hrs,
                   hangers=hanger_hrs, sleeves=slv_hrs,
                   demo=sheet_demo_pipe + demo_fix + (cap if T['demo_cap_in_hours'] else 0))
    total = sum(summary.values())
    sheet_days = ceil(total / 8) if T['crew_days_from_total'] else \
        ceil((summary['dwv'] + summary['cold'] + summary['hot'] + summary['air'] + fix_hrs + hanger_hrs + summary['demo']) / 8)
    crew, shift = float(inp['crew_size'] or 2), float(inp['shift_hours'] or 8)
    phases = []
    for p in PHASES:
        mh = sum(h for ph, h, _ in comps if ph == p)
        if mh > EPS or p != 'DEMO':
            phases.append(dict(phase=PHASE_NAMES[p], man_hours_raw=round(mh, 3), labor_qty=ceil(mh - EPS) if mh > EPS else 0,
                               mobilization_qty=ceil(mh / shift - EPS) if mh > EPS else 0,
                               elapsed_days=round(mh / (crew * shift), 2),
                               detail=[dict(item=d, hrs=round(h, 3)) for ph, h, d in comps if ph == p]))
    hangers = dict(type=ht, by_system=hanger_pts, single_clevis=single, trapeze_2=trap2, trapeze_3=trap3,
                   threaded_rod_lf=rod, beam_clamps=clamps, rod_per_point=T['rod_per_point'])
    return dict(inputs={k: inp[k] for k in ('complexity', 'wall_type', 'slab_on_grade', 'crew_size', 'shift_hours',
                                           'hanger_type', 'water_material')},
                complexity_multiplier=cx, phases=phases,
                jobtread_man_hours=round(sum(h for _, h, _ in comps), 4),
                summary_hours={k: round(v, 4) for k, v in summary.items()}, total_man_hours=round(total, 4),
                cap_stub_hours=round(cap, 4), sheet_crew_days=sheet_days, summary_crew_days=ceil(total / 8),
                fixtures=fix_lines, materials=dict(pipe=mats_pipe, hangers=hangers, sleeves=mats_slv,
                                                   cmu_drops=inp['cmu_drops']),
                contingency=T['contingency'], blended_rate=round(T['blended_rate'], 3),
                labor_cost_ref=round((total + cap) * T['blended_rate'], 2), warnings=list(dict.fromkeys(warnings)))


def fmt(x):
    return f'{x:g}' if isinstance(x, (int, float)) else str(x)


def to_md(r):
    out = ['| Phase | Man-Hrs (raw) | Labor qty | Mobilization qty | Elapsed days |', '|---|---|---|---|---|']
    for p in r['phases']:
        out.append(f"| {p['phase']} | {fmt(p['man_hours_raw'])} | {p['labor_qty']} | {p['mobilization_qty']} | {p['elapsed_days']} |")
    out.append(f"| **Total** | {fmt(round(r['jobtread_man_hours'], 3))} | {sum(p['labor_qty'] for p in r['phases'])} | "
               f"{sum(p['mobilization_qty'] for p in r['phases'])} | {round(sum(p['elapsed_days'] for p in r['phases']), 2)} |")
    out += ['', 'Phase detail:']
    for p in r['phases']:
        if p['detail']:
            out.append(f"- {p['phase']}: " + ' · '.join(f"{d['item']} {fmt(d['hrs'])}" for d in p['detail']))
    s, i = r['summary_hours'], r['inputs']
    out += ['', f"Estimator SUMMARY hours — DWV {fmt(s['dwv'])} · Cold {fmt(s['cold'])} · Hot {fmt(s['hot'])} · Recirc {fmt(s['recirc'])} · Air {fmt(s['air'])} · "
            f"CMU drops {fmt(s['cmu'])} · Fixtures {fmt(s['fixtures'])} · Hangers {fmt(s['hangers'])} · Sleeves {fmt(s['sleeves'])} · "
            f"Demo {fmt(s['demo'])} = {fmt(r['total_man_hours'])} man-hrs",
            f"Complexity {i['complexity']} ×{fmt(r['complexity_multiplier'])} · wall {i['wall_type']} · slab on grade {i['slab_on_grade']} · "
            f"crew {fmt(i['crew_size'])} × {fmt(i['shift_hours'])} hr · sheet crew-days {r['sheet_crew_days']} (SETTINGS B32) / "
            f"{r['summary_crew_days']} (SUMMARY E9) · blended rate ${r['blended_rate']:.2f}/hr → ${r['labor_cost_ref']:,.0f} (reference only)",
            'Buffer % by plan confidence (SETTINGS contingency): ' + ' · '.join(f'{k} {v:.0%}' for k, v in r['contingency'].items())]
    m = r['materials']
    if m['pipe']:
        out += ['', 'Pipe LF (final = override or helper total; UG = underground helper LF):']
        for key, rows in m['pipe'].items():
            out.append(f"- {SYSTEM_NAMES.get(key, key)}: " + ' · '.join(
                f"{x['size']} {fmt(x['final_lf'])} (UG {fmt(x['ug_lf'])}, wall {fmt(x['in_wall_lf'])}, ceiling {fmt(x['ceiling_lf'])}"
                + (', override' if x['override'] else '') + ')' for x in rows))
    h = m['hangers']
    if h['by_system']:
        out.append(f"Hanger points ({h['type']}): " + ' ; '.join(
            f"{SYSTEM_NAMES.get(k, k)} " + ', '.join(f'{sz} {n}' for sz, n in v.items()) for k, v in h['by_system'].items())
            + f" → clevis {h['single_clevis']} · 2-pipe trapeze {h['trapeze_2']} · 3+ trapeze {h['trapeze_3']} · "
            f"threaded rod {fmt(h['threaded_rod_lf'])} LF · beam clamps {fmt(h['beam_clamps'])}")
    if m['sleeves']:
        out.append('Sleeves: ' + ' · '.join(f"{x['size']} ({x['wall']}) × {fmt(x['qty'])}" for x in m['sleeves']))
    if m['cmu_drops']:
        out.append(f"CMU block wall drops: {fmt(m['cmu_drops'])}")
    if r['warnings']:
        out += [''] + [f'⚠ {w}' for w in r['warnings']]
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('config', nargs='?')
    ap.add_argument('--xlsx', default=DEFAULT_XLSX, help='estimator workbook supplying the tables (JSON mode)')
    ap.add_argument('--from-xlsx', help='filled-in estimator: read tables AND inputs from it')
    ap.add_argument('--format', default='md', choices=['md', 'json'])
    a = ap.parse_args()
    if not a.config and not a.from_xlsx:
        ap.error('give a config JSON or --from-xlsx')
    bk = Book(a.from_xlsx or a.xlsx)
    T = load_tables(bk)
    if a.from_xlsx:
        inp = inputs_from_workbook(bk, T)
        if a.config:   # optional extra keys: phase_overrides, extra_hours
            extra = json.load(open(a.config))
            inp['phase_overrides'] = extra.get('phase_overrides', {})
            inp['extra_hours'] = extra.get('extra_hours', [])
    else:
        inp = inputs_from_config(json.load(open(a.config)), T)
    res = estimate(inp, T)
    if a.from_xlsx:
        cached = bk.v['SUMMARY'][f"B{bk.find('SUMMARY', 'TOTAL LABOR HOURS')}"].value
        if isinstance(cached, (int, float)) and abs(cached - res['total_man_hours']) > 0.01:
            res['warnings'].append(f'Workbook SUMMARY shows {cached:g} total hrs but the inputs compute to '
                                   f'{res["total_man_hours"]:g} - recalc/save the workbook in Excel, or its layout changed.')
    print(json.dumps(res, indent=2, ensure_ascii=False) if a.format == 'json' else to_md(res))


if __name__ == '__main__':
    main()
