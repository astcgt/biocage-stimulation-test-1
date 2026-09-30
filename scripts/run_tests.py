"""Test drivers (one job = one independent FEM case on one GPU).

Test 1  static : vertical compression, displacement-controlled Uz of the C3 rigid reference, other 5 DOF free (ball joint).
Test 2  cyclic : ASTM F2077-style sinusoidal axial compression, R = Fmin/Fmax = 0.1 (i.e. R=10 in compression convention),
                 Fmax = level x static failure load; Basquin + Goodman + Miner damage with cycle jumping; slip ratcheting
                 extrapolated from explicit cycles.
Test 3  6-DOF  : 100 N compressive preload (force-controlled), then the tested DOF is displacement/rotation-controlled in
                 increments, all other DOFs force-free.
Endpoints: PLCL damaged-volume fraction >= 15 % (runs continue to 20 % for reporting), interface slip >= 2 mm,
           or (6-DOF) imposed rotation 10 deg / translation 3 mm reached without endpoint.
"""
import os, sys, json, time, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from params import MAT, CONTACT, ENDPOINTS, CYCLIC, SIXDOF
from progress import Progress

RES = 'results'


def load_model(design, dev, log):
    from fem_core import VoxelContactModel
    M = np.load(f'design/model_{design}.npz')
    return VoxelContactModel(M['L'], float(M['h']), (float(M['x0']), float(M['y0']), float(M['z0'])), M['ref'], MAT, CONTACT,
                             dev=dev, log=log)


class Recorder:
    def __init__(self, outdir, m):
        os.makedirs(outdir, exist_ok=True)
        self.dir = outdir; self.rows = []; self.frames = []
        self.idx = m.is_plcl.nonzero().cpu().numpy().astype(np.int16)             # PLCL element (i,j,k) in cage grid
        self.logf = open(f'{outdir}/log.txt', 'a')

    def log(self, *a):
        s = ' '.join(str(x) for x in a); print(s, flush=True); self.logf.write(s + '\n'); self.logf.flush()

    def record(self, m, row, frame=True):
        vm, s1, s3, sig = m.cage_stress()
        P = m.is_plcl
        slip_lo, slip_up, vlo, vup = m.interface_slip()
        R = m.reaction(); q = m.x[-6:].cpu().numpy()
        st = m.status.cpu().numpy(); pl = m.p_plcl.cpu().numpy()
        row.update(dict(Fx=R[0], Fy=R[1], Fz=R[2], Mx=R[3], My=R[4], Mz=R[5],
                        Ux=q[0], Uy=q[1], Uz=q[2], Rx_deg=math.degrees(q[3]), Ry_deg=math.degrees(q[4]), Rz_deg=math.degrees(q[5]),
                        damage=m.damage_fraction(), max_vm=float(vm[P].max()), p99_vm=float(torch_quant(vm[P], 0.99)),
                        max_s1=float(s1[P].max()), min_s3=float(s3[P].min()),
                        slip_C4=slip_lo, slip_C3=slip_up, slip=max(slip_lo, slip_up),
                        contact_closed=float(np.mean(st[pl] > 0)), contact_slipping=float(np.mean(st[pl] == 2)),
                        contact_area_mm2=float((m.parea[m.p_plcl] * (m.status[m.p_plcl] > 0)).sum())))
        self.rows.append(row)
        if frame:
            pr, _ = m.contact_pressure()
            self.frames.append(dict(vm=vm[P].cpu().numpy().astype(np.float16), s1=s1[P].cpu().numpy().astype(np.float16),
                                    dmg=(m.cage.dmg[P] < 0.5).cpu().numpy(), p=pr[pl].astype(np.float16), st=st[pl]))
        self.flush()
        return row

    def flush(self):
        keys = list(self.rows[0].keys())
        with open(f'{self.dir}/steps.csv', 'w') as f:
            f.write(','.join(keys) + '\n')
            for r in self.rows: f.write(','.join(str(r.get(k, '')) for k in keys) + '\n')

    def save_frames(self, m, extra=None):
        pn = m.pn.cpu().numpy(); pl = m.p_plcl.cpu().numpy()
        out = dict(elem_idx=self.idx, cage_k0=m.cage.off[2], pair_node=pn[pl].astype(np.int16), pair_upper=m.p_upper.cpu().numpy()[pl],
                   pair_area=m.parea.cpu().numpy()[pl])
        for k in ('vm', 's1', 'dmg', 'p', 'st'):
            out[k] = np.stack([f[k] for f in self.frames])
        if extra: out.update(extra)
        np.savez_compressed(f'{self.dir}/frames.npz', **out)


