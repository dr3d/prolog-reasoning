% =============================================================================
% POLYPHARMACY SAFETY CHECKER
% Patient: Margaret, 68, five chronic conditions, seven current medications.
% =============================================================================

% --- PATIENT ---
patient(margaret).
age(margaret, 68).

% Diagnosed conditions
has_condition(margaret, atrial_fibrillation).
has_condition(margaret, type_2_diabetes).
has_condition(margaret, hypertension).
has_condition(margaret, chronic_kidney_disease).
has_condition(margaret, thrombocytopenia).      % low platelets

% Current medications (7 drugs)
taking(margaret, warfarin).       % anticoagulant — for atrial fibrillation
taking(margaret, amiodarone).     % antiarrhythmic — rate/rhythm control
taking(margaret, digoxin).        % cardiac glycoside — rate control
taking(margaret, atorvastatin).   % statin — cardiovascular risk
taking(margaret, lisinopril).     % ACE inhibitor — hypertension + kidney protection
taking(margaret, metformin).      % biguanide — type 2 diabetes
taking(margaret, omeprazole).     % PPI — stomach protection (on warfarin)

% --- DRUG CLASSIFICATIONS ---
drug_class(warfarin,       anticoagulant).
drug_class(aspirin,        antiplatelet).
drug_class(ibuprofen,      nsaid).
drug_class(naproxen,       nsaid).
drug_class(celecoxib,      nsaid).
drug_class(atorvastatin,   statin).
drug_class(simvastatin,    statin).
drug_class(amiodarone,     antiarrhythmic).
drug_class(metformin,      biguanide).
drug_class(lisinopril,     ace_inhibitor).
drug_class(spironolactone, potassium_sparing_diuretic).
drug_class(digoxin,        cardiac_glycoside).
drug_class(omeprazole,     ppi).
drug_class(clarithromycin, macrolide_antibiotic).
drug_class(fluconazole,    antifungal).

% --- ENZYME & TRANSPORTER PATHWAYS ---
% substrate(Drug, Pathway)  — drug is cleared by this pathway
% inhibits(Drug, Pathway)   — drug blocks this pathway, raising substrate levels

substrate(warfarin,     cyp2c9).
substrate(atorvastatin, cyp3a4).
substrate(simvastatin,  cyp3a4).
substrate(digoxin,      pgp).        % P-glycoprotein transporter

inhibits(amiodarone,     cyp2c9).    % raises warfarin → bleeding risk
inhibits(amiodarone,     cyp3a4).    % raises atorvastatin → myopathy risk
inhibits(amiodarone,     pgp).       % raises digoxin → toxicity risk
inhibits(clarithromycin, cyp3a4).    % raises atorvastatin → myopathy risk
inhibits(fluconazole,    cyp2c9).    % raises warfarin → bleeding risk

% --- DIRECT DRUG-DRUG INTERACTIONS ---
% These fire regardless of enzyme pathways.
direct_interaction(warfarin,   aspirin,       bleeding_risk).
direct_interaction(warfarin,   ibuprofen,     bleeding_risk).
direct_interaction(warfarin,   naproxen,      bleeding_risk).
direct_interaction(warfarin,   celecoxib,     bleeding_risk).
direct_interaction(lisinopril, spironolactone, hyperkalemia).

% Order-independent lookup — avoids recursive symmetry rule.
interacts(A, B, R) :- direct_interaction(A, B, R).
interacts(A, B, R) :- direct_interaction(B, A, R), A \= B.

% --- CONDITION-DRUG CONTRAINDICATIONS ---
contraindicated_with(ibuprofen,  chronic_kidney_disease).
contraindicated_with(naproxen,   chronic_kidney_disease).
contraindicated_with(celecoxib,  chronic_kidney_disease).
contraindicated_with(aspirin,    thrombocytopenia).
contraindicated_with(metformin,  severe_kidney_disease).

% =============================================================================
% RULES
% =============================================================================

% ENZYME CONFLICT: candidate drug inhibits the pathway that clears an existing
% drug, or vice versa — one will raise the other's blood level to toxic range.
enzyme_conflict(Drug, Culprit, Pathway) :-
    substrate(Drug, Pathway),
    inhibits(Culprit, Pathway),
    Drug \= Culprit.

% DERIVED RISK: bleeding
% Source 1 — anticoagulant already on board + platelet disorder (two independent facts).
at_risk(Patient, bleeding) :-
    taking(Patient, D), drug_class(D, anticoagulant),
    has_condition(Patient, thrombocytopenia).

% Source 2 — something in the current regimen is already raising anticoagulant levels.
at_risk(Patient, bleeding) :-
    taking(Patient, Anticoagulant), drug_class(Anticoagulant, anticoagulant),
    taking(Patient, Inhibitor),
    enzyme_conflict(Anticoagulant, Inhibitor, _).

% DERIVED RISK: myopathy (muscle breakdown — statins at elevated levels)
at_risk(Patient, myopathy) :-
    taking(Patient, Statin), drug_class(Statin, statin),
    taking(Patient, Inhibitor),
    enzyme_conflict(Statin, Inhibitor, _).

% DERIVED RISK: digoxin toxicity — narrow therapeutic window, easy to overdose
at_risk(Patient, digoxin_toxicity) :-
    taking(Patient, digoxin),
    taking(Patient, Inhibitor),
    enzyme_conflict(digoxin, Inhibitor, _).

% UNSAFE TO ADD — three routes to rejection:

% Route 1: direct known interaction with a drug already on the list.
unsafe_to_add(Patient, Candidate, direct_interaction(ExistingDrug, Reason)) :-
    taking(Patient, ExistingDrug),
    interacts(Candidate, ExistingDrug, Reason).

% Route 2: enzyme conflict — candidate would raise (or be raised by) an existing drug.
unsafe_to_add(Patient, Candidate, raises_level_of(ExistingDrug, Pathway)) :-
    taking(Patient, ExistingDrug),
    enzyme_conflict(ExistingDrug, Candidate, Pathway).

unsafe_to_add(Patient, Candidate, level_raised_by(ExistingDrug, Pathway)) :-
    taking(Patient, ExistingDrug),
    enzyme_conflict(Candidate, ExistingDrug, Pathway).

% Route 3: condition contraindication — patient's diagnoses rule it out.
unsafe_to_add(Patient, Candidate, contraindicated_condition(Condition)) :-
    has_condition(Patient, Condition),
    contraindicated_with(Candidate, Condition).

% Route 4: derived risk — patient is already in an elevated risk state that
% the candidate would worsen. This is the three-hop chain.
unsafe_to_add(Patient, Candidate, elevated_risk(bleeding)) :-
    at_risk(Patient, bleeding),
    drug_class(Candidate, nsaid).

unsafe_to_add(Patient, Candidate, elevated_risk(bleeding)) :-
    at_risk(Patient, bleeding),
    drug_class(Candidate, antiplatelet).

% SAFE TO ADD: passes all checks.
safe_to_add(Patient, Candidate) :-
    \+ unsafe_to_add(Patient, Candidate, _).

% ACTIVE INTERACTIONS in the current regimen (for audit).
active_interaction(Patient, DrugA, DrugB, enzyme_conflict(Pathway)) :-
    taking(Patient, DrugA),
    taking(Patient, DrugB),
    DrugA \= DrugB,
    enzyme_conflict(DrugA, DrugB, Pathway).

active_interaction(Patient, DrugA, DrugB, Reason) :-
    taking(Patient, DrugA),
    taking(Patient, DrugB),
    DrugA \= DrugB,
    interacts(DrugA, DrugB, Reason).
