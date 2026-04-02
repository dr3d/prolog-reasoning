# Demo: Abyss-Alpha Outpost

**Domain:** Robotic station safety and operational readiness  
**Prolog features exercised:** Recursive part hierarchies, negation-as-failure, numeric comparison, transitive access control

---

## The Problem

You're managing a remote outpost with autonomous robotic units. An LLM asked "is rov_01 okay?" at high temperature will say something like "It's in Sector 7 doing its job." It won't trace the fault three levels deep through the part hierarchy.

Prolog will.

---

## What's in the KB

**Facts:**
- Three units: `rov_01` (explorer), `rov_02` (repair), `drone_alpha` (surveillance)
- Battery levels, locations, component hierarchies, access clearances
- `gimbal_lock` is `faulty`, and `gimbal_lock` is a part of `thruster_main`, which is a part of `rov_01`

**Rules:**
- `can_enter(Unit, Sector)` — compares unit clearance level against sector requirement
- `is_compromised(Unit)` — recursively checks if any part or sub-part is faulty
- `mission_ready(Unit)` — battery > 20% AND not compromised
- `is_blocking(Unit, Sector)` — unit is present but not mission-ready

---

## Run It

```bash
cd demos/abyss-alpha

# Who is mission-ready?
python3 ../../prolog-executor.py "mission_ready(X)" -kb knowledge-base.pl
# {"success": false, "error": "No solutions found"}
# rov_01: compromised (faulty gimbal). rov_02: battery 12%. drone_alpha: no battery fact.
# Nobody is ready — that's the correct answer from the KB as written.

# Can rov_01 enter Sector 7?
python3 ../../prolog-executor.py "can_enter(rov_01, sector_7)" -kb knowledge-base.pl
# {"success": true, "bindings": [{}]}
# Explorer clearance is level_2; sector_7 requires level_2. Passes.

# Can rov_01 enter the reactor core?
python3 ../../prolog-executor.py "can_enter(rov_01, reactor_core)" -kb knowledge-base.pl
# {"success": false, "error": "No solutions found"}
# Reactor requires level_4; explorer only has level_2. Deduced — never explicitly stated.

# Is rov_01 compromised?
python3 ../../prolog-executor.py "is_compromised(rov_01)" -kb knowledge-base.pl
# {"success": true, "bindings": [{}]}
# Traces: rov_01 → thruster_main → gimbal_lock → status(faulty). Three levels deep.

# What is currently blocking a sector?
python3 ../../prolog-executor.py "is_blocking(Unit, Sector)" -kb knowledge-base.pl
# {"success": true, "bindings": [{"Unit": "rov_01", "Sector": "sector_7"}]}
# rov_01 is physically in sector_7 but not mission-ready. It's a bottleneck.

# List all clearance levels in the system
python3 ../../prolog-executor.py "findall(L, clearance(_, L), Levels)" -kb knowledge-base.pl
# {"success": true, "bindings": [{"Levels": "[level_2, level_3]"}]}
```

---

## Why This Is a Good Test

The `is_compromised` rule is the key one. `gimbal_lock` is not directly attached to `rov_01` — it's a sub-part of `thruster_main`. The fault chain only surfaces through recursive `part_of` traversal. An LLM that summarized this KB a few turns ago would have flattened that hierarchy. Prolog doesn't summarize — it traces.

The `can_enter` / `reactor_core` result is the cleanest demonstration of transitive deduction: the KB never says `rov_01` can't enter `reactor_core`. The engine infers it by comparing numeric clearance levels.