def torch_quant(t, q):
    import torch
    k = max(1, int(round(q * t.numel())))
    return torch.kthvalue(t.flatten().float().cpu(), k).values


def damage_passes(m, rec, q_presc, F_ext, max_passes=25):
    """Progressive failure at the current load: delete over-stressed PLCL elements and re-equilibrate."""
    n_tot = 0; prog = getattr(rec, 'prog', None)
    for p in range(max_passes):
        if prog and p: prog.update(phase=f'damage pass {p + 1}', minor=True)
        vm, s1, _, _ = m.cage_stress()
        n = m.apply_failure(vm, s1, max_frac_per_pass=0.02)
        if n == 0: break
        n_tot += n
        m.solve_increment(q_presc, F_ext, max_outer=8)
        if m.damage_fraction() >= ENDPOINTS['damage_report'][-1]: break
    return n_tot


def crossings(rows, key, levels, xkey):
    out = {}
    for L in levels:
        hit = next((r for r in rows if r[key] >= L), None)
        out[str(L)] = None if hit is None else {xkey: hit[xkey], 'Fz': hit.get('Fz'), 'step': hit['step']}
    return out


# ------------------------------------------------------------------------------------------------ Test 1
def static_job(job, dev):
    design = job[1]
    out = f'{RES}/test1_static/{design}'
    prog = Progress(f'static/{design}', total_steps=int(3.0 / 0.005)); prog.update(phase='build model')
    m = load_model(design, dev, log=lambda *a: None)
    rec = Recorder(out, m); m.log = rec.log; rec.prog = prog
    rec.log(f'=== Test 1 static compression, design {design}, device {dev}')
    uz, du, step, t0 = 0.0, 0.01, 0, time.time()
    rec.record(m, dict(step=0, uz_imposed=0.0, new_failed=0, outer=0, pcg=0, wall=0.0))
    peakF = 0.0; reason = 'max displacement'
    while uz < 3.0:
        uz += du; step += 1
        info = m.solve_increment({2: -uz}, np.zeros(6))
        nf = damage_passes(m, rec, {2: -uz}, np.zeros(6))
        m.commit_slip(m.x)
        r = rec.record(m, dict(step=step, uz_imposed=uz, new_failed=nf, outer=info['outer'], pcg=info['pcg_it'], wall=time.time() - t0))
        peakF = max(peakF, -r['Fz'])
        rec.log(f"step {step:3d} uz {uz:.4f} Fz {r['Fz']:9.1f} N  dmg {100 * r['damage']:6.2f}%  maxVM {r['max_vm']:6.2f}  "
                f"slip C4/C3 {r['slip_C4']:.4f}/{r['slip_C3']:.4f}  tilt {r['Rx_deg']:+.3f}/{r['Ry_deg']:+.3f}  contact {r['contact_closed']:.2f}  "
                f"({info['outer']} outer, {info['pcg_it']} pcg, {time.time() - t0:.0f}s)")
        prog.update(step, frac=max(uz / 3.0, r['damage'] / ENDPOINTS['damage_report'][-1], r['slip'] / ENDPOINTS['slip_mm']),
                    phase='axial compression', extra=f"Uz {uz:.3f} mm, Fz {-r['Fz']:.0f} N, dmg {100 * r['damage']:.1f}%")
        if r['max_vm'] > 0.6 * MAT['PLCL']['sigma_vm_fail'] or r['damage'] > 0: du = 0.005
        if r['damage'] >= ENDPOINTS['damage_report'][-1]: reason = 'damage >= 20 %'; break
        if r['slip'] >= ENDPOINTS['slip_mm']: reason = 'slip >= 2 mm'; break
        if -r['Fz'] < 0.5 * peakF and r['damage'] > ENDPOINTS['damage_frac']: reason = 'load drop > 50 %'; break
    rows = rec.rows
    ep = next((r for r in rows if r['damage'] >= ENDPOINTS['damage_frac'] or r['slip'] >= ENDPOINTS['slip_mm']), None)
    first = next((r for r in rows if r['damage'] > 0), None)
    lin = [r for r in rows[1:6]]
    summ = dict(design=design, stop_reason=reason, peak_Fz_N=peakF,
                stiffness_N_per_mm=float(np.polyfit([r['uz_imposed'] for r in lin], [-r['Fz'] for r in lin], 1)[0]),
                first_damage=None if first is None else dict(uz=first['uz_imposed'], Fz=-first['Fz']),
                endpoint=None if ep is None else dict(uz=ep['uz_imposed'], Fz=-ep['Fz'], damage=ep['damage'], slip=ep['slip'],
                                                      type='damage 15 %' if ep['damage'] >= ENDPOINTS['damage_frac'] else 'slip 2 mm'),
                damage_crossings=crossings(rows, 'damage', ENDPOINTS['damage_report'], 'uz_imposed'),
                max_slip_mm=max(r['slip'] for r in rows), steps=len(rows) - 1, wall_s=time.time() - t0)
    summ['F_fail_N'] = peakF   # static ultimate (peak) load = reference for ASTM F2077 fatigue levels
    summ['F_fail_definition'] = 'peak axial force in displacement-controlled compression (structural failure)'
    json.dump(summ, open(f'{out}/summary.json', 'w'), indent=1, default=float)
    prog.update(phase='saving results')
    rec.save_frames(m, dict(uz=np.array([r['uz_imposed'] for r in rows])))
    rec.log(json.dumps(summ, default=float))
    prog.done(reason)
    return summ


