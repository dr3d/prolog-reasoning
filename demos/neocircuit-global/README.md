# Demo: NeoCircuit Global Supply Chain

**Domain:** Component supply chain compliance and sanctions risk  
**Prolog features exercised:** Recursive chain traversal, transitive risk propagation, negation-as-failure, nested part hierarchies

---

## The Problem

An LLM summarizing a supplier audit will say "most vendors are certified." Prolog says "one vendor in the chain is sanctioned — the whole product is at risk." These are not the same answer.

The other failure mode: ask an LLM three turns after loading a 50-page supplier PDF whether your processor is compliant. It will hallucinate an answer. Prolog traces the chain from the finished product back to the raw material origin and returns a proof, not a guess.

---

## What's in the KB

**Facts:**
- Three components: `mc_707` (processor), `sub_pcb_v2` (motherboard), `cap_x1` (capacitor)
- Assembly hierarchy: `cap_x1` is inside `sub_pcb_v2`, which is inside `mc_707`
- Vendor chain: `cap_x1` is supplied by `Volt-Tech Inc`, which is supplied by `Primary-Ores LLC`
- `Primary-Ores LLC` is sanctioned for `forced_labor`
- `Volt-Tech Inc` is certified (Austria), but that doesn't save it

**Rules:**
- `ultimate_source(Component, Source)` — recursively finds the root supplier with no upstream vendor
- `has_risk(Component)` — true if any vendor in the supply chain is sanctioned
- `is_seizable(Product)` — true if any sub-component contains an at-risk vendor chain

---

## Run It

```bash
cd demos/neocircuit-global

# Who is the ultimate source of cap_x1?
python3 ../../prolog-executor.py "ultimate_source(cap_x1, Source)" -kb knowledge-base.pl
# {"success": true, "bindings": [{"Source": "'Primary-Ores LLC'"}]}
# Volt-Tech has a supplier, so it's not the root. Primary-Ores has none — it's the origin.

# Is cap_x1 at risk?
python3 ../../prolog-executor.py "has_risk(cap_x1)" -kb knowledge-base.pl
# {"success": true, "bindings": [{}]}
# cap_x1 → Volt-Tech → Primary-Ores (sanctioned). Risk confirmed.

# Is the finished processor seizable?
python3 ../../prolog-executor.py "is_seizable(mc_707)" -kb knowledge-base.pl
# {"success": true, "bindings": [{}]}
# mc_707 contains sub_pcb_v2, which contains cap_x1, which traces to a sanctioned vendor.

# Is sub_pcb_v2 seizable on its own?
python3 ../../prolog-executor.py "is_seizable(sub_pcb_v2)" -kb knowledge-base.pl
# {"success": true, "bindings": [{}]}

# Is Volt-Tech itself sanctioned? (No — it's certified. But it doesn't matter.)
python3 ../../prolog-executor.py "sanctioned('Volt-Tech Inc', R)" -kb knowledge-base.pl
# {"success": false, "error": "No solutions found"}
# Certified factory, clean record — but its upstream supplier is sanctioned.
# has_risk still fires because the rule recurses through the whole chain.
```

---

## Why This Is a Good Test

The `has_risk` rule is the sharp edge here. `Volt-Tech Inc` is certified. A naive check would stop there and return clean. The rule recurses up the vendor chain and finds `Primary-Ores LLC` — one level removed from the direct supplier. The certification doesn't override the sanction upstream.

The real-world version of this: a new sanction is announced. The agent appends one line to the KB:

```prolog
sanctioned('Primary-Ores LLC', reason(forced_labor)).
```

Every product in the catalog is immediately re-evaluated on the next query. No re-summarization, no cache invalidation, no manual audit. The inference happens fresh every time.
