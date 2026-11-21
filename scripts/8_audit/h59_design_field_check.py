"""Automatic comparison 'FE model material of every cage element = design field value' (capability check DIV-02, no homogenization).

The design field is the per-voxel hard-phase fraction phi of the cage mesh file (h12: <cage_npz> 'phi', 0.2 mm voxels, region 1 =
cage). The FE model is the deck FEBio read (case.feb): every cage element sits in one material block cage_<kind>_<phi>. For every
deck the check
  1. reads the cage element blocks of case.feb (block name -> phi, element -> its 8 node ids) - the deck itself, not the builder's
     book-keeping;
  2. takes the element -> voxel correspondence from cage_elems.npz (npz_index) and VERIFIES it on the connectivity: the node map
     deck node -> mesh-file node implied by all elements must be one-to-one (a wrong correspondence breaks it at once);
  3. compares phi(block) with the design field for every cage element (fabrication 'mix': the blend fraction phi[npz_index];
     'interleave': the printed voxel material hard[npz_index] = 1 or 0, the rule h14 uses; the share of hard voxels per design-phi
     class is reported), and the number of cage elements with the
     number of cage voxels of the mesh file (no element dropped or merged).
Pass = 100 % of the cage elements of every checked deck agree (threshold of DIV-02).
usage: python h59_design_field_check.py [workers=3]   -> human_study/qa/design_field_check.json (all designs of the tied production
       sets and the friction insertion sets that are verdict sources), exit 1 on any mismatch
"""
import os, sys, json, glob, re, time, numpy as np, xml.etree.ElementTree as ET
from concurrent.futures import ProcessPoolExecutor
P = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); A = os.path.join(P, 'human_study/al_v2')
SETS = ('physio_rot', 'physio_rot_dyn', 'physio_rot_dyn2', 'physio_rot_r2', 'physio_rot_split2', 'physio_rot_split3', 'physio_rot_split4',   # every tied verdict-source set (audit 2026-11-21: only split2 was listed)
        'physio_fric3', 'physio_relG', 'pilot_mu03', 'pilot_mu03G')


def phi_of(name):
    m = re.search(r'_(\d+(?:\.\d+)?)$', name); return float(m.group(1)) if m else None


def one(cd):
    r = dict(case=os.path.relpath(cd, P))
    try:
        prm = json.load(open(os.path.join(cd, 'case.json'))).get('params') or json.load(open(cd.split('_gpu')[0] + '_params.json'))
        mesh = np.load(os.path.join(P, prm['cage_npz']), allow_pickle=True); ce = np.load(os.path.join(cd, 'cage_elems.npz'), allow_pickle=True)
        g = ET.parse(os.path.join(cd, 'case.feb')).getroot().find('Geometry')
        blocks, conn = [], []
        for eb in g.findall('Elements'):
            n = eb.get('name') or ''
            if not n.startswith('cage_') or 'biodisc' in n: continue
            for e in eb: blocks.append(n); conn.append([int(v) for v in e.text.split(',')])
        conn = np.array(conn); idx = ce['npz_index']; hexes = mesh['hexes'][idx]
        r.update(n_cage_elements=len(blocks), n_bookkeeping=int(len(idx)), mesh_file=prm['cage_npz'])
        if len(blocks) != len(idx): r['problem'] = 'deck cage element count differs from cage_elems.npz'; return r
        if list(ce['block']) != blocks: r['problem'] = 'deck block order differs from cage_elems.npz'; return r
        # one-to-one node map deck -> mesh file over all (element, local node) pairs
        a, b = conn.ravel(), hexes.ravel(); order = np.argsort(a, kind='stable'); a, b = a[order], b[order]
        first = np.r_[True, a[1:] != a[:-1]]; ref = np.maximum.accumulate(np.where(first, np.arange(len(a)), 0)); consistent = bool((b == b[ref]).all())
        injective = len(np.unique(b[first])) == int(first.sum())
        r.update(node_map_consistent=consistent, node_map_one_to_one=bool(injective), n_nodes=int(first.sum()))
        info = json.loads(str(mesh['info'])); phi_deck = np.array([phi_of(n) for n in blocks], float); phi_design = mesh['phi'][idx].astype(float)
        # fabrication 'mix': the voxel material is the blend phi; 'interleave': each voxel is printed hard OR soft (mesh-file field 'hard'),
        # the design phi is met by the share of hard voxels - both are the 0.2 mm design field, nothing is averaged over elements
        phi_field = mesh['hard'][idx].astype(float) if info.get('fabrication') == 'interleave' else phi_design
        bad = np.abs(phi_deck - phi_field) > 1e-9
        if info.get('fabrication') == 'interleave':
            r['interleave_hard_share_by_design_phi'] = {f'{v:g}': round(float(phi_field[phi_design == v].mean()), 3) for v in sorted(set(phi_design.tolist()))}
        region = mesh['region'] if 'region' in mesh.files else None
        r.update(n_mismatch=int(bad.sum()), n_cage_voxels=int(info.get('n_cage', -1)),
                                                      phi_values=sorted({float(v) for v in phi_field}), fabrication=info.get('fabrication'), gradient=info.get('gradient'), design=info.get('design'))
        if not consistent or not injective: r['problem'] = 'element correspondence fails the node-map test'
        elif bad.any(): r['problem'] = f'{int(bad.sum())} cage elements whose block phi differs from the design field'
        elif info.get('n_cage') not in (None, len(blocks)): r['problem'] = f"deck has {len(blocks)} cage elements, mesh file {info.get('n_cage')} cage voxels"
    except Exception as ex: r['problem'] = 'error: ' + repr(ex)[:200]
    return r


if __name__ == '__main__':
    nw = int(sys.argv[1]) if len(sys.argv) > 1 else 3; cds = []
    for s in SETS:
        for pj in sorted(glob.glob(os.path.join(A, s, 'p???_params.json'))):
            p = os.path.basename(pj)[:4]; c = [d for d in sorted(glob.glob(os.path.join(A, s, p + '_gpu*'))) + [os.path.join(A, s, p)] if os.path.exists(os.path.join(d, 'case.feb')) and os.path.exists(os.path.join(d, 'cage_elems.npz'))]
            if c: cds.append(c[0])
    with ProcessPoolExecutor(nw) as ex: res = list(ex.map(one, cds))
    bad = [r for r in res if r.get('problem')]
    fam = {}
    for r in res:
        if not r.get('problem'): k = f"{r.get('design')}/{r.get('gradient')}/{r.get('fabrication')}"; fam[k] = fam.get(k, 0) + 1
    json.dump(dict(time=time.strftime('%Y-%m-%dT%H:%M'), sets=SETS, n_decks=len(res), n_ok=len(res) - len(bad), n_cage_elements=sum(r.get('n_cage_elements', 0) for r in res),
                   families_ok=fam, problems=bad, results=res), open(os.path.join(P, 'human_study/qa/design_field_check.json'), 'w'), indent=1)
    for r in bad: print(r['case'], r['problem'])
    print(f'{len(res) - len(bad)} / {len(res)} decks: every cage element = design field; families {fam}'); sys.exit(1 if bad else 0)
