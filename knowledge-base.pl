%% knowledge-base.pl
%% Prolog facts and rules for the prolog-reasoning skill.
%%
%% Conventions:
%%   - Facts use lowercase atoms.
%%   - Variables start with uppercase (standard Prolog).
%%   - Group related predicates together and label each section.
%% ---------------------------------------------------------------


%% ---------------------------------------------------------------
%% SECTION: Family / Hierarchy (starter example — replace freely)
%% ---------------------------------------------------------------

parent(tom,  bob).
parent(tom,  liz).
parent(bob,  ann).
parent(bob,  pat).

grandparent(X, Z) :-
    parent(X, Y),
    parent(Y, Z).

ancestor(X, Y) :- parent(X, Y).
ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).

sibling(X, Y) :-
    parent(P, X),
    parent(P, Y),
    X \= Y.


%% ---------------------------------------------------------------
%% SECTION: Classification
%% ---------------------------------------------------------------

%% Biological taxonomy stubs — extend as needed.
mammal(human).
mammal(dolphin).
mammal(bat).

bird(penguin).
bird(eagle).

can_fly(X) :- bird(X), X \= penguin.
can_fly(bat).

warm_blooded(X) :- mammal(X).
warm_blooded(X) :- bird(X).


%% ---------------------------------------------------------------
%% SECTION: Policy / Rules
%% ---------------------------------------------------------------

%% Example: simple access-control rules.
%% role(User, Role), permission(Role, Action) -> allowed(User, Action)

role(alice, admin).
role(bob,   reader).

permission(admin,  read).
permission(admin,  write).
permission(admin,  delete).
permission(reader, read).

allowed(User, Action) :-
    role(User, Role),
    permission(Role, Action).


%% ---------------------------------------------------------------
%% SECTION: Arithmetic helpers
%% ---------------------------------------------------------------

factorial(0, 1) :- !.
factorial(N, F) :-
    N > 0,
    N1 is N - 1,
    factorial(N1, F1),
    F is N * F1.

fibonacci(0, 0) :- !.
fibonacci(1, 1) :- !.
fibonacci(N, F) :-
    N > 1,
    N1 is N - 1,
    N2 is N - 2,
    fibonacci(N1, F1),
    fibonacci(N2, F2),
    F is F1 + F2.


%% ---------------------------------------------------------------
%% SECTION: Meta / Utility
%% ---------------------------------------------------------------

%% list_facts/1 — print all clauses of a given functor/arity atom.
%% Example: list_facts(parent/2).
list_facts(F/A) :-
    functor(Head, F, A),
    clause(Head, true),
    write(Head), nl,
    fail.
list_facts(_).
