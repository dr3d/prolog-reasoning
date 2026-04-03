%% knowledge-base.pl — project / task tracking domain
%% ---------------------------------------------------------------


%% ---------------------------------------------------------------
%% SECTION: Tasks
%% ---------------------------------------------------------------

% task(task_id, title_atom).
% status(task_id, todo).       % todo | in_progress | done | blocked
% owner(task_id, alice).
% priority(task_id, high).     % high | medium | low
% due(task_id, '2026-04-15').

% task(t1, setup_ci).
% status(t1, done).
% owner(t1, alice).

% task(t2, write_tests).
% status(t2, in_progress).
% owner(t2, bob).
% depends_on(t2, t1).


%% ---------------------------------------------------------------
%% SECTION: Decisions / Rationale
%% ---------------------------------------------------------------

% decision(use_postgres, '2026-04-01').       % decision(What, When)
% rationale(use_postgres, schema_needed).     % rationale(Decision, Reason)
% decision(drop_redis, '2026-04-02').
% rationale(drop_redis, complexity_not_worth_it).


%% ---------------------------------------------------------------
%% SECTION: Milestones
%% ---------------------------------------------------------------

% milestone(m1, alpha_release, '2026-05-01').
% milestone_task(m1, t1).
% milestone_task(m1, t2).


%% ---------------------------------------------------------------
%% SECTION: Team
%% ---------------------------------------------------------------

% member(alice, team_backend).
% member(bob,   team_backend).
% member(carol, team_frontend).


%% ---------------------------------------------------------------
%% SECTION: Derived
%% ---------------------------------------------------------------

blocked_by(T, D) :- depends_on(T, D), status(D, S), S \= done.

ready(T) :- task(T, _), \+ blocked_by(T, _), status(T, todo).

milestone_complete(M) :-
    milestone(M, _, _),
    \+ (milestone_task(M, T), status(T, S), S \= done).
