% --- HARD FACTS (The "Truth" Layer) ---
% Components & Origins
component(mc_707, processor).
component(cap_x1, capacitor).
component(sub_pcb_v2, motherboard).

% Assembly (What is inside what)
part_of(cap_x1, sub_pcb_v2).
part_of(sub_pcb_v2, mc_707).

% Vendor Chain
supplied_by(cap_x1, 'Volt-Tech Inc').
supplied_by('Volt-Tech Inc', 'Primary-Ores LLC').

% The Red List (Global Sanctions - Updated via Agent)
sanctioned('Primary-Ores LLC', reason(forced_labor)).
certified_factory('Volt-Tech Inc', region(austria)).

% --- RULES (The Compliance Engine) ---

% RECURSIVE ORIGIN: Who is the ultimate source of a component?
ultimate_source(Component, Source) :-
    supplied_by(Component, Source),
    \+ supplied_by(Source, _). % If the source has no supplier, it's the root.
ultimate_source(Component, Source) :-
    supplied_by(Component, Mid),
    ultimate_source(Mid, Source).

% TRACE RISK: A component is 'at_risk' if ANY entity in its chain is sanctioned.
has_risk(Component) :-
    supplied_by(Component, Vendor),
    (sanctioned(Vendor, _) ; has_risk(Vendor)).

% COMPLIANCE CHECK: A product is 'seizable' if it contains ANY at_risk parts.
is_seizable(Product) :-
    part_of(Sub, Product),
    (has_risk(Sub) ; is_seizable(Sub)).