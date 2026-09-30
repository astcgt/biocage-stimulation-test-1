"""Visualise simulation method, stress evolution, damage, contact and load curves for every finished case."""
import os, sys, json, glob, math
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import animation, colors
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from params import MAT, ENDPOINTS, CYCLIC, SIXDOF

H = 0.2
VM_MAX = MAT['PLCL']['sigma_vm_fail']
CMAP = 'turbo'


def load_design(design):
    M = np.load(f'design/model_{design}.npz')
    return M


def read_csv(fn):
    lines = open(fn).read().strip().split('\n'); keys = lines[0].split(',')
    rows = []
    for l in lines[1:]:
        vals = l.split(','); r = {}
        for k, v in zip(keys, vals):
            try: r[k] = float(v)
            except ValueError: r[k] = v
        rows.append(r)
    return rows


def topview(F, idx, vals, shape, reduce='max'):
    """Project element values onto the XY plane (max over height)."""
    img = np.full(shape[:2], np.nan)
    flat = idx[:, 0] * shape[1] + idx[:, 1]
    out = np.full(shape[0] * shape[1], -np.inf)
    np.maximum.at(out, flat, vals.astype(float))
    out[np.isinf(out)] = np.nan
    return out.reshape(shape[:2])


def pair_map(F, sel, vals, shape):
    img = np.full((shape[0] + 1, shape[1] + 1), np.nan)
    pn = F['pair_node'][sel]
    v = vals[sel].astype(float)
    flat = pn[:, 0] * (shape[1] + 1) + pn[:, 1]
    out = np.full(img.size, -np.inf); np.maximum.at(out, flat, v); out[np.isinf(out)] = np.nan
    return out.reshape(img.shape)


