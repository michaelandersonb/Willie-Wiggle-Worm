"""Willie Wiggle Worm level-pack generator.
Static output is levels.ts in the repo (compiled to levels.js for the game).
Spec: 5x5 grid, clues {(r,c): number 1..25}.
Engine: backtracking solver with parity and distance pruning (tools/solver.py).
Counts are exact up to the requested limit: 0 impossible, 1 unique, 2+ ambiguous.
Unique tiers use fewest-clues subset search: every subset of k cells for
k = 1, 2, 3, ..., tested with limit=2, first (smallest k) unique set wins.
"""
import json, random, math, itertools
from solver import solve as board_solve

N = 5
random.seed(20261010)

# ---------- 1. solver-backed engine ----------
def neighbors(r, c):
    if r > 0: yield (r-1, c)
    if r < N-1: yield (r+1, c)
    if c > 0: yield (r, c-1)
    if c < N-1: yield (r, c+1)

def count_solutions(clues, limit):
    """clues: dict (r,c)->v. Returns up to `limit` solution boards."""
    grid = [[0] * N for _ in range(N)]
    for (r, c), v in clues.items():
        grid[r][c] = v
    return board_solve(grid, limit=limit)

def num_solutions(clues, limit):
    return len(count_solutions(clues, limit))

_answer_pool = None

def random_answer():
    """A random full solution board, drawn from a cached pool."""
    global _answer_pool
    if _answer_pool is None:
        _answer_pool = board_solve([[0] * N for _ in range(N)], limit=300)
        assert _answer_pool, "empty grid must be solvable"
    return random.choice(_answer_pool)

def full_clues(board):
    return {(r, c): board[r][c] for r in range(N) for c in range(N)}

def parity_ok(clues):
    bad = []
    for (r, c), v in clues.items():
        # odd numbers must sit on (r+c) even
        if ((r+c) % 2 == 0) != (v % 2 == 1):
            bad.append(((r, c), v))
    return bad

def distance_violations(clues):
    items = list(clues.items())
    bad = []
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            (r1, c1), a = items[i]
            (r2, c2), b = items[j]
            if a == b:
                continue
            lo, hi = (a, b) if a < b else (b, a)
            d = abs(r1-r2) + abs(c1-c2)
            if d > (hi-lo) or ((hi-lo-d) % 2 == 1):
                bad.append((((r1, c1), a), ((r2, c2), b), d))
    return bad

def explain(clues):
    if parity_ok(clues):
        return "parity"
    if distance_violations(clues):
        return "distance"
    return "dead_end"

def naive_node_count(clues, cap=200000):
    """DFS in number order with clue pruning; returns visit count proxy."""
    by_val = {}
    for cell, v in clues.items():
        by_val[v] = cell
    count = [0]
    adj = {}
    for r in range(N):
        for c in range(N):
            adj[(r, c)] = list(neighbors(r, c))
    if 1 in by_val:
        starts = [by_val[1]]
    else:
        starts = [(r, c) for r in range(N) for c in range(N)]
    def rec(step, cell, vis):
        count[0] += 1
        if count[0] > cap:
            return True
        if step == N*N:
            return False
        nxt_val = step + 1
        if nxt_val in by_val:
            t = by_val[nxt_val]
            if t in adj[cell] and t not in vis:
                if rec(step+1, t, vis | {t}):
                    return True
            return False
        for nb in adj[cell]:
            if nb not in vis:
                if nb in clues and clues[nb] != nxt_val:
                    continue
                if rec(step+1, nb, vis | {nb}):
                    return True
                if count[0] > cap:
                    return True
        return False
    for s in starts:
        if s in clues and clues[s] != 1:
            continue
        if rec(1, s, {s}):
            break
    return count[0]

def tightness(clues):
    items = list(clues.values())
    cells = list(clues.keys())
    if len(items) < 2:
        return 0.0
    best = 0.0
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            a, b = items[i], items[j]
            lo, hi = (a, b) if a < b else (b, a)
            d = abs(cells[i][0]-cells[j][0]) + abs(cells[i][1]-cells[j][1])
            t = d / (hi - lo)
            if t > best:
                best = t
    return round(best, 3)

def difficulty(nclues, solcount, has1, has25, nodes, tight):
    s = 0.0
    s += (8 - nclues) * 8
    s += 0 if has1 else 25
    s += 0 if has25 else 8
    s += math.log10(nodes + 1) * 12
    s += tight * 25
    if solcount == 1:
        s += 40
    elif solcount > 1:
        s -= math.log10(solcount) * 18
    return round(s, 1)

