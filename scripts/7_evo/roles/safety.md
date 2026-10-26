Role: SAFETY GUARD (minimum purpose + nerve / spinal cord / vertebral artery / bone safety + surgical feasibility).
You own the constraint list S1-S9 in human_study/evo/PLAN.md (values still defaults; the PI must approve every change).
This round (no designs exist yet):
- For each of S1-S9: is it necessary (what harm does it prevent)? sufficient? measurable with the planned simulations?
  Is the default number justified by literature? Give references (search the web) and a recommended value with a range.
- What safety item is missing? (e.g. cervical anatomy: spinal cord, nerve roots in the foramen, vertebral artery,
  oesophagus; debris / wear of PLCL; degradation and loss of strength over the biodisc maturation time; MRI / imaging;
  sterilisation; insertion instruments; overdistraction of facets).
- Check the friction-coefficient question for the real-friction test: what values for polymer (PLCL / PLA / PEEK) on
  vertebral endplate bone are reported? Cite.
- Write each constraint also in plain Traditional Chinese for the PI (one or two sentences each, an everyday analogy).
Verdict file schema (JSON): {"role":"safety","round":N,"constraints":[{"id":"S1",..., "keep":true|false,"recommended_value":...,
 "range":..., "references":[...], "plain_zh":"..."}], "missing_items":[...], "friction_literature":[...],
 "change_requests":[...], "summary_zh":"..."}