# ------------------------------------------------------------------------------------------ method schematic
def method_figure():
    os.makedirs('figures', exist_ok=True)
    M = load_design('B_tread'); L = M['L']; ref = M['ref']
    x0, y0, z0 = float(M['x0']), float(M['y0']), float(M['z0'])
    nx, ny, nz = L.shape
    cmap = np.array([[1, 1, 1], [.93, .85, .7], [.72, .56, .36], [.93, .85, .7], [.72, .56, .36], [.2, .45, .8], [.95, .6, .6]])
    j = int((ref[1] - y0) / H); i = int((ref[0] - x0) / H)
    fig, axs = plt.subplots(1, 2, figsize=(17, 7.5))
    for a, sec, ext, xl in [(axs[0], L[:, j, :], [x0, x0 + nx * H, z0, z0 + nz * H], 'x (mm, lateral)'),
                            (axs[1], L[i, :, :], [y0, y0 + ny * H, z0, z0 + nz * H], 'y (mm, anterior +)')]:
        a.imshow(cmap[sec].transpose(1, 0, 2), origin='lower', extent=ext)
        a.set_xlabel(xl); a.set_ylabel('z (mm, cranial +)')
        a.axhline(z0 + 0.02, color='k', lw=5); a.text(ext[0] + 0.5, z0 + 0.4, 'C4 base: fixed (u = 0)', fontsize=10, weight='bold')
        a.axhline(ext[3] - 0.02, color='crimson', lw=5)
        a.text(ext[0] + 0.5, ext[3] - 1.2, 'C3 top: tied to rigid reference point (6 DOF)', color='crimson', fontsize=10, weight='bold')
        c = ref[0] if a is axs[0] else ref[1]
        a.plot(c, ref[2], 'r*', ms=16)
        a.annotate('', xy=(c, ref[2] + 2.5), xytext=(c, ref[2] + 7), arrowprops=dict(arrowstyle='->', color='crimson', lw=3))
        a.text(c + 0.4, ref[2] + 5, 'Fz / Uz (Test 1, 2)\n+ 6-DOF (Test 3)', color='crimson', fontsize=9)
    axs[0].set_title('Coronal section through reference point (design B)')
    axs[1].set_title('Sagittal section through reference point (design B)')
    from matplotlib.patches import Patch
    axs[1].legend(handles=[Patch(color=cmap[1], label=f"cancellous bone E={MAT['cancellous']['E']:.0f} MPa"),
                           Patch(color=cmap[2], label=f"cortical / bony endplate E={MAT['cortical']['E']:.0f} MPa"),
                           Patch(color=cmap[5], label=f"PLCL cage E={MAT['PLCL']['E']:.0f} MPa (PLC 8516)"),
                           Patch(color=cmap[6], label=f"biodisc E={MAT['biodisc']['E'] * 1000:.0f} kPa"),
                           Patch(color='w', label='cage-bone: contact only (pressure + friction mu=0.3)')],
                  loc='lower right', fontsize=9)
    plt.tight_layout(); plt.savefig('figures/method_model_setup.png', dpi=110); plt.close()

    # flow chart of the solution procedure
    fig, a = plt.subplots(figsize=(15, 6)); a.axis('off')
    boxes = [('STL (pig C3-C4)\nGPU ray casting ->\nendplate height maps', 0.02),
             ('Cage design\ncontour-matched,\n1 mm inset, 60 % window,\nA smooth / B chevron lugs', 0.19),
             ('Voxel hex mesh h=0.2 mm\n~2.4 M DOF, 2 bodies\n(bone | cage+biodisc)\nduplicated interface nodes', 0.36),
             ('Load increment\n(Uz, Fz or 6-DOF)\nmatrix-free Jacobi PCG\n(fp64, A100)', 0.53),
             ('Contact active set\nnormal penalty + Coulomb\nreturn mapping (stick/slip)\nuntil converged', 0.70),
             ('Progressive damage\nsigma_vm>=35 or sigma_1>=30 MPa\n-> element stiffness x1e-3\nre-equilibrate; fatigue:\nBasquin+Goodman+Miner\ncycle jumping', 0.87)]
    for t, x in boxes:
        a.text(x, 0.55, t, ha='left', va='center', fontsize=10, bbox=dict(boxstyle='round,pad=0.6', fc='#e8f0fb', ec='#2a5ea8'))
    for x in (0.165, 0.335, 0.505, 0.675, 0.845):
        a.annotate('', xy=(x + 0.02, 0.55), xytext=(x - 0.005, 0.55), arrowprops=dict(arrowstyle='->', lw=2))
    a.text(0.5, 0.12, f"Endpoints: PLCL damaged volume >= {int(ENDPOINTS['damage_frac'] * 100)} % (10/15/20 % reported) or cage-bone slip >= {ENDPOINTS['slip_mm']} mm",
           ha='center', fontsize=12, weight='bold')
    a.text(0.5, 0.95, 'FE simulation procedure', ha='center', fontsize=15, weight='bold')
    plt.savefig('figures/method_flowchart.png', dpi=110, bbox_inches='tight'); plt.close()