# ------------------------------------------------------------------------------------------------ Test 2
def cyclic_job(job, dev):
    import torch
    _, design, level, F_ult = job
    out = f'{RES}/test2_cyclic/{design}_L{int(round(level * 1000)):04d}'
    prog = Progress(f'cyclic/{design}_L{int(round(level * 1000)):04d}', total_steps=60); prog.update(phase='build model')
    m = load_model(design, dev, log=lambda *a: None)
    rec = Recorder(out, m); m.log = rec.log; rec.prog = prog
    Fmax = level * F_ult; Fmin = Fmax / CYCLIC['R']
    sig_u = MAT['PLCL']['sigma_vm_fail']; b = MAT['PLCL']['basquin_b']; sf = MAT['PLCL']['basquin_sf']
    rec.log(f'=== Test 2 cyclic {design}: level {level:.3f} x F_fail {F_ult:.0f} N -> Fmax {Fmax:.0f} N, Fmin {Fmin:.0f} N, device {dev}')
    t0 = time.time()
    # ramp (force control on Fz, all other DOF free)
    preload(m, rec, Fmin)
    P = m.is_plcl
    D = torch.zeros_like(m.cage.dmg)
    N = 0.0; block = 0; slip_acc = np.zeros(2); reason = 'runout'
    kst = [12000.0]          # secant axial stiffness estimate (N/mm), updated every solve
    def at(F):
        """Reach axial force F by secant iteration on imposed Uz (other 5 DOF free) = load control at convergence."""
        t = time.time(); n = 0
        prog.update(phase=f'load to {F:.0f} N', minor=True)
        uz = -float(m.x[-4]); Fc = -m.reaction()[2]
        for n in range(1, 6):
            uz_new = uz + (F - Fc) / kst[0]
            m.solve_increment({2: -uz_new}, np.zeros(6), max_outer=15, tol=1e-6, dx_tol=1e-3, chg_frac=1 / 200)
            F_new = -m.reaction()[2]
            if abs(uz_new - uz) > 1e-9 and (F_new - Fc) / (uz_new - uz) > 500: kst[0] = (F_new - Fc) / (uz_new - uz)
            uz, Fc = uz_new, F_new
            if abs(Fc - F) < 0.01 * Fmax: break
        rec.log(f'      reach F={F:.0f} N -> {Fc:.1f} N, Uz {uz:.4f} mm, {n} solves, k {kst[0]:.0f} N/mm, {time.time() - t:.0f}s')
        return m
    def signed_eq():
        vm, s1, s3, sig = m.cage_stress()
        return vm * torch.sign(sig[..., :3].sum(-1)), vm, s1
    prog.update(phase=f'ramp to Fmax {Fmax:.0f} N')
    for F in np.linspace(Fmin, Fmax, max(2, int(math.ceil((Fmax - Fmin) / 300))) + 1)[1:]:
        at(F)
    damage_passes(m, rec, {2: float(m.x[-4])}, np.zeros(6)); m.commit_slip(m.x)
    rec.record(m, dict(step=0, block=0, N=0.0, dN=0.0, Fmax=Fmax, Fmin=Fmin, maxD=0.0, slip_extrap=0.0, stiffness=0.0, wall=0.0))
    while N < CYCLIC['runout'] and block < 60:
        block += 1
        # 3 explicit cycles (Fmax -> Fmin); ratcheting = slip change per cycle at Fmin, accepted only if it exceeds 3x the
        # numerical noise (re-solve at the same load) and is not decaying (shakedown -> 0)
        sl = []
        prog.update(block - 1, phase=f'cycle block {block}: explicit cycles + damage/ratchet update', extra=f'N {N:.3g}')
        for c in range(3):
            at(Fmax); nf = damage_passes(m, rec, {2: float(m.x[-4])}, np.zeros(6)); m.commit_slip(m.x)
            eq_max, vm_max, s1_max = signed_eq(); uz_max = float(m.x[-4])
            at(Fmin); m.commit_slip(m.x)
            eq_min, _, _ = signed_eq(); uz_min = float(m.x[-4])
            _, _, vlo, vup = m.interface_slip(); sl.append(np.r_[vlo[:2], vup[:2]])
        at(Fmin); _, _, vlo, vup = m.interface_slip(); rep = np.r_[vlo[:2], vup[:2]]
        nrm = lambda v: np.array([np.linalg.norm(v[:2]), np.linalg.norm(v[2:])])
        noise = nrm(rep - sl[2]); r1 = nrm(sl[1] - sl[0]); r2 = nrm(sl[2] - sl[1])
        ratchet = np.where((r2 > 3 * noise) & (r2 >= 0.8 * r1), r2, 0.0)
        sa = (eq_max - eq_min).abs() / 2; sm = (eq_max + eq_min) / 2
        sar = sa / torch.clamp(1 - torch.clamp(sm, min=0) / sig_u, min=1e-3)
        Nf = 0.5 * (torch.clamp(sar, min=1e-9) / sf) ** (1 / b)
        rate = torch.where(P & (m.cage.dmg > 0.5), 1 / Nf, torch.zeros_like(Nf))
        rmax = float(rate.max())
        dN = CYCLIC['runout'] - N if rmax <= 0 else min(CYCLIC['max_dD_per_jump'] / rmax, CYCLIC['runout'] - N)
        if ratchet.max() > 0: dN = min(dN, 0.2 / ratchet.max())
        dN = max(dN, 1.0)
        D += rate * dN; N += dN + 3
        slip_acc += ratchet * dN
        newly = P & (m.cage.dmg > 0.5) & (D >= 1)
        m.cage.dmg[newly] = 1e-3
        stiff = (Fmax - Fmin) / max(abs(uz_max - uz_min), 1e-12)
        r = rec.record(m, dict(step=block, block=block, N=N, dN=dN, Fmax=Fmax, Fmin=Fmin, maxD=float(D[P].max()),
                               slip_extrap=float(slip_acc.max()), stiffness=stiff, wall=time.time() - t0))
        r['damage'] = m.damage_fraction(); rec.rows[-1]['damage'] = r['damage']
        rec.log(f"block {block:3d} N {N:12.0f} (+{dN:10.0f}) maxD {float(D[P].max()):.3f} dmg {100 * r['damage']:6.2f}%  "
                f"maxVM@Fmax {float(vm_max[P].max()):6.2f}  ratchet {ratchet.max():.2e} (raw {r2.max():.1e}, noise {noise.max():.1e}) mm/cyc slip {slip_acc.max():.4f} mm  "
                f"k {stiff:8.0f} N/mm ({time.time() - t0:.0f}s)")
        prog.update(block, frac=max(math.log10(N + 1) / math.log10(CYCLIC['runout']), r['damage'] / ENDPOINTS['damage_report'][-1],
                                    (slip_acc.max() + r['slip']) / ENDPOINTS['slip_mm'], block / 60),
                    phase=f'cycle block {block} done', extra=f"N {N:.3g}/{CYCLIC['runout']:.0e}, dmg {100 * r['damage']:.1f}%, slip {slip_acc.max() + r['slip']:.3f} mm")
        if r['damage'] >= ENDPOINTS['damage_report'][-1]: reason = 'damage >= 20 %'; break
        if slip_acc.max() + r['slip'] >= ENDPOINTS['slip_mm']: reason = 'slip >= 2 mm'; break
    rows = rec.rows
    ep = next((r for r in rows if r['damage'] >= ENDPOINTS['damage_frac'] or r['slip_extrap'] + r['slip'] >= ENDPOINTS['slip_mm']), None)
    summ = dict(design=design, level=level, F_fail_static=F_ult, Fmax=Fmax, Fmin=Fmin, stop_reason=reason,
                cycles_run=N, runout=N >= CYCLIC['runout'] and ep is None,
                cycles_to_endpoint=None if ep is None else ep['N'],
                endpoint_type=None if ep is None else ('damage 15 %' if ep['damage'] >= ENDPOINTS['damage_frac'] else 'slip 2 mm'),
                damage_crossings=crossings(rows, 'damage', ENDPOINTS['damage_report'], 'N'),
                final_damage=rows[-1]['damage'], final_slip_mm=rows[-1]['slip_extrap'] + rows[-1]['slip'],
                initial_stiffness=rows[1]['stiffness'] if len(rows) > 1 else None, final_stiffness=rows[-1]['stiffness'],
                blocks=len(rows) - 1, wall_s=time.time() - t0, test_duration_days_at_5Hz=N / CYCLIC['freq_hz'] / 86400)
    json.dump(summ, open(f'{out}/summary.json', 'w'), indent=1, default=float)
    prog.update(phase='saving results')
    rec.save_frames(m, dict(N=np.array([r['N'] for r in rows]), D=D[P].cpu().numpy().astype(np.float16)))
    rec.log(json.dumps(summ, default=float))
    prog.done(reason)
    return summ


