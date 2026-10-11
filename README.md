# Willie Wiggle Wiggle Worm Game

Willie Wiggle Wiggle Worm is a spatial reasoning and counting game. Guide Willie
through every square of a 5×5 grid — each numbered clue must land on that exact
step of the path. Some levels are impossible; spot them and declare it.

https://mathpickle.com/project/willie-wiggle-wiggle-worm/

## How to Play

1. Pick a level type on the menu, then press Play.
2. Click squares adjacent to Willie to extend him. The `1` tile (if shown) is
   your fixed start; otherwise your first click anywhere starts the worm.
3. Numbered badges are clues: the cell must be stepped on at that exact number.
   A clue that becomes unreachable turns red with a Reset hint.
4. Stuck? Use **Undo Move** to step back or **Reset Level** to restart.
5. Think a level can't be done? **Declare Impossible** unlocks 60 seconds into
   each level — correct calls advance you, wrong ones don't.
6. Finishing a tier rolls straight into the next one. **Menu** quits back to
   the level-type picker at any time.

## Levels (`levels.ts`)

25 static levels in a `const levels` pack (`Level`: `id`, `tier`, `label`,
`startPosition`, `requirements.clues`, difficulty data, explanation `rule`).
Play order is array order, grouped into 7 tiers:

| Tier | Levels |
|---|---|
| Open Play | Empty grid, then a single `1` — teaches the mechanic |
| Anchored Ends | `1` and `25` given, many solutions |
| Dense & Unique | 5–6 clues incl. a `1`, exactly one solution |
| Sparse & Unique | 3–4 clues incl. a `1`, exactly one solution |
| Hidden Start | Unique, no `1`/`25`, mid-sequence clues only |
| Spot the Impossible | Groups of four with exactly one impossible grid |
| Hard | Hardest unique levels mixed with hidden dead ends |

Impossible levels carry a `rule` (`parity`, `distance`, `dead_end`) explaining
why no path can fit the clues.

## Assets

Worm graphics (PNG, loaded over HTTP, no file paths):

| File | Used for |
|---|---|
| `single tile worm.png` | Starting single segment (becomes the tail on the first move) |
| `head02.png` | Head, rotated to face the direction of travel |
| `worm-end02.png` | Tail, rotated along the direction of travel |
| `tube-segment.png` | Straight body segments (rotated for vertical runs) |
| `corner-segment.png` | Corner body segments |

Number sounds live in `sounds/` (`1.mp3`–`25.mp3`). The `1` sound plays only
when a `1` actually lands on the board.

## Development

This game is HTML, CSS, and TypeScript. Serve it over HTTP (it does not
support `file://`):

```sh
python3 -m http.server 8000
# play at http://localhost:8000/index.html
```

Rebuild the compiled JS after editing TypeScript:

```sh
tsc          # uses tsconfig.json -> main.js, levels.js (+ sourcemaps)
```

`tools/` holds the level pipeline (all Python 3):

| File | Purpose |
|---|---|
| `tools/solver.py` | Backtracking solver with parity and distance pruning. `solve(grid, limit=2)` returns up to `limit` solutions: 0 = impossible, 1 = unique, 2+ = ambiguous |
| `tools/generate_levels.py` | Regenerates `levels.ts` from random solutions: solver-backed counts, fewest-clues subset search for unique tiers, parity/distance/dead-end traps, difficulty scoring, symmetry dedupe, full validation |
| `tools/test_levels.py` | Solves every level from `levels.js` with the solver, then click-through-tests the game in headless Chromium (needs the HTTP host on :8000) |

```sh
python3 tools/generate_levels.py   # rewrite levels.ts
python3 tools/test_levels.py       # verify the game end to end
```

## Credits

- The intro worm graphic was generated using Image Creator from Microsoft Bing
- The worm glyphs were scrapped from mathpickle
- The number sounds were downloaded from https://ttsmp3.com/