# ------------------------------------------------------------------------------------------ per-case figures
def case_figures(case_dir, kind):
    F = np.load(f'{case_dir}/frames.npz'); rows = read_csv(f'{case_dir}/steps.csv')
    S = json.load(open(f'{case_dir}/summary.json'))
    design = 'A_smooth' if 'A_smooth' in case_dir else 'B_tread'
    M = load_design(design); nx, ny = M['L'].shape[:2]
    shape = (nx, ny)
    idx = F['elem_idx'].astype(int); up = F['pair_upper']
    ext = [float(M['x0']), float(M['x0']) + nx * H, float(M['y0']), float(M['y0']) + ny * H]
    nfr = len(F['vm'])
    if kind == 'static':
        xv, xl = np.array([r['uz_imposed'] for r in rows]), 'imposed axial displacement Uz (mm)'
        yv, yl = np.array([-r['Fz'] for r in rows]), 'axial force (N)'
    elif kind == 'cyclic':
        xv, xl = np.array([max(r['N'], 1) for r in rows]), 'cycles N'
        yv, yl = np.array([r['damage'] * 100 for r in rows]), 'damaged PLCL volume (%)'
    else:
        dof = int(S['dof']); key = ['Fx', 'Fy', 'Fz', 'Mx', 'My', 'Mz'][dof]
        xv = np.array([r['imposed'] for r in rows]); xv = np.degrees(np.abs(xv)) if dof > 2 else np.abs(xv)
        xl = 'imposed rotation (deg)' if dof > 2 else 'imposed translation (mm)'
        yv = np.abs(np.array([r[key] for r in rows])) / (1000 if dof > 2 else 1); yl = f"|{key}| ({'Nm' if dof > 2 else 'N'})"
    dmg_pct = np.array([r['damage'] * 100 for r in rows]); slip = np.array([r['slip'] for r in rows])
    title = os.path.basename(case_dir)

    # ---- curves
    fig, axs = plt.subplots(1, 4, figsize=(22, 4.8))
    axs[0].plot(xv, yv, 'o-', ms=3); axs[0].set_xlabel(xl); axs[0].set_ylabel(yl)
    if kind == 'cyclic': axs[0].set_xscale('log')
    axs[1].plot(xv, dmg_pct, 'o-', ms=3, color='crimson'); axs[1].set_ylabel('damaged PLCL volume (%)'); axs[1].set_xlabel(xl)
    for lv in ENDPOINTS['damage_report']: axs[1].axhline(lv * 100, ls='--', color='grey', lw=.8)
    axs[2].plot(xv, [r['slip_C4'] for r in rows], label='cage vs C4'); axs[2].plot(xv, [r['slip_C3'] for r in rows], label='cage vs C3')
    if kind == 'cyclic': axs[2].plot(xv, [r['slip_extrap'] for r in rows], label='ratchet (extrapolated)')
    axs[2].axhline(ENDPOINTS['slip_mm'], ls='--', color='grey'); axs[2].set_ylabel('interface slip (mm)'); axs[2].set_xlabel(xl); axs[2].legend()
    axs[2].set_yscale('symlog', linthresh=1e-3)
    axs[3].plot(xv, [r['max_vm'] for r in rows], label='max von Mises'); axs[3].plot(xv, [r['p99_vm'] for r in rows], label='99th pct von Mises')
    axs[3].plot(xv, [r['max_s1'] for r in rows], label='max principal')
    axs[3].axhline(MAT['PLCL']['sigma_vm_fail'], ls='--', color='crimson', lw=.8, label='breakage limits')
    axs[3].axhline(MAT['PLCL']['sigma_1_fail'], ls=':', color='crimson', lw=.8)
    axs[3].set_ylabel('cage stress (MPa)'); axs[3].set_xlabel(xl); axs[3].legend(fontsize=8)
    for a in axs:
        if kind == 'cyclic': a.set_xscale('log')
        a.grid(alpha=.3)
    fig.suptitle(f'{title}: {S.get("stop_reason", "")}'); plt.tight_layout(); plt.savefig(f'{case_dir}/curves.png', dpi=90); plt.close()

    # ---- stress evolution animation (top-view max von Mises, damage, contact pressure C3/C4, curve marker)
    sel_fr = np.unique(np.linspace(0, nfr - 1, min(nfr, 40)).astype(int))
    pmax = np.nanpercentile(np.concatenate([F['p'][k].astype(float) for k in sel_fr]), 99) or 1
    fig, axs = plt.subplots(1, 5, figsize=(26, 5.2))
    ims = []
    def draw(k):
        for a in axs: a.clear()
        vmimg = topview(F, idx, F['vm'][k], shape)
        dimg = topview(F, idx, F['dmg'][k].astype(float), shape)
        axs[0].imshow(vmimg.T, origin='lower', extent=ext, cmap=CMAP, vmin=0, vmax=VM_MAX); axs[0].set_title('max von Mises through height (MPa)')
        axs[1].imshow(np.where(np.isnan(vmimg), np.nan, dimg).T, origin='lower', extent=ext, cmap=colors.ListedColormap(['#cfe3f7', '#d62728']), vmin=0, vmax=1)
        axs[1].set_title(f'damaged columns (red)  total {dmg_pct[k]:.2f}% vol')
        for a, s, t in [(axs[2], up, 'C3 interface contact pressure (MPa)'), (axs[3], ~up, 'C4 interface contact pressure (MPa)')]:
            im = pair_map(F, s, F['p'][k], shape)
            a.imshow(im.T, origin='lower', extent=[ext[0], ext[1] + H, ext[2], ext[3] + H], cmap='magma', vmin=0, vmax=pmax); a.set_title(t)
        axs[4].plot(xv, yv, '-', color='grey'); axs[4].plot(xv[k], yv[k], 'ro', ms=9); axs[4].set_xlabel(xl); axs[4].set_ylabel(yl)
        if kind == 'cyclic': axs[4].set_xscale('log')
        axs[4].grid(alpha=.3); axs[4].set_title(f'step {k}')
        for a in axs[:4]: a.set_xlabel('x (mm)'); a.set_ylabel('y (mm, ant +)')
        fig.suptitle(f'{title}   frame {k}/{nfr - 1}', fontsize=13)
    sm = plt.cm.ScalarMappable(cmap=CMAP, norm=colors.Normalize(0, VM_MAX)); fig.colorbar(sm, ax=axs[0], fraction=.046)
    sm2 = plt.cm.ScalarMappable(cmap='magma', norm=colors.Normalize(0, pmax)); fig.colorbar(sm2, ax=axs[3], fraction=.046)
    anim = animation.FuncAnimation(fig, draw, frames=sel_fr, interval=250)
    anim.save(f'{case_dir}/stress_evolution.gif', writer=animation.PillowWriter(fps=4))
    draw(sel_fr[-1]); plt.savefig(f'{case_dir}/final_state.png', dpi=90)
    # snapshot at endpoint crossing if any
    k15 = next((i for i, r in enumerate(rows) if r['damage'] >= ENDPOINTS['damage_frac']), None)
    if k15 is not None and k15 < nfr:
        draw(k15); plt.savefig(f'{case_dir}/state_at_15pct_damage.png', dpi=90)
    plt.close()

    # ---- stress distribution inside the cage at the final frame: coronal + sagittal image sections
    vm = F['vm'][sel_fr[-1]].astype(float); dm = F['dmg'][sel_fr[-1]]
    k0 = int(F['cage_k0']); nzc = idx[:, 2].max() + 1
    vol = np.full((nx, ny, nzc), np.nan); vol[idx[:, 0], idx[:, 1], idx[:, 2]] = vm
    brk = np.zeros((nx, ny, nzc), bool); brk[idx[:, 0], idx[:, 1], idx[:, 2]] = dm
    zlo = float(M['z0']) + k0 * H; zhi = zlo + nzc * H
    ys = np.percentile(idx[:, 1], [15, 38, 62, 85]).astype(int); xm = int(np.median(idx[:, 0]))
    fig, axs = plt.subplots(5, 1, figsize=(14, 17))
    for a, jj in zip(axs[:4], ys):
        a.imshow(vol[:, jj, :].T, origin='lower', extent=[ext[0], ext[1], zlo, zhi], cmap=CMAP, vmin=0, vmax=VM_MAX, aspect='equal')
        a.contour(np.linspace(ext[0], ext[1], nx), np.linspace(zlo, zhi, nzc), brk[:, jj, :].T.astype(float), [0.5], colors='k', linewidths=1)
        a.set_title(f'coronal section y = {float(M["y0"]) + (jj + .5) * H:.1f} mm (black contour = broken)'); a.set_ylabel('z (mm)')
    im = axs[4].imshow(vol[xm, :, :].T, origin='lower', extent=[ext[2], ext[3], zlo, zhi], cmap=CMAP, vmin=0, vmax=VM_MAX, aspect='equal')
    axs[4].contour(np.linspace(ext[2], ext[3], ny), np.linspace(zlo, zhi, nzc), brk[xm, :, :].T.astype(float), [0.5], colors='k', linewidths=1)
    axs[4].set_title(f'sagittal section x = {float(M["x0"]) + (xm + .5) * H:.1f} mm (anterior right)'); axs[4].set_xlabel('y (mm)'); axs[4].set_ylabel('z (mm)')
    fig.colorbar(im, ax=axs, fraction=.02, label='von Mises (MPa)')
    fig.suptitle(f'{title}: internal von Mises stress at final step'); plt.savefig(f'{case_dir}/internal_stress_slices.png', dpi=80); plt.close()


