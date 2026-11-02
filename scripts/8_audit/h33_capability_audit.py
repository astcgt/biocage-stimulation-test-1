"""Platform capability audit: verdict of every capability object per platform configuration (PI 2026-11-01 / 11-02).

Object model (rules in human_study/PLATFORM_CAPABILITIES.md, instances in human_study/platform_capabilities.json):
  Capability ([物理] [數值] [速度] [觀測] [多元]; secondary [泛化] [時程]) -> Facets -> Checks
  Check       one measurable test: method, threshold, configs it applies to, required (blocking) or advisory,
              the platform Components it depends on, and a status per Config (pass / fail / partial / not_run / deferred + date)
  Restriction a usage limit attached to checks: 'bounded' (deviation direction and bound known -> results usable with the
              limit; upgrades the check to 有條件合格), 'exclusion' (results must not be used for X; no upgrade), 'scope'
              (sentence every conclusion must carry; secondary capabilities)
  Component   platform files; a component modified after a check's evidence date makes that check STALE: re-run it, or, if the
              change cannot affect it, add status.reconfirmed {date, note} (the evidence date itself is never moved)
Verdict of a facet for one config = worst over its required checks:
  pass -> 合格;  fail -> 不合格 (有條件合格 if a bounded restriction covers it);
  partial / not_run / stale -> 未評 (有條件合格 if a bounded restriction covers it).   Capability = worst facet.
  Order 合格 < 有條件合格 < 未評 < 不合格; secondary capabilities report 暫緩. Advisory checks are listed, never counted.
usage: python scripts/8_audit/h33_capability_audit.py              # validate, write human_study/CAPABILITY_SCORECARD.md, print summary
       python scripts/8_audit/h33_capability_audit.py impact <component id | file path> [...]   # checks to re-run after a change
       python scripts/8_audit/h33_capability_audit.py --check      # validate the registry only (exit 1 on errors)
"""
import os, sys, json, time
from dataclasses import dataclass, field
from datetime import datetime

P = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REG = os.path.join(P, 'human_study/platform_capabilities.json')
OUT = os.path.join(P, 'human_study/CAPABILITY_SCORECARD.md')
ORDER = ['合格', '有條件合格', '未評', '不合格']
STATE_ZH = {'pass': '通過', 'fail': '不通過', 'partial': '部分', 'not_run': '未做', 'deferred': '暫緩', 'stale': '過期'}


def parse_date(s):
    if not s: return None
    return datetime.fromisoformat(s if 'T' in s else s + 'T23:59:59').timestamp()


def worst(vs):
    vs = [v for v in vs if v in ORDER]
    return max(vs, key=ORDER.index) if vs else 'n/a'


@dataclass
class Component:
    id: str
    name: str
    paths: list
    _mtime: float = None

    def mtime(self):                                    # newest file under the component's paths (None if none exist)
        if self._mtime is None:
            ts = []
            for p in self.paths:
                a = os.path.normpath(os.path.join(P, p))
                if os.path.isfile(a): ts.append(os.path.getmtime(a))
                for root, dirs, files in os.walk(a):
                    dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git')]
                    ts += [os.path.getmtime(os.path.join(root, f)) for f in files]
            self._mtime = max(ts) if ts else 0.0
        return self._mtime or None


@dataclass
class Restriction:
    id: str
    type: str
    configs: list
    covers: list
    text: str
    refs: list = field(default_factory=list)


@dataclass
class Check:
    id: str
    cap: str
    facet: str
    name: str
    required: bool
    configs: list
    depends: list
    status: dict
    raw: dict

    def result(self, cfg, reg):
        """(effective state, components modified after the evidence) for one config; None if not applicable."""
        if cfg not in self.configs: return None
        st = self.status.get(cfg, {'state': 'not_run'})
        t = max([x for x in (parse_date(st.get('date')), parse_date(st.get('reconfirmed', {}).get('date'))) if x] or [0]) or None
        newer = [c for c in self.depends if t and reg.components[c].mtime() and reg.components[c].mtime() > t]
        state = st['state']
        if newer and state in ('pass', 'partial'): state = 'stale'
        return state, newer

    def verdict(self, cfg, reg):
        r = self.result(cfg, reg)
        if r is None: return None
        state = r[0]
        if state == 'deferred': return '暫緩'
        if state == 'pass': return '合格'
        bounded = any(x.type == 'bounded' and self.id in x.covers and cfg in x.configs for x in reg.restrictions.values())
        if bounded: return '有條件合格'
        return '不合格' if state == 'fail' else '未評'


