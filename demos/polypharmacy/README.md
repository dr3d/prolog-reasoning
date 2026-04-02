# Demo: Polypharmacy Safety Checker

**Domain:** Multi-drug interaction and patient safety  
**Prolog features exercised:** Recursive risk derivation, multi-hop inference, negation-as-failure, compound reason terms, findall audit

---

## The Problem

Margaret is 68, has five chronic conditions, and is on seven medications. Her cardiologist wants to add ibuprofen for joint pain. Is that safe?

An LLM asked this question will probably say "ibuprofen should be used cautiously with warfarin." That's true but incomplete — and it's the wrong level of reasoning. The real answer requires three independent facts that the model has to hold simultaneously:

1. Margaret is on `warfarin` (anticoagulant)
2. Margaret has `thrombocytopenia` (low platelets — already impaired clotting)
3. Therefore she is in an `elevated_risk(bleeding)` state
4. `ibuprofen` is an NSAID — contraindicated in elevated bleeding risk

The engine derives step 3 from steps 1 and 2. Nobody told it Margaret is at bleeding risk. It figured that out. Then it used that derived state to block ibuprofen at step 4.

That's three hops. Across a long clinical session, with notes and lab values and medication adjustments in between, an LLM will drop one of them. Prolog doesn't.

---

## What's in the KB

**Patient facts:**
- Five conditions: `atrial_fibrillation`, `type_2_diabetes`, `hypertension`, `chronic_kidney_disease`, `thrombocytopenia`
- Seven current medications: `warfarin`, `amiodarone`, `digoxin`, `atorvastatin`, `lisinopril`, `metformin`, `omeprazole`

**Drug facts:**
- Drug classifications (anticoagulant, statin, NSAID, etc.)
- Enzyme/transporter pathways — which drugs are metabolized by CYP2C9, CYP3A4, P-glycoprotein
- Which drugs inhibit which pathways (raising co-substrate blood levels)
- Direct drug-drug interaction table
- Condition-drug contraindication table

**Rules:**
- `enzyme_conflict/3` — drug A's clearance pathway is inhibited by drug B → A accumulates
- `at_risk/2` — derives patient risk states from combinations of conditions and current meds
- `unsafe_to_add/3` — four routes to rejection: direct interaction, enzyme conflict, condition contraindication, derived risk state
- `safe_to_add/2` — passes all checks
- `active_interaction/4` — audits interactions already present in the current regimen

---

## Run It

```bash
cd demos/polypharmacy

# What risk states is Margaret currently in?
python3 ../../prolog-executor.py "at_risk(margaret, Risk)" -kb knowledge-base.pl
# {"success": true, "bindings": [
#   {"Risk": "bleeding"},       ← warfarin + thrombocytopenia
#   {"Risk": "bleeding"},       ← warfarin levels elevated by amiodarone (CYP2C9)
#   {"Risk": "myopathy"},       ← atorvastatin levels elevated by amiodarone (CYP3A4)
#   {"Risk": "digoxin_toxicity"} ← digoxin levels elevated by amiodarone (P-gp)
# ]}
# Three of her four current risk states trace back to amiodarone.
# Nobody flagged this explicitly. The engine derived all of it.

# Can we add ibuprofen?
python3 ../../prolog-executor.py "unsafe_to_add(margaret, ibuprofen, Reason)" -kb knowledge-base.pl
# {"success": true, "bindings": [
#   {"Reason": "direct_interaction(warfarin, bleeding_risk)"},
#   {"Reason": "contraindicated_condition(chronic_kidney_disease)"},
#   {"Reason": "elevated_risk(bleeding)"}
# ]}
# Three independent reasons. The third one — elevated_risk(bleeding) — was derived,
# not stored. Nobody wrote "ibuprofen is dangerous for Margaret."

# Can we add clarithromycin (antibiotic)?
python3 ../../prolog-executor.py "unsafe_to_add(margaret, clarithromycin, Reason)" -kb knowledge-base.pl
# {"success": true, "bindings": [{"Reason": "raises_level_of(atorvastatin, cyp3a4)"}]}
# Clarithromycin inhibits CYP3A4 → atorvastatin accumulates → myopathy risk.
# No direct interaction fact was needed. The enzyme pathway did the work.

# Can we add fluconazole (antifungal)?
python3 ../../prolog-executor.py "unsafe_to_add(margaret, fluconazole, Reason)" -kb knowledge-base.pl
# {"success": true, "bindings": [{"Reason": "raises_level_of(warfarin, cyp2c9)"}]}
# Fluconazole inhibits CYP2C9 → warfarin accumulates → bleeding risk.
# Same rule, different drug, same mechanism caught.

# What interactions already exist in the current regimen?
python3 ../../prolog-executor.py "active_interaction(margaret, DrugA, DrugB, Reason)" -kb knowledge-base.pl
# {"success": true, "bindings": [
#   {"DrugA": "warfarin",     "DrugB": "amiodarone", "Reason": "enzyme_conflict(cyp2c9)"},
#   {"DrugA": "digoxin",      "DrugB": "amiodarone", "Reason": "enzyme_conflict(pgp)"},
#   {"DrugA": "atorvastatin", "DrugB": "amiodarone", "Reason": "enzyme_conflict(cyp3a4)"}
# ]}
# Amiodarone is interacting with three other drugs already on the list.
# This is a pre-existing problem in the regimen — not a hypothetical.

# Is omeprazole safe to add? (It's already on the list — but as a candidate check)
python3 ../../prolog-executor.py "safe_to_add(margaret, omeprazole)" -kb knowledge-base.pl
# {"success": true, "bindings": [{}]}
# No conflicts. (Omeprazole inhibits CYP2C19, which nothing in this regimen uses.)
```

---

## The Amiodarone Problem

Run the active interaction audit and you'll notice: amiodarone appears in every result. It's interacting with warfarin, digoxin, and atorvastatin simultaneously — all through enzyme inhibition. No single interaction fact captures this. The engine assembled it from three substrate facts and one inhibitor fact.

A doctor reviewing this patient's chart one drug at a time would likely catch the warfarin interaction (it's well-known). They might miss the digoxin toxicity risk. They almost certainly won't hold all three simultaneously and think "amiodarone is the common factor here."

Prolog sees all of it at once.

---

## Adding a New Sanction

New evidence comes in: `naproxen` is being flagged as contraindicated for patients with both CKD and anticoagulant therapy. Add one line to the KB:

```prolog
contraindicated_with(naproxen, chronic_kidney_disease).
```

Every subsequent check of `unsafe_to_add(margaret, naproxen, _)` now returns the correct result — no re-summarization, no re-training, no cache to flush.