# ------------------------------------------------------------------------------------------ interactive 3D (plotly)
def interactive_3d(case_dir, max_frames=10):
    import plotly.graph_objects as go
    F = np.load(f'{case_dir}/frames.npz'); rows = read_csv(f'{case_dir}/steps.csv')
    design = 'A_smooth' if 'A_smooth' in case_dir else 'B_tread'
    M = load_design(design); k0 = int(F['cage_k0'])
    # coarsen 2x2x2 for a light-weight viewer (0.4 mm blocks, max von Mises, broken if any element broken)
    idx_f = F['elem_idx'].astype(int); cb = idx_f // 2
    idx, inv = np.unique(cb, axis=0, return_inverse=True); inv = inv.ravel()
    def coarse(v, red):
        out = np.full(len(idx), -np.inf if red == 'max' else 0.0); getattr(np, red + 'imum' if red == 'max' else 'add').at(out, inv, v); return out
    VM = np.stack([coarse(F['vm'][k].astype(float), 'max') for k in range(len(F['vm']))])
    DM = np.stack([coarse(F['dmg'][k].astype(float), 'add') > 0 for k in range(len(F['vm']))])
    Hc = 2 * H
    occ = set(map(tuple, idx))
    # exposed faces of PLCL voxels -> quads -> two triangles, coloured by element value
    verts, faces, owner = {}, [], []
    def vid(p):
        if p not in verts: verts[p] = len(verts)
        return verts[p]
    dirs = [((1, 0, 0), [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)]), ((-1, 0, 0), [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)]),
            ((0, 1, 0), [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)]), ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
            ((0, 0, 1), [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]), ((0, 0, -1), [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)])]
    for e, (i, j, k) in enumerate(map(tuple, idx)):
        for d, quad in dirs:
            if (i + d[0], j + d[1], k + d[2]) in occ: continue
            v = [vid((i + a, j + b, k + c)) for a, b, c in quad]
            faces += [(v[0], v[1], v[2]), (v[0], v[2], v[3])]; owner += [e, e]
    P = np.array(list(verts.keys()), float)
    X = float(M['x0']) + P[:, 0] * Hc; Y = float(M['y0']) + P[:, 1] * Hc; Z = float(M['z0']) + k0 * H + P[:, 2] * Hc
    fa = np.array(faces); owner = np.array(owner)
    sel = np.unique(np.linspace(0, len(F['vm']) - 1, min(len(F['vm']), max_frames)).astype(int))
    def mesh(k):
        v = VM[k].astype(np.float32)[owner]
        v = np.where(DM[k][owner], np.nan, v)
        return go.Mesh3d(x=X.astype(np.float32), y=Y.astype(np.float32), z=Z.astype(np.float32), i=fa[:, 0].astype(np.int32), j=fa[:, 1].astype(np.int32), k=fa[:, 2].astype(np.int32), intensity=np.nan_to_num(v, nan=-1).astype(np.float32), intensitymode='cell',
                         colorscale='Turbo', cmin=0, cmax=VM_MAX, colorbar=dict(title='von Mises MPa'), flatshading=True)
    fig = go.Figure(data=[mesh(sel[0])], frames=[go.Frame(data=[mesh(k)], name=str(k)) for k in sel])
    lab = lambda k: f"step {k}: damage {rows[k]['damage'] * 100:.1f}%, Fz {rows[k]['Fz']:.0f} N"
    fig.update_layout(title=f'{os.path.basename(case_dir)} - cage von Mises stress (broken elements removed)',
                      scene=dict(aspectmode='data', xaxis_title='x (mm)', yaxis_title='y (mm, ant)', zaxis_title='z (mm)'),
                      updatemenus=[dict(type='buttons', buttons=[dict(label='Play', method='animate', args=[None, dict(frame=dict(duration=400))])])],
                      sliders=[dict(steps=[dict(method='animate', args=[[str(k)], dict(mode='immediate', frame=dict(duration=0))], label=lab(k)) for k in sel])])
    fig.write_html(f'{case_dir}/interactive_3d.html', include_plotlyjs='cdn')


