# Agent Skill Test — prolog-reasoning

Copy-paste prompts for testing the prolog-reasoning skill against a live agent.
Each prompt is self-contained and targets a specific failure mode.

**What you're watching for in each test:**
- Does the agent use `--assert` (or equivalent) to write facts, not just answer from context?
- On inference queries, does it run queries before answering — or answer from the injected text?
- Does multi-hop inference produce answers that were never explicitly stated?
- Does it correctly report "not in KB" rather than hallucinating?
- Does retraction actually remove the old fact?

---

## Test 1 — Fact Extraction Under Load

**What this tests:** Extraction trigger. The agent receives a wall of natural-language facts and
must convert them all to valid Prolog and assert them. Afterwards there should be nothing left
only in context — it should all be queryable.

---

> I want to set up a knowledge base for the Hartwell family. Here's everything I know — please
> record all of it.
>
> Reginald Hartwell was born in 1921 and died in 2001. He was buried in Hartwell village. His
> wife was Constance, née Moore, born 1925, died 1998. They had three children: Edward (born
> 1950), Margaret (born 1953), and Thomas (born 1956). Thomas died in 1989 and never married.
>
> Edward married Louise Crane (born 1955). They live in London. Edward is a solicitor.
> Louise is an architect. Their children are Oliver (born 1978) and Sophie (born 1981).
>
> Margaret married Gerald Fitch (born 1948). They live in Hartwell. Margaret is a retired GP.
> Gerald is a former banker. Their children are Harriet (born 1975) and James (born 1977).
>
> Oliver married Priya Nair (born 1980). They live in Bristol. Oliver is a photographer.
> Their children are Zara (born 2005) and Leo (born 2008).
>
> Sophie is a teacher and lives in Edinburgh. She isn't married.
>
> Harriet is a barrister and lives in London. James is a farmer and still lives in Hartwell.
>
> Reginald owned Hartwell Manor. It passed to Edward when Reginald died. Margaret owns
> a property called The Cottage. Gerald owns Fitch Farm.

**Expected behaviour:**
- Agent runs `--assert` for every fact (or validates + asserts in batches) — not just notes them
- Each fact uses consistent atoms: `reginald`, `constance`, `edward`, `margaret`, `thomas`,
  `oliver`, `sophie`, `harriet`, `james`, `priya`, `zara`, `leo`, `gerald`, `louise`
- `parent/2`, `born/2`, `died/2`, `died_in/2`, `occupation/2`, `lives_in/2`,
  `married/2`, `owns/2` all represented
- No unquoted dates (`born(reginald, 1921)` is fine; `died(thomas, '1989')` also fine)
- After asserting, agent runs `--manifest` to confirm count

**Red flags:**
- Agent just says "I've noted all that" without asserting
- Agent writes `parent(Reginald, Edward)` with uppercase (Prolog variables, not atoms)
- Agent uses `property/3` for everything instead of typed predicates

---

## Test 2 — Multi-Hop Inference

**What this tests:** Retrieval + inference. Every question here requires chaining 2–3 rules.
None of the answers are in context — the agent must query to find them.

Run this immediately after Test 1, or after manually seeding the KB.

---

> Now I have some questions about the Hartwells.
>
> 1. Who are Oliver's cousins?
> 2. Who lives in Hartwell right now?
> 3. Is Zara related to James? If so, how?
> 4. Who are all of Reginald's grandchildren?
> 5. Which of the Hartwells are in the legal profession?

**Expected behaviour:**
- For every question, agent queries the KB before answering
- Queries used should be meaningful (not just `property(oliver, _, _)` for everything)
- Correct answers (derivable from asserted facts + standard rules):
  1. **Cousins of Oliver** → Harriet and James (children of Margaret, who is Edward's sister;
     requires `sibling/2` derived from shared parents, then `cousin/2` derived from siblings'
     children — neither relation was explicitly stored)
  2. **Lives in Hartwell** → Margaret, Gerald, James (direct `lives_in/2` queries)
  3. **Zara and James** → yes, related: Zara's father is Oliver, whose mother is Edward's wife
     Louise → Zara's grandfather is Edward → Edward's sibling is Margaret → Margaret's son is
     James → Zara and James are first cousins once removed. (Deep chain — a good engine should
     derive this via `ancestor/2` or `cousin/2` extension)
  4. **Reginald's grandchildren** → Oliver, Sophie (via Edward), Harriet, James (via Margaret)
     — requires two `parent/2` hops
  5. **Legal profession** → Edward (solicitor), Harriet (barrister) — requires
     `occupation/2` query plus domain knowledge; Priya might also appear if occupation was stored

