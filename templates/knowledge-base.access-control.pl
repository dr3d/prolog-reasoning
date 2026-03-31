%% knowledge-base.pl — access control domain
%% ---------------------------------------------------------------


%% ---------------------------------------------------------------
%% SECTION: Users & Roles
%% ---------------------------------------------------------------

% user(alice).
% user(bob).
% role(alice, admin).
% role(bob,   reader).
% role(carol, editor).


%% ---------------------------------------------------------------
%% SECTION: Role Hierarchy
%% ---------------------------------------------------------------

% role_inherits(editor, reader).   % editor has all reader permissions
% role_inherits(admin, editor).

effective_role(User, Role) :- role(User, Role).
effective_role(User, Role) :-
    role(User, R),
    role_inherits(R, Role).


%% ---------------------------------------------------------------
%% SECTION: Permissions
%% ---------------------------------------------------------------

% permission(reader, read).
% permission(editor, read).
% permission(editor, write).
% permission(admin,  read).
% permission(admin,  write).
% permission(admin,  delete).
% permission(admin,  manage_users).


%% ---------------------------------------------------------------
%% SECTION: Resources
%% ---------------------------------------------------------------

% resource(report_q1, finance).    % resource(Name, Category)
% resource(user_data, pii).
% category_restriction(pii, admin).  % only admins can touch pii


%% ---------------------------------------------------------------
%% SECTION: Derived
%% ---------------------------------------------------------------

allowed(User, Action) :-
    effective_role(User, Role),
    permission(Role, Action).

allowed(User, Action, Resource) :-
    allowed(User, Action),
    resource(Resource, Category),
    \+ (category_restriction(Category, Required),
        \+ effective_role(User, Required)).
