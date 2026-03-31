%% knowledge-base.pl — personal memory domain
%% ---------------------------------------------------------------


%% ---------------------------------------------------------------
%% SECTION: Identity
%% ---------------------------------------------------------------

% person(scott).
% male(scott).  female(dana).
% born(scott, 1981).
% lives_in(scott, austin).
% occupation(scott, developer).


%% ---------------------------------------------------------------
%% SECTION: Relationships
%% ---------------------------------------------------------------

% parent(ann, scott).         % parent(Parent, Child)
% spouse(scott, susan).
% sibling(scott, blake).
% partner(scott, hope).

grandparent(X, Z) :- parent(X, Y), parent(Y, Z).
ancestor(X, Y) :- parent(X, Y).
ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).
sibling(X, Y) :- parent(P, X), parent(P, Y), X \= Y.


%% ---------------------------------------------------------------
%% SECTION: Properties (catch-all)
%% ---------------------------------------------------------------

% property(scott, eye_color, brown).
% property(scott, prefers, dark_mode).


%% ---------------------------------------------------------------
%% SECTION: Events
%% ---------------------------------------------------------------

% event(started_job, '2024-01-15').
% event(moved_to_austin, '2023-06-01').