def transforms(r, c):
    return [
        (r, c), (c, 4-r), (4-r, 4-c), (4-c, r),
        (r, 4-c), (4-r, c), (c, r), (4-c, 4-r),
    ]

def canonical(clues):
    variants = []
    for k in range(8):
        t = tuple(sorted(((transforms(r, c)[k], v) for (r, c), v in clues.items())))
        variants.append(t)
    return min(variants)

SUBSET_CAP = 60000


def fewest_subset(board, k_min, k_max, must_include=frozenset(), allowed=None,
                  cap=SUBSET_CAP, collect=1):
    """Fewest clues by brute force: every subset of k cells, k ascending.

    board: full solution. must_include: cells always revealed. allowed:
    candidate cells (default all 25). Each subset is tested with limit=2.
    Returns up to `collect` clue dicts at the smallest k with exactly one
    solution.
    """
    full = full_clues(board)
    cells = [cell for cell in full if allowed is None or cell in allowed]
    random.shuffle(cells)
    rest = [cell for cell in cells if cell not in must_include]
    base = {cell: full[cell] for cell in must_include}
    found = []
    calls = 0
    for k in range(max(k_min, len(base)), k_max + 1):
        for combo in itertools.combinations(rest, k - len(base)):
            if calls >= cap:
                return found
            clues = dict(base)
            for cell in combo:
                clues[cell] = full[cell]
            calls += 1
            if num_solutions(clues, 2) == 1:
                found.append(clues)
                if len(found) >= collect:
                    return found
        if found:
            return found
    return found


def pad_clues(board, clues, target):
    """Add true cells up to `target` clues (uniqueness is preserved)."""
    full = full_clues(board)
    rest = [cell for cell in full if cell not in clues]
    random.shuffle(rest)
    clues = dict(clues)
    for cell in rest:
        if len(clues) >= target:
            break
        clues[cell] = full[cell]
    return clues


def one_cell(board, value):
    for r in range(N):
        for c in range(N):
            if board[r][c] == value:
                return (r, c)
    raise AssertionError(value)

def random_clue_set(nclues, vals=None):
    cells = random.sample([(r, c) for r in range(N) for c in range(N)], nclues)
    if vals is None:
        vals = random.sample(range(1, 26), nclues)
    return {cell: v for cell, v in zip(cells, vals)}

levels = []
seen = set()

def add_level(clues, tier, label, note=""):
    global levels
    key = canonical(clues)
    if key in seen:
        return None
    sols = count_solutions(clues, 501)
    if label == "solvable":
        assert len(sols) >= 1, f"solvable tier {tier} has 0 solutions: {clues}"
        if tier in ("dense_unique", "sparse_unique", "hidden_start", "hard") and label == "solvable":
            assert len(sols) == 1, f"{tier} must be unique, got {len(sols)}"
    else:
        assert len(sols) == 0, f"impossible tier {tier} has {len(sols)} solutions"
    seen.add(key)
    has1 = 1 in clues.values()
    has25 = 25 in clues.values()
    nodes = naive_node_count(clues)
    tight = tightness(clues)
    diff = difficulty(len(clues), len(sols), has1, has25, nodes, tight)
    rule = None if label == "solvable" else explain(clues)
    grid = []
    for r in range(5):
        row = []
        for c in range(5):
            row.append(str(clues[(r, c)]) if (r, c) in clues else ".")
        grid.append(" ".join(row))
    lv = {
        "tier": tier,
        "label": label,
        "clues": [{"row": r, "col": c, "number": v} for (r, c), v in sorted(clues.items(), key=lambda kv: kv[1])],
        "grid": grid,
        "numClues": len(clues),
        "hasOne": has1,
        "hasTwentyFive": has25,
        "nodeCount": nodes,
        "tightness": tight,
        "difficulty": diff,
        "rule": rule,
        "note": note,
    }
    levels.append(lv)
    return lv

add_level({}, "open_play", "solvable", note="Empty grid: teaches the mechanic.")
add_level({(2, 2): 1}, "open_play", "solvable", note="Single 1 in the center.")

anch = 0
tries = 0
while anch < 3 and tries < 400:
    tries += 1
    board = random_answer()
    clues = {one_cell(board, 1): 1, one_cell(board, 25): 25}
    n = num_solutions(clues, 501)
    if 30 <= n <= 500:
        if add_level(clues, "anchored_ends", "solvable", note="1 and 25 given; constrained at both ends."):
            anch += 1