# ------------------------------------------------------------------------------------------------ Test 3
MODES = {  # name: (dof index, sign, step, max)   dof: 0 Ux 1 Uy 2 Uz 3 Rx 4 Ry 5 Rz ; x lateral(+left/right), y anterior, z cranial
    'flexion': (3, -1, math.radians(0.25), math.radians(10)), 'extension': (3, +1, math.radians(0.25), math.radians(10)),
    'lat_bend_pos': (4, +1, math.radians(0.25), math.radians(10)), 'lat_bend_neg': (4, -1, math.radians(0.25), math.radians(10)),
    'axial_rot_pos': (5, +1, math.radians(0.25), math.radians(10)), 'axial_rot_neg': (5, -1, math.radians(0.25), math.radians(10)),
    'shear_ant': (1, +1, 0.05, 5.0), 'shear_post': (1, -1, 0.05, 5.0),
    'shear_lat_pos': (0, +1, 0.05, 5.0), 'shear_lat_neg': (0, -1, 0.05, 5.0),
}


def preload(m, rec, Fp, k_guess=12000.0):
    """Reach Fz = -Fp by secant iteration on imposed Uz (other DOFs free), then hold Fz by force control."""
    uz, F = 0.0, 0.0; prog = getattr(rec, 'prog', None)
    if prog: prog.update(phase=f'preload to {Fp:.0f} N')
    for it in range(12):
        uz_new = uz + (Fp - F) / k_guess
        m.solve_increment({2: -uz_new}, np.zeros(6))
        F_new = -m.reaction()[2]
        if it > 0 and abs(F_new - F) > 1e-6: k_guess = max(1000.0, (F_new - F) / (uz_new - uz))
        uz, F = uz_new, F_new
        rec.log(f'   preload secant {it}: Uz {uz:.5f} mm -> Fz {-F:.2f} N')
        if abs(F - Fp) < 0.02 * Fp: break
    m.solve_increment({}, np.array([0, 0, -Fp, 0, 0, 0.]))
    m.commit_slip(m.x)
    rec.log(f'   preload done: Fz {m.reaction()[2]:.2f} N, Uz {float(m.x[-4]):.5f} mm')