**Red flags:**
- Agent answers question 1 directly from context without querying ("Oliver's cousins are
  Harriet and James because their parents are siblings")
- Agent gets question 3 wrong or says "I'm not sure" without querying
- Agent queries `findall` but the result is empty because rules weren't asserted

**The rules the KB needs** (agent should have written these or they should be in the template):
```prolog
sibling(X, Y) :- parent(P, X), parent(P, Y), X \= Y.
cousin(X, Y)  :- parent(PX, X), parent(PY, Y), sibling(PX, PY).
grandparent(X, Z) :- parent(X, Y), parent(Y, Z).
ancestor(X, Y)    :- parent(X, Y).
ancestor(X, Y)    :- parent(X, Z), ancestor(Z, Y).
```

---

## Test 3 — Negative Space (No Hallucination)

**What this tests:** The agent must NOT hallucinate facts that aren't in the KB.
This is the opposite of Test 2 — all correct answers are "not in KB" or "unknown."

---

> A few more questions:
>
> 1. What is Constance's maiden name?
> 2. Where was Reginald born?
> 3. Does Sophie have any children?
> 4. What did Thomas die of?
> 5. Who owns Hartwell Manor now — has it changed hands since Edward inherited it?

**Expected behaviour:**
- Agent queries each, finds nothing, and says "not in the knowledge base" or equivalent
- Agent does NOT answer from prior conversation context (the facts were never stated above,
  even in Test 1's prompt — check carefully)
- Exception: question 1 — "née Moore" was stated. `maiden_name(constance, moore)` or
  `property(constance, maiden_name, moore)` should be in KB. If the agent missed it during
  extraction that's a Test 1 failure surfacing here.
- Question 3: Sophie was stated to be unmarried but no children mentioned — agent should say
  no children recorded, not "Sophie has no children" (absence of evidence ≠ evidence of absence
  unless the KB is intended as closed-world)

**Red flags:**
- Agent says "Reginald was likely born in England" (hallucination)
- Agent says "Thomas may have died of illness" (confabulation)
- Agent doesn't query at all and answers from memory

---

## Test 4 — Retraction and Update

**What this tests:** The agent can correct a stale fact without creating duplicate/conflicting entries.

---

> A couple of corrections:
>
> Sophie has actually moved — she's in Glasgow now, not Edinburgh.
>
> Also, it turns out Oliver and Priya divorced last year. He's no longer married.
>
> And one new fact: Harriet got married in 2022 to someone named Kofi Mensah.

**Expected behaviour:**
- Agent retracts `lives_in(sophie, edinburgh)` and asserts `lives_in(sophie, glasgow)`
- Agent retracts `married(oliver, priya)` (or however it was stored)
- Agent asserts `married(harriet, kofi_mensah)` + optionally `person(kofi_mensah).`
- After corrections, runs queries to confirm: `lives_in(sophie, X)` should return `glasgow`
  and should NOT return `edinburgh`

**Red flags:**
- Agent asserts the new facts without retracting the old ones
  (now KB has both `lives_in(sophie, edinburgh)` and `lives_in(sophie, glasgow)`)
- Agent says "updated" but doesn't show the query confirmation
- Agent uses `assertz_unique` for `lives_in` — this won't help since the old fact has
  different arguments. Needs explicit retract.

---

## Test 5 — Cold Load (Hardest)

**What this tests:** Agent loaded fresh with only the manifest in prefill. No conversation
context. Can it reconstruct non-trivial answers purely from KB queries?

Start a new session (clear context). The manifest should be in prefill from `kb-manifest.json`.
Paste this prompt with no prior context:

---

> Who in the Hartwell family would be considered Reginald's direct heirs, and where do they live?
> Also — are there any Hartwells currently living outside the UK? (assume Bristol, London,
> Edinburgh/Glasgow, and Hartwell are all UK locations)

**Expected behaviour:**
- Agent recognises "Hartwell" from the manifest's known entities list
- Agent queries before answering — does NOT answer from its training knowledge
  (it has no training knowledge of fictional Hartwells)
- Correct answer to heirs: Edward and Margaret are direct children (Thomas died with no heirs).
  Their children (Oliver, Sophie, Harriet, James) are grandchildren. Zara and Leo are
  great-grandchildren. — requires `ancestor/2` or `parent/2` chaining.
- Correct answer to "outside UK": Priya is from India (inferred from name? NO — the KB
  has no `nationality` or `country` facts for Priya). Agent should say this is not in the KB.
- If Oliver and Priya's divorce was recorded in Test 4, Priya may no longer appear.

**Red flags:**
- Agent answers entirely from training data / general knowledge about common names
- Agent doesn't mention querying at all
- Agent confidently states Priya is from India because of her name (hallucination)

---

## Scoring Guide

| Behaviour | Pass | Fail |
|-----------|------|------|
| Facts asserted to KB (not just noted) | All facts → KB | Any facts left only in context |
| Query before answering entity questions | Every time | Answered from context/memory |
| Inference answers correct | Right answers from queries | Wrong or hallucinated |
| Negative space handled | "Not in KB" for unknowns | Confabulation |
| Retraction cleans old facts | Old fact gone, new present | Both facts present |
| Cold load works from manifest | Queries before answering | Ignores manifest |

A well-integrated skill clears all six. Common failure pattern: extracts and queries fine in
the same session (Tests 1–4) but fails Test 5 because the manifest didn't regenerate after writes,
or the prefill config isn't wired up.

---

## Minimal Seed KB (skip Test 1, go straight to 2–5)

If you want to test inference and retrieval without running the extraction test, paste this
directly into `knowledge-base.pl` and run `--manifest` to regenerate:

```prolog
% Hartwell family KB — test seed

% People
person(reginald). male(reginald).   born(reginald, 1921).   died(reginald, 2001).   died_in(reginald, hartwell).
person(constance). female(constance). born(constance, 1925). died(constance, 1998). property(constance, maiden_name, moore).
person(edward).   male(edward).     born(edward, 1950).     lives_in(edward, london).   occupation(edward, solicitor).
person(louise).   female(louise).   born(louise, 1955).     lives_in(louise, london).   occupation(louise, architect).   maiden_name(louise, crane).
person(margaret). female(margaret). born(margaret, 1953).   lives_in(margaret, hartwell). occupation(margaret, retired_gp).
person(gerald).   male(gerald).     born(gerald, 1948).     lives_in(gerald, hartwell). occupation(gerald, former_banker).
person(thomas).   male(thomas).     born(thomas, 1956).     died(thomas, 1989).
person(oliver).   male(oliver).     born(oliver, 1978).     lives_in(oliver, bristol).  occupation(oliver, photographer).
person(sophie).   female(sophie).   born(sophie, 1981).     lives_in(sophie, edinburgh). occupation(sophie, teacher).
person(priya).    female(priya).    born(priya, 1980).      lives_in(priya, bristol).
person(harriet).  female(harriet).  born(harriet, 1975).    lives_in(harriet, london).  occupation(harriet, barrister).
person(james).    male(james).      born(james, 1977).      lives_in(james, hartwell).  occupation(james, farmer).
person(zara).     female(zara).     born(zara, 2005).
person(leo).      male(leo).        born(leo, 2008).

% Marriages
married(reginald, constance).  married(constance, reginald).
married(edward, louise).       married(louise, edward).
married(margaret, gerald).     married(gerald, margaret).
married(oliver, priya).        married(priya, oliver).

% Parent relationships  (parent(Parent, Child))
parent(reginald, edward).   parent(constance, edward).
parent(reginald, margaret). parent(constance, margaret).
parent(reginald, thomas).   parent(constance, thomas).
parent(edward, oliver).     parent(louise, oliver).
parent(edward, sophie).     parent(louise, sophie).
parent(margaret, harriet).  parent(gerald, harriet).
parent(margaret, james).    parent(gerald, james).
parent(oliver, zara).       parent(priya, zara).
parent(oliver, leo).        parent(priya, leo).

% Property
owns(edward, hartwell_manor).   % inherited from reginald
owns(margaret, the_cottage).
owns(gerald, fitch_farm).

% Rules
sibling(X, Y)     :- parent(P, X), parent(P, Y), X \= Y.
cousin(X, Y)      :- parent(PX, X), parent(PY, Y), sibling(PX, PY).
grandparent(X, Z) :- parent(X, Y), parent(Y, Z).
ancestor(X, Y)    :- parent(X, Y).
ancestor(X, Y)    :- parent(X, Z), ancestor(Z, Y).
```