dense = 0
tries = 0
while dense < 3 and tries < 25:
    tries += 1
    board = random_answer()
    must = frozenset([one_cell(board, 1)])
    hits = fewest_subset(board, 2, 4, must_include=must)
    if not hits:
        continue
    clues = pad_clues(board, hits[0], random.choice([5, 6]))
    if 5 <= len(clues) <= 6 and num_solutions(clues, 2) == 1:
        if add_level(clues, "dense_unique", "solvable", note="Dense but unique; deduction-heavy."):
            dense += 1

sparse = 0
tries = 0
while sparse < 3 and tries < 40:
    tries += 1
    board = random_answer()
    must = frozenset([one_cell(board, 1)])
    hits = fewest_subset(board, 2, 4, must_include=must)
    if not hits:
        continue
    clues = hits[0] if len(hits[0]) >= 3 else pad_clues(board, hits[0], 3)
    if 3 <= len(clues) <= 4 and num_solutions(clues, 2) == 1:
        if add_level(clues, "sparse_unique", "solvable", note="Sparse and unique."):
            sparse += 1

hidden = 0
tries = 0
while hidden < 2 and tries < 25:
    tries += 1
    board = random_answer()
    allowed = {(r, c) for r in range(N) for c in range(N) if 4 <= board[r][c] <= 22}
    hits = fewest_subset(board, 3, 5, allowed=allowed)
    if not hits:
        continue
    clues = hits[0]
    if 3 <= len(clues) <= 5 and num_solutions(clues, 2) == 1:
        if add_level(clues, "hidden_start", "solvable", note="Unique, no 1 given; mid-sequence clues only."):
            hidden += 1

def make_spot_solvable():
    for _ in range(200):
        clues = random_clue_set(3)
        if distance_violations(clues):
            continue
        n = num_solutions(clues, 401)
        if 1 <= n <= 400:
            return clues
    return {(0, 0): 1, (0, 4): 5, (4, 0): 9}

def make_parity_trap():
    for _ in range(500):
        base = make_spot_solvable()
        cells = list(base.keys())
        cell = random.choice(cells)
        v = base[cell]
        empt = [(r, c) for r in range(N) for c in range(N) if (r, c) not in base]
        random.shuffle(empt)
        for nc in empt:
            if (((nc[0]+nc[1]) % 2 == 0) != (v % 2 == 1)):
                trial = dict(base); del trial[cell]; trial[nc] = v
                if parity_ok(trial) and num_solutions(trial, 1) == 0:
                    return trial
    return {(0, 0): 2, (2, 2): 10}

def make_distance_trap():
    return {(0, 0): 3, (4, 4): 9}

for g in (1, 2):
    rule = "parity" if g == 1 else "distance"
    trap = make_parity_trap() if g == 1 else make_distance_trap()
    group = []
    while len(group) < 3:
        c = make_spot_solvable()
        k = canonical(c)
        if k in seen or any(canonical(x) == k for x in group):
            continue
        group.append(c)
    # sort the 3 solvables by difficulty proxy (solution count desc = easier first),
    # then insert the trap at a random position so each group of four holds
    # exactly one impossible grid but is still roughly easy-first.
    group = sorted(group, key=lambda c: -min(num_solutions(c, 401), 401))
    pos = random.randrange(4)
    group.insert(pos, trap)
    for c in group:
        lab = "impossible" if c is trap else "solvable"
        lv = add_level(c, "spot_impossible", lab, note=f"Spot-the-impossible group {g} ({rule} trap; exactly one impossible in four).")
        if lv is not None:
            lv["group"] = g

hard_imp = 0
tries = 0
while hard_imp < 2 and tries < 6000:
    tries += 1
    clues = random_clue_set(random.choice([4, 5, 6]))
    if parity_ok(clues):
        continue
    if distance_violations(clues):
        continue
    if num_solutions(clues, 1) == 0:
        if add_level(clues, "hard", "impossible", note="Hidden dead end; passes local checks, only search confirms."):
            hard_imp += 1

added = 0
tries = 0
while added < 2 and tries < 60:
    tries += 1
    board = random_answer()
    cands = fewest_subset(board, 2, 4, collect=12)
    cands.sort(key=naive_node_count, reverse=True)
    for clues in cands:
        if 2 <= len(clues) <= 4 and num_solutions(clues, 2) == 1:
            if add_level(dict(clues), "hard", "solvable", note="Highest-scoring unique level."):
                added += 1
                break

tier_order = ["open_play", "anchored_ends", "dense_unique", "sparse_unique", "hidden_start", "spot_impossible", "hard"]
ordered = []
for t in tier_order:
    group = [lv for lv in levels if lv["tier"] == t]
    if t == "open_play":
        # Easiest first: empty grid before single-1 (difficulty formula is
        # tuned for unique levels, where fewer clues = harder, so override).
        group.sort(key=lambda lv: lv["numClues"])
    elif t == "spot_impossible":
        # Keep each group of four contiguous (exactly one impossible each);
        # generation order already places trap at a random position.
        group.sort(key=lambda lv: lv.get("group", 0))
    else:
        group.sort(key=lambda lv: lv["difficulty"])
    ordered.extend(group)

