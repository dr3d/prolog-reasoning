# Demo: Singularity Signal — Narrative Continuity Engine

**Domain:** Sci-fi story world state tracking  
**Prolog features exercised:** Epistemic facts (who knows what), faction relationships, location-based reachability, inventory consistency checking

---

## The Problem

Complex narratives drift. An LLM running a long story will eventually put a character in two places, give an item to someone who already lost it, or forget that two factions are rivals. These aren't hallucinations in the usual sense — they're state-tracking failures. The model loses the thread.

A Prolog KB is an authoritative world state. Before the agent writes the next scene, it queries the KB. The world doesn't drift because the world is defined, not remembered.

---

## What's in the KB

**Facts:**
- Four characters: `elara` (Science Officer), `kane` (Security Lead), `mira` (Freelancer), `vance` (Diplomat)
- Faction memberships: elara and kane in `solar_council`, mira in `void_nomads`, vance in `outer_rim_union`
- Locations: elara and kane at `station_zenith`, mira at `asteroid_b_612`, vance at `lunar_base_one`
- Possessions: elara has `signal_decryptor`, mira has `ancient_relic`, kane has `master_key`
- Secrets: elara and mira both know `signal_coordinates` (narrative hook — why does a Nomad know Council secrets?)
- Alliances: `solar_council` allied with `outer_rim_union`, rival to `void_nomads`

**Rules:**
- `can_meet(P1, P2)` — true if same location, or locations are `connected/2` (see below)
- `world_is_consistent` — verifies no character is in two places and no item is held by two people
- `is_suspect(C)` — character is suspect if they possess a rival faction's item or know a secret protected by a rival faction (requires `originally_from/2` and `protected_by/2` facts)
- `can_influence(P1, P2)` — same faction, or P1 knows a secret about P2 (requires `is_about/2` facts)

---

## Run It

```bash
cd demos/world-builder

# Is the world state currently consistent?
python3 ../../prolog-executor.py "world_is_consistent" -kb knowledge-base.pl
# {"success": true, "bindings": [{}]}
# No character is in two places. No item is held by two characters. Clean state.

# Who knows the signal coordinates?
python3 ../../prolog-executor.py "knows(Who, signal_coordinates)" -kb knowledge-base.pl
# {"success": true, "bindings": [{"Who": "elara"}, {"Who": "mira"}]}
# elara (Council) — expected. mira (Nomad) — that's the story hook.

# Can elara and kane meet?
python3 ../../prolog-executor.py "can_meet(elara, kane)" -kb knowledge-base.pl
# {"success": true, "bindings": [{}]}
# Both at station_zenith.

# Can elara meet vance?
python3 ../../prolog-executor.py "can_meet(elara, vance)" -kb knowledge-base.pl
# {"success": false, "error": "No solutions found"}
# Different locations, and no connected/2 facts defined — they cannot meet.

# What does each character possess?
python3 ../../prolog-executor.py "findall(C-I, possesses(C, I), Inventory)" -kb knowledge-base.pl
# {"success": true, "bindings": [{"Inventory": "[(elara - signal_decryptor), (mira - ancient_relic), (kane - master_key)]"}]}
```

---

## Extending the KB

Several rules are defined but require additional facts to fire. Add these to `knowledge-base.pl` to unlock them:

```prolog
% Location connections (for can_meet across stations)
connected(station_zenith, lunar_base_one).

% Item origins (for is_suspect traitor logic)
originally_from(ancient_relic, void_nomads).
originally_from(master_key, solar_council).

% Secret ownership (for is_suspect / protected_by logic)
protected_by(signal_coordinates, solar_council).

% Secret subjects (for can_influence)
is_about(traitor_identity, elara).
```

With those facts loaded:

```bash
# Is anyone a suspect?
python3 ../../prolog-executor.py "is_suspect(X)" -kb knowledge-base.pl
# mira: void_nomad possessing an item originally from a rival faction
# vance: knows traitor_identity — a secret protected by a rival faction

# Who can elara influence?
python3 ../../prolog-executor.py "can_influence(elara, X)" -kb knowledge-base.pl
# kane (same faction), and anyone she knows a secret about
```

---

## Why This Is a Good Test

`world_is_consistent` is the most directly useful rule for an agent writing long-form narrative: run it after every scene update to catch contradictions before they compound. It's a two-line integrity check that an LLM can't reliably do from memory but Prolog does trivially.

The `knows(mira, signal_coordinates)` fact is an intentional narrative hook — it's in the KB as a mystery, not a mistake. The KB doesn't explain it. The story does.
