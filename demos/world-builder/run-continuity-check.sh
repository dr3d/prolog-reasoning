# 1. Audit: Is the story world currently consistent?
python3 prolog-executor.py "world_is_consistent."
# Expected: true. (If false, the Agent has made a narrative error).

# 2. Discovery: Who knows the secret coordinates?
python3 prolog-executor.py "knows(Who, signal_coordinates)."
# Result: {Who: elara}, {Who: mira}
# Follow-up: Why does a Nomad know Council secrets?

# 3. Mystery Solving: Who are the current suspects for the 'signal leak'?
# (Let's add some "Lore" facts first)
python3 prolog-executor.py "assert(originally_from(ancient_relic, void_nomads))."
python3 prolog-executor.py "is_suspect(X)."
# Result: {X: mira} (If she was pretending to be Council) 
# or other complex overlaps.

# 4. Logistics: Can Elara meet Vance to exchange the decryptor?
python3 prolog-executor.py "can_meet(elara, vance)."
# Result: false (They are on different stations).

# 5. Massive Query: List every character, their faction, and their current inventory.
python3 prolog-executor.py "character(C, _), faction(C, F), findall(I, possesses(C, I), Inv)."