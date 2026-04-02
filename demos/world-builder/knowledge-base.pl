% --- CHARACTERS & FACTIONS ---
character(elara, 'Science Officer').
character(kane, 'Security Lead').
character(mira, 'Freelancer').
character(vance, 'Diplomat').

faction(elara, solar_council).
faction(kane, solar_council).
faction(mira, void_nomads).
faction(vance, outer_rim_union).

% --- WORLD STATE (Locations & Items) ---
% at(Entity, Location)
at(elara, station_zenith).
at(kane, station_zenith).
at(mira, asteroid_b_612).
at(vance, lunar_base_one).

% possesses(Character, Item)
possesses(elara, signal_decryptor).
possesses(mira, ancient_relic).
possesses(kane, master_key).

% --- SECRET MOTIVES & LORE ---
% knows(Character, Secret)
knows(elara, signal_coordinates).
knows(vance, traitor_identity).
knows(mira, signal_coordinates). % How does she know? (Narrative Hook)

% Hidden Alliances
ally(solar_council, outer_rim_union).
rival(solar_council, void_nomads).

% --- COMPLEX RULES (The "Power" Layer) ---

% REACHABILITY: Can Character A meet Character B?
% (Uses location and faction-controlled travel rules)
can_meet(P1, P2) :-
    at(P1, Loc),
    at(P2, Loc).
can_meet(P1, P2) :-
    at(P1, Loc1),
    at(P2, Loc2),
    connected(Loc1, Loc2).

% TRAITOR LOGIC: A character is a 'suspect' if they are in a Faction 
% but possess an item belonging to a Rival faction, OR know a secret they shouldn't.
is_suspect(C) :-
    faction(C, F1),
    possesses(C, Item),
    originally_from(Item, F2),
    rival(F1, F2).
is_suspect(C) :-
    faction(C, F1),
    knows(C, Secret),
    protected_by(Secret, F2),
    rival(F1, F2).

% NARRATIVE CONSISTENCY: Is the world state "legal"?
% (Ensures no character is in two places or owns the same unique item)
world_is_consistent :-
    \+ (at(C, L1), at(C, L2), L1 \= L2),
    \+ (possesses(C1, I), possesses(C2, I), C1 \= C2).

% RECURSIVE INFLUENCE: Who can influence whom?
% (Social network: P1 influences P2 if they are allies or P1 knows P2's secret)
can_influence(P1, P2) :-
    faction(P1, F), faction(P2, F).
can_influence(P1, P2) :-
    knows(P1, Secret),
    is_about(Secret, P2).