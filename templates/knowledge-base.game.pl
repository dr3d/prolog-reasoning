%% knowledge-base.pl — game state domain
%% ---------------------------------------------------------------


%% ---------------------------------------------------------------
%% SECTION: World / Locations
%% ---------------------------------------------------------------

% location(forest).
% location(village).
% location(cave).
% connected(forest, village).
% connected(village, cave).

reachable(A, B) :- connected(A, B).
reachable(A, B) :- connected(A, C), reachable(C, B).


%% ---------------------------------------------------------------
%% SECTION: Player State
%% ---------------------------------------------------------------

% player_location(village).
% health(player, 100).
% gold(player, 50).


%% ---------------------------------------------------------------
%% SECTION: Inventory
%% ---------------------------------------------------------------

% has(player, sword).
% has(player, torch).
% item_property(sword, damage, 10).
% item_property(torch, light, true).


%% ---------------------------------------------------------------
%% SECTION: Characters / NPCs
%% ---------------------------------------------------------------

% npc(merchant, village).
% npc(guard, cave).
% friendly(merchant).
% hostile(guard).


%% ---------------------------------------------------------------
%% SECTION: Quests / Flags
%% ---------------------------------------------------------------

% quest(find_artifact, active).    % active | complete | failed
% quest_step(find_artifact, 1, enter_cave).   % quest_step(Quest, StepNum, StepName)
% quest_step_done(find_artifact, 1).          % mark done by step number
% flag(door_unlocked).

quest_complete(Q) :-
    quest(Q, _),
    \+ (quest_step(Q, N, _), \+ quest_step_done(Q, N)).
