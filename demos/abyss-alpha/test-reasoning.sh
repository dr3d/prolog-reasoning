# 1. Simple Retrieval: Who is currently mission ready?
python3 prolog-executor.py "mission_ready(X)."
# Expected: drone_alpha (if battery is high and no faults)
# Logic: rov_01 fails (faulty gimbal), rov_02 fails (low battery)

# 2. Inference: Can rov_01 enter Sector 7?
python3 prolog-executor.py "can_enter(rov_01, sector_7)."
# Expected: true (Explorer has Level 2, Sector 7 needs Level 2)

# 3. Deep Recursion: Why is rov_01 compromised?
python3 prolog-executor.py "part_of(X, rov_01), status(X, faulty)."
# Then follow the chain:
python3 prolog-executor.py "is_compromised(rov_01)."
# This exercises the nested part_of/status rules.

# 4. Negation/Safety: Is any unit currently blocking a vital sector?
python3 prolog-executor.py "is_blocking(Unit, Sector)."
# Expected: {Unit: rov_01, Sector: sector_7} 
# Because rov_01 is in sector_7 but is NOT mission_ready.

# 5. Findall: List all unique clearance levels currently in the system.
python3 prolog-executor.py "findall(L, clearance(_, L), List)."