for i, lv in enumerate(ordered, start=1):
    lv["id"] = i

ids = [lv["id"] for lv in ordered]
assert len(ids) == len(set(ids))
keys = [canonical({(c["row"], c["col"]): c["number"] for c in lv["clues"]}) for lv in ordered]
assert len(keys) == len(set(keys)), "duplicate clue set under symmetry"
for lv in ordered:
    nums = [c["number"] for c in lv["clues"]]
    assert all(1 <= v <= 25 for v in nums), "clue number out of range"
    assert len(nums) == len(set(nums)), "duplicated clue numbers"
    cells = [(c["row"], c["col"]) for c in lv["clues"]]
    assert len(cells) == len(set(cells)), "two clues on one cell"
    assert all(0 <= r < 5 and 0 <= c < 5 for r, c in cells)
    clues = {(c["row"], c["col"]): c["number"] for c in lv["clues"]}
    n = num_solutions(clues, 501)
    if lv["label"] == "solvable":
        assert n >= 1
        if lv["tier"] in ("dense_unique", "sparse_unique", "hidden_start", "hard"):
            assert n == 1
    else:
        assert n == 0
        assert lv["rule"] in ("parity", "distance", "dead_end")
        if lv["rule"] == "parity":
            assert parity_ok(clues), f'id {lv["id"]} claims parity but passes'
        elif lv["rule"] == "distance":
            assert not parity_ok(clues) and distance_violations(clues), f'id {lv["id"]} claims distance'
        else:
            assert not parity_ok(clues) and not distance_violations(clues)

print(f"levels: {len(ordered)}")
for lv in ordered:
    clues = {(c["row"], c["col"]): c["number"] for c in lv["clues"]}
    print(lv["id"], lv["tier"], lv["label"], lv["numClues"], num_solutions(clues, 501), lv["difficulty"], lv["rule"])

# Shipped pack: human-readable, no answer keys and no solution counts.
# Solvability is re-checked by solving, not by trusting stored numbers.
# Single source of truth is levels.ts (compiled to levels.js for the game).

# Also emit the pack as a `const levels` TypeScript file so the game can
# include it as a plain script (no fetch).
def ts_str(s):
    return json.dumps(s)

lines = []
lines.append("// Generated by tools/generate_levels.py. Do not edit by hand.")
lines.append("// Static Willie Wiggle Worm level pack (5x5). Play order is array order.")
lines.append("type Clue = {")
lines.append("  row: number;")
lines.append("  col: number;")
lines.append("  number: number;")
lines.append("};")
lines.append("")
lines.append("type Level = {")
lines.append("  id: number;")
lines.append("  tier: string;")
lines.append('  label: "solvable" | "impossible";')
lines.append("  // Cell index (row * 5 + col) of the pre-filled 1 tile, or -1 for free start.")
lines.append("  startPosition: number;")
lines.append("  requirements: {")
lines.append("    clues: Clue[];")
lines.append("  };")
lines.append("  rule: string | null; // parity | distance | dead_end, impossible levels only")
lines.append("  note: string;")
lines.append("};")
lines.append("")
lines.append("const levels: Level[] = [")
for lv in ordered:
    clues = {(c["row"], c["col"]): c["number"] for c in lv["clues"]}
    start = next((r * 5 + c for (r, c), v in clues.items() if v == 1), -1)
    if start >= 0:
        assert clues[(start // 5, start % 5)] == 1
    lines.append("  {")
    lines.append(f'    id: {lv["id"]},')
    lines.append(f'    tier: {ts_str(lv["tier"])},')
    lines.append(f'    label: {ts_str(lv["label"])},')
    lines.append(f'    startPosition: {start},')
    lines.append("    requirements: {")
    clue_ts = ", ".join(
        "{ row: %d, col: %d, number: %d }" % (c["row"], c["col"], c["number"])
        for c in lv["clues"]
    )
    lines.append(f'      clues: [{clue_ts}],')
    lines.append("    },")
    lines.append(f'    rule: {ts_str(lv["rule"])},')
    lines.append(f'    note: {ts_str(lv["note"])},')
    lines.append("  },")
lines.append("];")
with open("levels.ts", "w") as f:
    f.write("\n".join(lines) + "\n")
print("wrote levels.ts")
