% --- HARD FACTS ---
% Robotic Units
unit(rov_01, explorer).
unit(rov_02, repair).
unit(drone_alpha, surveillance).

% Status & Sensors (The "preciseness" the agent updates)
battery(rov_01, 85).
battery(rov_02, 12).
location(rov_01, sector_7).
location(rov_02, repair_bay).

% Maintenance Dependencies (Component -> Sub-component)
part_of(thruster_main, rov_01).
part_of(gimbal_lock, thruster_main).
status(gimbal_lock, faulty).

% Access Levels
clearance(explorer, level_2).
clearance(repair, level_3).
requires_clearance(sector_7, level_2).
requires_clearance(reactor_core, level_4).

% --- RULES (The Reasoning Power) ---

% A unit can enter a sector if its clearance meets or exceeds the requirement.
can_enter(Unit, Sector) :-
    unit(Unit, Type),
    clearance(Type, ULevel),
    requires_clearance(Sector, SLevel),
    ULevel >= SLevel.

% Recursive: A unit is 'compromised' if any of its parts (or sub-parts) are faulty.
is_compromised(Unit) :-
    part_of(Part, Unit),
    (status(Part, faulty) ; is_compromised(Part)).

% A unit is mission_ready only if it has > 20% battery AND is not compromised.
mission_ready(Unit) :-
    unit(Unit, _),
    battery(Unit, B),
    B > 20,
    \+ is_compromised(Unit).

% Identifying bottlenecks: What unit is blocking a sector?
is_blocking(Unit, Sector) :-
    location(Unit, Sector),
    \+ mission_ready(Unit).
