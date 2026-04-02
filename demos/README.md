# Demos

Four self-contained examples showing what the prolog-reasoning engine does in realistic domains. Each has its own knowledge base, runnable queries, and a README walking through the reasoning.

All demos run from the repo root — no installation required beyond Python 3.

---

## [abyss-alpha](abyss-alpha/) — Robotic Outpost Safety

A remote station with three autonomous units, a component fault buried three levels deep in a part hierarchy, and a clearance system that has to deduce access rights by comparing levels — not by looking them up.

**The sharp edge:** `rov_01` is in Sector 7 but can't do its job. The engine traces the fault chain from `rov_01` → `thruster_main` → `gimbal_lock` → `status(faulty)` and returns the right answer. An LLM that summarized this KB two turns ago would have dropped the gimbal detail.

```bash
python3 prolog-executor.py "is_blocking(Unit, Sector)" -kb demos/abyss-alpha/knowledge-base.pl
# {"success": true, "bindings": [{"Unit": "rov_01", "Sector": "sector_7"}]}
```

---

## [neocircuit-global](neocircuit-global/) — Supply Chain Compliance

A processor that contains a motherboard that contains a capacitor supplied by a vendor whose upstream supplier is sanctioned. The finished product is seizable. The vendor in the middle is certified. Neither of those facts cancels the other.

**The sharp edge:** `Volt-Tech Inc` has a clean factory certification. The engine ignores that and keeps tracing — finding `Primary-Ores LLC` one level up, flagging the entire product. "Most vendors are certified" is not the same as "the product is compliant."

```bash
python3 prolog-executor.py "is_seizable(mc_707)" -kb demos/neocircuit-global/knowledge-base.pl
# {"success": true, "bindings": [{}]}
```

---

## [world-builder](world-builder/) — Narrative Continuity

Four characters, four factions, three locations, a secret that the wrong person knows, and a consistency rule that catches contradictions before they compound across a long story.

**The sharp edge:** `world_is_consistent` is a two-line integrity check — no character in two places, no item held by two people. Run it after every scene update. An LLM can't reliably do this from memory across 50 scenes. Prolog does it in a single query.

```bash
python3 prolog-executor.py "world_is_consistent" -kb demos/world-builder/knowledge-base.pl
# {"success": true, "bindings": [{}]}
```

---

## [polypharmacy](polypharmacy/) — Drug Interaction Safety

A 68-year-old patient on seven medications for five chronic conditions. The question: is it safe to add ibuprofen? The answer requires holding three independent facts simultaneously — anticoagulant on board, platelet disorder present, therefore elevated bleeding risk — and using that derived state to block the NSAID. Three hops. The engine derives the risk state nobody stored, then uses it.

**The sharp edge:** amiodarone is already interacting with three other drugs in the current regimen through enzyme pathway inhibition. No single interaction fact captures all three — the engine assembles them from substrate and inhibitor facts.

```bash
python3 prolog-executor.py "active_interaction(margaret, DrugA, DrugB, Reason)" -kb demos/polypharmacy/knowledge-base.pl
# warfarin/amiodarone, digoxin/amiodarone, atorvastatin/amiodarone — all live problems
```

---

## Running All Four

```bash
# From the repo root:
for kb in demos/*/knowledge-base.pl; do
    echo "=== $kb ==="
    python3 prolog-executor.py --manifest -kb "$kb"
    echo
done
```

See each demo's README for the full query set and expected outputs.
