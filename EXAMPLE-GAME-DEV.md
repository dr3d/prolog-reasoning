# Example: Game Dev Session

A realistic scenario showing how the prolog-reasoning skill pays off when
building a Three.js game across multiple sessions.

The developer is building **Echoes of the Vault** — a first-person puzzle game.
Three areas, a handful of items, progression gates, and a growing pile of assets
in various states of completion.

---

## Session 1 — Designing the world (two weeks ago)

> **dev:** ok so the game has three areas — atrium, library, vault. atrium is
> where you start. library is accessible from atrium if you have the keycard.
> vault is only accessible from library and you need the lantern.
>
> **agent:** Got it. Extracting to KB.
> ```prolog
> area(atrium).
> area(library).
> area(vault).
>
> connected(atrium, library).
> connected(library, vault).
>
> gate(atrium, library, keycard).
> gate(library, vault,  lantern).
> ```
>
> **dev:** the keycard is on the desk in the atrium. lantern is in the library
> on the shelf — but it only appears after you solve the clock puzzle.
>
> **agent:**
> ```prolog
> item_location(keycard, atrium).
> item_location(lantern, library).
> requires_puzzle(lantern, clock_puzzle).
> ```
>
> **dev:** clock puzzle is in the library too. it unlocks when you have the gear
> item. gear is hidden in the atrium behind the painting.
>
> **agent:**
> ```prolog
> puzzle(clock_puzzle, library).
> puzzle_requires(clock_puzzle, gear).
> item_location(gear, atrium).
> item_hidden(gear, painting).
> ```
>
> **dev:** add a rule — player can enter an area if they have the required item,
> or if there's no gate
>
> **agent:**
> ```prolog
> can_enter(Area) :-
>     \+ gate(_, Area, _).
> can_enter(Area) :-
>     gate(_, Area, Item),
>     has(player, Item).
> ```

---

## Session 2 — Two weeks later, different context window

> **dev:** hey picking this back up. remind me — if the player finds the gear
> first thing, what's the earliest they can reach the vault?
>
> **agent:** Querying the KB.
> ```bash
> python3 prolog-executor.py "puzzle_requires(clock_puzzle, gear)."
> # {"success": true, "bindings": [{}]}
>
> python3 prolog-executor.py "requires_puzzle(lantern, P)."
> # {"success": true, "bindings": [{"P": "clock_puzzle"}]}
>
> python3 prolog-executor.py "gate(library, vault, I)."
> # {"success": true, "bindings": [{"I": "lantern"}]}
> ```
> Gear → solves clock puzzle → spawns lantern → unlocks vault gate. So the
> sequence is: pick up gear (atrium, behind painting) → solve clock puzzle
> (library) → get lantern → enter vault. They still need the keycard to get
> into the library first.
>
> **dev:** right. what's the keycard gate again — i forgot if it was atrium→library or library→vault
>
> **agent:** Querying.
> ```bash
> python3 prolog-executor.py "gate(From, To, keycard)."
> # {"success": true, "bindings": [{"From": "atrium", "To": "library"}]}
> ```
> atrium → library.
>
> **dev:** perfect. ok so i'm wiring up the asset loader. what assets do we
> have tracked so far?

---

## Session 3 — Asset tracking (next day)

> **dev:** ok i've got three.js models ready for the atrium furniture. the desk
> model is at assets/models/atrium/desk.glb. the painting is at
> assets/models/atrium/painting.glb. the gear is assets/models/items/gear.glb
>
> **agent:** Extracting.
> ```prolog
> asset(desk,     'assets/models/atrium/desk.glb',     complete).
> asset(painting, 'assets/models/atrium/painting.glb', complete).
> asset(gear,     'assets/models/items/gear.glb',      complete).
> ```
>
> **dev:** lantern model isn't done yet. i've got a placeholder cube at
> assets/models/items/lantern_placeholder.glb
>
> **agent:**
> ```prolog
> asset(lantern, 'assets/models/items/lantern_placeholder.glb', placeholder).
> ```
>
> **dev:** keycard is missing entirely, haven't modeled it
>
> **agent:**
> ```prolog
> asset(keycard, '', missing).
> ```

---

## Session 4 — Debugging a week later

> **dev:** something weird — gear is not appearing behind the painting. i think
> there might be a path issue. what's the gear asset path?
>
> **agent:** Querying.
> ```bash
> python3 prolog-executor.py "asset(gear, Path, Status)."
> # {"success": true, "bindings": [{"Path": "assets/models/items/gear.glb", "Status": "complete"}]}
> ```
> Path is `assets/models/items/gear.glb`, status complete. The asset exists —
> probably a scene placement issue rather than a missing file. Worth checking
> whether the painting object has the gear as a child or if it's being spawned
> on puzzle completion instead.
>
> **dev:** oh right — i hid it as a child of the painting mesh. the painting
> asset path, what is it
>
> **agent:**
> ```bash
> python3 prolog-executor.py "asset(painting, Path, _)."
> # {"success": true, "bindings": [{"Path": "assets/models/atrium/painting.glb"}]}
> ```
> `assets/models/atrium/painting.glb`
>
> **dev:** found it — i'd renamed the file to atrium_painting.glb on disk but
> never updated the KB. fix that.
>
> **agent:** Updating `knowledge-base.pl` — retracting old path, asserting correct one.
> ```prolog
> % was:
> asset(painting, 'assets/models/atrium/painting.glb', complete).
> % corrected:
> asset(painting, 'assets/models/atrium/atrium_painting.glb', complete).
> ```

---

## Session 5 — Pre-playtest check

> **dev:** we're doing a playtest tomorrow. what assets are still missing or
> placeholder?
>
> **agent:** Querying.
> ```bash
> python3 prolog-executor.py "findall(Name-Status, (asset(Name, _, Status), Status \= complete), L)."
> # {"success": true, "bindings": [{"L": "[lantern-placeholder, keycard-missing]"}]}
> ```
> Two gaps: lantern is placeholder, keycard is missing entirely. Everything else
> is complete.
>
> **dev:** ok keycard we can fake with a placeholder too. lantern placeholder
> is fine for now. can the player actually complete the game with current assets?
>
> **agent:** Let me reason through the progression gates against asset status.
> ```bash
> python3 prolog-executor.py "gate(_, _, Item), asset(Item, _, missing)."
> # {"success": false, "error": "No solutions found"}
> ```
> No gate item has a missing asset — keycard is now placeholder, lantern is
> placeholder. Both will load. The critical path is unblocked for the playtest.

---

## Why this works

The KB answers questions that LLM recall would get wrong or hedged. After two
weeks and multiple sessions, the agent knows exactly:

- `gate(atrium, library, keycard)` — not "I think the keycard was for the library?"
- `asset(painting, 'assets/models/atrium/atrium_painting.glb', complete)` — after the rename correction
- The full critical path derivable from a handful of facts

None of that is in the current context window. It's in the KB.

The game domain template (`python3 prolog-executor.py --init game`) gives you
the predicate structure — `connected/2`, `gate/3`, `item_location/2`, `has/2`,
`asset/3` — as a starting point.