@dataclass
class Facet:
    id: str
    name: str
    question: str
    checks: list = field(default_factory=list)

    def verdict(self, cfg, reg):
        return worst([c.verdict(cfg, reg) for c in self.checks if c.required])


@dataclass
class Capability:
    id: str
    label: str
    name: str
    priority: str
    question: str
    facets: dict

    def verdict(self, cfg, reg):
        if not any(cfg in c.configs for f in self.facets.values() for c in f.checks): return 'n/a'
        if self.priority == 'secondary': return '暫緩'
        return worst([f.verdict(cfg, reg) for f in self.facets.values()])


class Registry:
    def __init__(self, path=REG):
        d = json.load(open(path, encoding='utf-8'))
        self.configs = d['configs']
        self.components = {k: Component(k, v['name'], v['paths']) for k, v in d['components'].items()}
        self.restrictions = {k: Restriction(k, v['type'], v['configs'], v['covers'], v['text'], v.get('refs', []))
                             for k, v in d['restrictions'].items()}
        self.caps = {k: Capability(k, v['label'], v['name'], v['priority'], v['question'],
                                   {f: Facet(f, fv['name'], fv['question']) for f, fv in v['facets'].items()})
                     for k, v in d['capabilities'].items()}
        self.checks = {}
        self.errors, self.warnings = [], []
        for c in d['checks']:
            if c['id'] in self.checks: self.errors.append(f"duplicate check id {c['id']}"); continue
            ck = Check(c['id'], c['cap'], c['facet'], c['name'], c['required'], c['configs'], c['depends'], c['status'], c)
            self.checks[ck.id] = ck
            if ck.cap not in self.caps or ck.facet not in self.caps[ck.cap].facets:
                self.errors.append(f"{ck.id}: unknown capability/facet {ck.cap}.{ck.facet}"); continue
            self.caps[ck.cap].facets[ck.facet].checks.append(ck)
        self._validate()

    def _validate(self):
        E, W = self.errors, self.warnings
        for ck in self.checks.values():
            E += [f"{ck.id}: unknown config {g}" for g in ck.configs if g not in self.configs]
            E += [f"{ck.id}: unknown component {c}" for c in ck.depends if c not in self.components]
            E += [f"{ck.id}: status for {g} not in its configs" for g in ck.status if g not in ck.configs]
            for g, st in ck.status.items():
                if st.get('state') not in STATE_ZH or st.get('state') == 'stale': E.append(f"{ck.id}/{g}: bad state {st.get('state')}")
                if st.get('state') in ('pass', 'fail', 'partial') and not st.get('date'): W.append(f"{ck.id}/{g}: {st['state']} without a date")
            for e in ck.raw.get('evidence', []):
                if not os.path.exists(os.path.normpath(os.path.join(P, e))): W.append(f"{ck.id}: evidence path missing: {e}")
            if ck.raw.get('threshold_src', '').startswith('提案'): pass  # proposals are listed in the scorecard, not warned
        for r in self.restrictions.values():
            E += [f"{r.id}: covers unknown check {c}" for c in r.covers if c not in self.checks]
            if r.type not in ('bounded', 'exclusion', 'scope'): E.append(f"{r.id}: bad type {r.type}")
        for c in self.components.values():
            if c.mtime() is None: W.append(f"component {c.id}: no files at {c.paths}")
        for cap in self.caps.values():
            for f in cap.facets.values():
                if not any(c.required for c in f.checks): W.append(f"{cap.id}.{f.id}: no required check")

    def impact(self, target):
        a = os.path.normpath(os.path.join(P, target)) if target not in self.components else None
        comps = [target] if a is None else [c.id for c in self.components.values()
                 if any(a == (q := os.path.normpath(os.path.join(P, p))) or a.startswith(q + os.sep) for p in c.paths)]
        return comps, [ck for ck in self.checks.values() if set(ck.depends) & set(comps)]


def cell(ck, cfg, reg):
    r = ck.result(cfg, reg)
    if r is None: return '—'
    s = STATE_ZH[r[0]] + (f"（{','.join(r[1])} 已改動）" if r[1] else '')
    v = ck.status.get(cfg, {}).get('value')
    return s + (f"：{v}" if v else '')


