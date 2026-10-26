# How the four roles are run (evo)

PI 2026-10-26: four roles, each independent, cooperating and supervising each other; data must not get mixed up; use expert methods.

## Methods borrowed
| Method | Where it comes from | What we take |
|---|---|---|
| Independent verification & validation (IV&V) | NASA / IEEE 1012 | the checker is organisationally separate from the builder and works only from delivered artifacts |
| Separation of duties, two-person rule | quality / safety engineering (ISO 13485 design reviews) | no role approves its own work; rule changes need the owner + PI |
| Blackboard architecture | Hayes-Roth 1985 (multi-expert AI systems) | one shared board with fixed sections; each expert writes only its own section |
| Standard operating procedures + structured outputs | MetaGPT (Hong 2023) | every role hands over a fixed-format JSON, not free chat; publish / subscribe instead of everyone reading everything |
| Debate / red teaming | Irving 2018 "AI safety via debate"; Du 2023 multi-agent debate | the red team argues against the others; findings need evidence and are judged, not just voiced |
| Blinding | peer review, clinical trials | the verifier and the safety guard see results and code, not the designer's reasoning or hopes |
| Provenance (data lineage) | W3C PROV | every number points to the code version, input hashes and seed that produced it |
| ASME V&V 40 | FDA-recognised standard for medical-device simulations | credibility gates for the solver; verifier owns them |

## Who owns what (single owner per thing)
| Thing | Owner (only one who may change it) | Others |
|---|---|---|
| design proposals (programs, encodings, mutation ideas) | designer | read |
| engine + solver code, archive database | engine (Claude main session = integrator) | read; changes via change request |
| test suite, reproducibility checks, credibility gates | verifier | read |
| constraint list S1-S9 + its code (`constraints.py`) | safety guard (any change also needs the PI) | read |
| findings register | red team | read, reply in the finding |
| decisions / rule changes | PI (integrator writes them into DECISIONS.md) | - |

## Folder layout (no mixing)
```
human_study/evo/
  board/            shared blackboard, append-only; one file per round per role: board/r0007/designer.json, verifier.json ...
  archive/          engine only: evaluated designs (genome, voxels, L0/L1/L2 results, provenance), never edited by roles
  roles/<role>/     each role's private workspace (notes, scratch); no other role reads or writes it
  requests/         change requests (CR-xxxx.json): who asks, target owner, reason, evidence, status
  findings/         red-team findings (F-xxxx.json): severity, evidence, target, 2-3 fix options, status
  ISSUES.md         open items for the PI (digest, written by the integrator)
```
Enforced, not just agreed: each role runs as a separate headless `claude -p` process with its own system prompt and
`--allowed-tools` limited to reading the public folders and writing only `roles/<role>/` and its own `board/` file
(red team: also `findings/`). No role can edit code, the archive or another role's files.

## One round (gated pipeline)
1. designer -> `board/rN/designer.json`: new programs / mutation ideas (max 10, schema-checked).
2. engine evaluates (L0 -> L1 -> chosen L2), writes `archive/` + round report (numbers only, with provenance).
3. verifier (blinded to designer's reasoning) -> re-runs a random sample with fixed seeds, checks provenance and gates;
   verdict PASS / HOLD (+ reasons). HOLD stops promotion of the round's results.
4. safety guard (blinded) -> checks every promoted design against S1-S9 and the purpose; can VETO single designs, cannot add rules (only propose via CR to the PI).
5. red team -> attacks steps 1-4 (L1 model exploits, missed checks, unsafe loopholes, data mix-ups); every finding: severity, reproducible evidence, 2-3 options.
6. integrator: applies verdicts, answers each finding (fix / reject with reason / escalate to PI), writes the digest to ISSUES.md.
Next round starts only when 3 + 4 are not HOLD / open-critical.

## Keeping the data clean
- Archive entries are immutable; a correction is a new entry that points to the old one (`supersedes`).
- Every result carries: code git hash, solver version, input file hashes, seed, settings class (same idea as h24 preflight).
- Roles exchange only schema-checked JSON (invalid -> rejected, not "interpreted").
- Each role gets a short round digest, not the whole history (fresh context per round, its own notes in roles/<role>/).
- Ids: designs E-<round>-<n>, findings F-<n>, requests CR-<n>; referenced, never copied.

## Supervision and incentives
- Red team is scored by confirmed findings (verifier reproduces them); unconfirmed claims are closed.
- Designer is scored by archive cells it fills that pass verifier + safety (novelty that survives), not by L1 score alone.
- Verifier is itself audited: the red team may plant known-bad results (canaries); missing them is a finding.
- Disagreement that two rounds do not settle -> PI.