def summary_figures():
    os.makedirs('figures', exist_ok=True)
    fs = sorted(glob.glob('results/test2_cyclic/*/summary.json'))
    if fs:
        fig, a = plt.subplots(figsize=(9, 6))
        for d, c in (('A_smooth', 'tab:blue'), ('B_tread', 'tab:orange')):
            S = [json.load(open(f)) for f in fs if f'/{d}_' in f]
            for s in S:
                n = s['cycles_to_endpoint'] if s['cycles_to_endpoint'] else s['cycles_run']
                a.scatter(max(n, 1), s['Fmax'], color=c, marker='o' if s['cycles_to_endpoint'] else '>', s=70,
                          label=f"{d} ({'endpoint' if s['cycles_to_endpoint'] else 'runout'})")
        a.axvline(CYCLIC['runout'], ls='--', color='grey'); a.set_xscale('log'); a.set_xlabel('cycles to endpoint (> = runout)'); a.set_ylabel('Fmax (N)')
        h, l = a.get_legend_handles_labels(); u = dict(zip(l, h)); a.legend(u.values(), u.keys()); a.grid(alpha=.3)
        a.set_title('Test 2: ASTM F2077-style axial compression fatigue (R = 10, 5 Hz)')
        plt.tight_layout(); plt.savefig('figures/test2_load_vs_cycles.png', dpi=100); plt.close()
    fs = sorted(glob.glob('results/test3_6dof/*/summary.json'))
    if fs:
        S = [json.load(open(f)) for f in fs]
        modes = sorted({s['mode'] for s in S})
        fig, axs = plt.subplots(1, 3, figsize=(22, 6))
        for k, (key, lab) in enumerate([('max_load', 'max moment (Nm) / shear (N)'), ('final_damage', 'final damaged PLCL volume (%)'), ('final_slip', 'final slip (mm)')]):
            for o, (d, c) in enumerate((('A_smooth', 'tab:blue'), ('B_tread', 'tab:orange'))):
                v = []
                for mo in modes:
                    s = next((x for x in S if x['design'] == d and x['mode'] == mo), None)
                    if s is None: v.append(np.nan); continue
                    val = s[key]
                    if key == 'max_load' and s['dof'] > 2: val /= 1000
                    if key == 'final_damage': val *= 100
                    v.append(val)
                axs[k].bar(np.arange(len(modes)) + o * 0.4 - 0.2, v, 0.4, color=c, label=d)
            axs[k].set_xticks(range(len(modes))); axs[k].set_xticklabels(modes, rotation=45, ha='right'); axs[k].set_ylabel(lab); axs[k].legend(); axs[k].grid(alpha=.3, axis='y')
        fig.suptitle('Test 3: 6-DOF (100 N preload, displacement-controlled tested DOF)'); plt.tight_layout(); plt.savefig('figures/test3_summary.png', dpi=100); plt.close()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'summary':
        summary_figures(); sys.exit()
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if what in ('all', 'method'): method_figure()
    for kind, pat in (('static', 'results/test1_static/*'), ('cyclic', 'results/test2_cyclic/*'), ('sixdof', 'results/test3_6dof/*')):
        if what not in ('all', kind): continue
        for d in sorted(glob.glob(pat)):
            if not os.path.exists(f'{d}/frames.npz'): continue
            if os.path.exists(f'{d}/curves.png') and os.path.getmtime(f'{d}/curves.png') > os.path.getmtime(f'{d}/frames.npz'): continue
            print('visualising', d, flush=True)
            case_figures(d, kind)
            if kind == 'static' or d.endswith(('flexion', 'axial_rot_pos', 'shear_ant')) or 'L0750' in d or 'L0500' in d:
                interactive_3d(d)