def render(reg):
    cfgs = list(reg.configs)
    L = [f"# 平台能力計分表（自動產生 {time.strftime('%Y-%m-%d %H:%M')}）", '',
         '由 `scripts/8_audit/h33_capability_audit.py` 從 `human_study/platform_capabilities.json` 產生，**不要手改**。'
         '判定規則見 `PLATFORM_CAPABILITIES.md`。門檻來源標「提案」的數字由 PI 拍板（[決定]）。', '',
         '## 1. 總表（能力 × 平台配置）', '', '| 能力 | ' + ' | '.join(f"{g} {reg.configs[g]['name']}" for g in cfgs) + ' |',
         '|---|' + '---|' * len(cfgs)]
    for cap in reg.caps.values():
        L.append(f"| **{cap.label}** {cap.name} | " + ' | '.join(cap.verdict(g, reg) for g in cfgs) + ' |')
    L += ['', '面向層級（必要檢查的最差者）：', '', '| 能力.面向 | ' + ' | '.join(cfgs) + ' |', '|---|' + '---|' * len(cfgs)]
    for cap in reg.caps.values():
        if cap.priority != 'primary': continue
        for f in cap.facets.values():
            L.append(f"| {cap.label} {f.name} | " + ' | '.join(f.verdict(g, reg) for g in cfgs) + ' |')
    L += ['', '## 2. 擋住合格的必要檢查', '', '| 檢查 | 能力 | 配置 | 判定 | 狀態 | 參照 |', '|---|---|---|---|---|---|']
    for ck in reg.checks.values():
        if not ck.required or reg.caps[ck.cap].priority != 'primary': continue
        for g in ck.configs:
            v = ck.verdict(g, reg)
            if v in ('未評', '不合格', '有條件合格'):
                L.append(f"| {ck.id} {ck.name} | {reg.caps[ck.cap].label} | {g} | {v} | {cell(ck, g, reg)} | {', '.join(ck.raw.get('refs', []))} |")
    stale = [(ck, g, r[1]) for ck in reg.checks.values() for g in ck.configs if (r := ck.result(g, reg)) and r[1]]
    L += ['', '## 3. 證據過期（元件在證據日期之後被修改：重跑，或確認改動無關後更新日期並註記）', '']
    L += [f"- {ck.id} {ck.name} [{g}]：{', '.join(f'{c}（{reg.components[c].name}）' for c in cs)}" for ck, g, cs in stale] or ['- 無']
    L += ['', '## 4. 使用限制', '', '| 編號 | 類型 | 配置 | 涵蓋檢查 | 內容 |', '|---|---|---|---|---|']
    tz = {'bounded': '界定（可升為有條件合格）', 'exclusion': '禁用', 'scope': '範圍聲明'}
    L += [f"| {r.id} | {tz[r.type]} | {','.join(r.configs)} | {','.join(r.covers)} | {r.text} |" for r in reg.restrictions.values()]
    L += ['', '## 5. 檢查目錄', '']
    for cap in reg.caps.values():
        L += [f"### {cap.label} {cap.name}" + ('（次要，暫緩）' if cap.priority == 'secondary' else ''), '', cap.question, '']
        for f in cap.facets.values():
            L += [f"**{f.name}** — {f.question}", '', '| ID | 檢查 | 方法 | 門檻（來源） | 必要 | ' + ' | '.join(cfgs) + ' |',
                  '|---|---|---|---|---|' + '---|' * len(cfgs)]
            for ck in f.checks:
                r = ck.raw
                L.append(f"| {ck.id} | {ck.name} | {r['method']} | {r['threshold']}（{r.get('threshold_src') or '—'}） | "
                         f"{'是' if ck.required else '診斷'} | " + ' | '.join(cell(ck, g, reg) for g in cfgs) + ' |')
            L.append('')
    L += ['## 6. 登錄檔檢查', ''] + [f"- 錯誤：{e}" for e in reg.errors] + [f"- 警告：{w}" for w in reg.warnings]
    if not (reg.errors or reg.warnings): L.append('- 無')
    return '\n'.join(L) + '\n'


def main(argv):
    reg = Registry()
    if argv[:1] == ['impact']:
        for t in argv[1:]:
            comps, cks = reg.impact(t)
            print(f"{t}: components {comps or 'none'}")
            for ck in cks: print(f"  re-run {ck.id:7s} {reg.caps[ck.cap].label}{'' if ck.required else '(診斷)'} {ck.name}  [{','.join(ck.configs)}]")
            print(f"  capabilities affected: {sorted({reg.caps[c.cap].label for c in cks})}")
        return 0
    for e in reg.errors: print('ERROR', e)
    for w in reg.warnings: print('warn ', w)
    if argv[:1] == ['--check']: return 1 if reg.errors else 0
    open(OUT, 'w', encoding='utf-8').write(render(reg))
    for cap in reg.caps.values():
        print(f"{cap.label:6s} " + '  '.join(f"{g}:{cap.verdict(g, reg)}" for g in reg.configs))
    print('wrote', os.path.relpath(OUT, P))
    return 1 if reg.errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