def sixdof_job(job, dev):
    _, design, mode = job
    dof, sgn, dstep, dmax = MODES[mode]
    out = f'{RES}/test3_6dof/{design}_{mode}'
    n_tot = int(round(dmax / dstep))
    prog = Progress(f'6dof/{design}_{mode}', total_steps=n_tot); prog.update(phase='build model')
    m = load_model(design, dev, log=lambda *a: None)
    rec = Recorder(out, m); m.log = rec.log; rec.prog = prog
    Fp = SIXDOF['preload_N']
    rec.log(f'=== Test 3 6-DOF {design} {mode}: preload {Fp} N (force), dof {dof} displacement-controlled, device {dev}')
    t0 = time.time()
    preload(m, rec, Fp)
    base = float(m.x[-6 + dof])
    rec.record(m, dict(step=0, imposed=0.0, new_failed=0, wall=0.0))
    val, step, reason = 0.0, 0, 'imposed limit reached'
    Fe = np.array([0, 0, -Fp, 0, 0, 0.])
    while abs(val) < dmax - 1e-12:
        val += sgn * dstep; step += 1
        pres = {dof: base + val}
        info = m.solve_increment(pres, Fe)
        nf = damage_passes(m, rec, pres, Fe)
        m.commit_slip(m.x)
        r = rec.record(m, dict(step=step, imposed=val if dof > 2 else val, imposed_deg=math.degrees(val) if dof > 2 else None,
                               new_failed=nf, wall=time.time() - t0))
        load = r[['Fx', 'Fy', 'Fz', 'Mx', 'My', 'Mz'][dof]]
        rec.log(f"step {step:3d} {mode} {'%.2f deg' % math.degrees(val) if dof > 2 else '%.3f mm' % val}  load {load:9.2f} {'Nmm' if dof > 2 else 'N'}  "
                f"Fz {r['Fz']:7.1f}  dmg {100 * r['damage']:5.2f}%  maxVM {r['max_vm']:6.2f}  slip C4/C3 {r['slip_C4']:.4f}/{r['slip_C3']:.4f}  "
                f"contact {r['contact_closed']:.2f} ({info['outer']} outer, {time.time() - t0:.0f}s)")
        prog.update(step, frac=max(step / n_tot, r['damage'] / ENDPOINTS['damage_frac'], r['slip'] / ENDPOINTS['slip_mm']),
                    phase=f'imposing {mode}', extra=f"{'%.2f deg' % math.degrees(val) if dof > 2 else '%.2f mm' % val}, load {load:.1f}, dmg {100 * r['damage']:.1f}%")
        if r['damage'] >= ENDPOINTS['damage_frac']: reason = 'damage >= 15 %'; break
        if r['slip'] >= ENDPOINTS['slip_mm']: reason = 'slip >= 2 mm'; break
    rows = rec.rows; key = ['Fx', 'Fy', 'Fz', 'Mx', 'My', 'Mz'][dof]
    loads = [abs(r[key]) for r in rows]
    summ = dict(design=design, mode=mode, dof=dof, stop_reason=reason, preload_N=Fp,
                max_imposed=rows[-1]['imposed'], max_imposed_unit='rad' if dof > 2 else 'mm',
                max_load=max(loads), load_unit='Nmm' if dof > 2 else 'N',
                load_at_endpoint=loads[-1], final_damage=rows[-1]['damage'], final_slip=rows[-1]['slip'],
                max_vm=max(r['max_vm'] for r in rows), steps=len(rows) - 1, wall_s=time.time() - t0)
    json.dump(summ, open(f'{out}/summary.json', 'w'), indent=1, default=float)
    prog.update(phase='saving results')
    rec.save_frames(m, dict(imposed=np.array([r['imposed'] for r in rows])))
    rec.log(json.dumps(summ, default=float))
    prog.done(reason)
    return summ


def dispatch(job, dev):
    return {'static': static_job, 'cyclic': cyclic_job, 'sixdof': sixdof_job}[job[0]](job, dev)
