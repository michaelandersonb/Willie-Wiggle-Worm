"""End-to-end click-through test for Willie Wiggle Worm (headless Chromium).

No stored answers: the test solves each level with tools/solver.py
(backtracking with parity and distance pruning) and plays the found path:
- open_play ladder (empty grid + single 1), tier chains into next, menu hook
- anchored_ends clue level completed via solved path (clue verification path)
- declare-impossible scolded on a solvable level
- spot_impossible group: solvable via solved path, impossible via declaration
- clue mismatch (reversed path) fills grid but does NOT advance
- wrong first move flags the failed clue live (badge + Reset warning)
- every level re-solved live: unique tiers == 1, anchored band 30-500,
  impossible tiers == 0

Run:  python3 tools/test_levels.py   (needs the python host on :8000)
"""
import json
import subprocess
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:8000"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from solver import solve_level, click_order, grid_from_clues  # noqa: E402


def load_levels():
    """Single source of truth is levels.ts; read it via the compiled levels.js."""
    src = (ROOT / "levels.js").read_text()
    out = subprocess.run(["node", "-e", src + "\n;console.log(JSON.stringify(levels))"],
                         capture_output=True, text=True, check=True)
    return {lv["id"]: lv for lv in json.loads(out.stdout)}


levels = load_levels()

def clues_of(lv):
    return lv["requirements"]["clues"]


def idx(r, c):
    return r * 5 + c


def play_path(pg, path):
    for (r, c) in path:
        pg.click(f'[elementNumber="{idx(r, c)}"]')


def play_solution(pg, board):
    play_path(pg, click_order(board))


# ---------- live solvability check (nothing trusted from the files) ----------
# limit=2 classifies: 0 impossible, 1 unique, 2 ambiguous. Anchored levels
# need their full count for the 30-500 band, so they get limit=501.
print("solving all levels...", flush=True)
t0 = time.perf_counter()
solved = {}
for lid, lv in levels.items():
    lim = 501 if lv["tier"] == "anchored_ends" else 2
    solved[lid] = solve_level(lv, limit=lim)
dt = time.perf_counter() - t0
for lid, lv in levels.items():
    n = len(solved[lid])
    if lv["label"] == "solvable":
        assert n >= 1, f"level {lid} unsolvable"
        if lv["tier"] in ("dense_unique", "sparse_unique", "hidden_start", "hard") and lv["label"] == "solvable":
            assert n == 1, f"level {lid} tier {lv['tier']} has {n} solutions"
        if lv["tier"] == "anchored_ends":
            assert 30 <= n <= 500, f"level {lid} anchored count {n} outside 30-500"
    else:
        assert n == 0, f"level {lid} labelled impossible has {n} solutions"
print(f"solvability OK ({dt:.2f}s for 25 levels)", flush=True)

errors = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    pg = browser.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(BASE + "/index.html")
    pg.wait_for_selector(".tier-button", timeout=10000)
    assert pg.locator(".tier-button").count() == 7, "expected 7 tier buttons"

    # ---- open_play ladder ----
    pg.click("text=Open Play")
    pg.click("#play-button")
    pg.wait_for_selector("#game-screen:visible")
    assert pg.locator("#impossible-button:disabled").count() == 1
    assert "(" in pg.inner_text("#impossible-button")
    dims = pg.evaluate("({sw:document.documentElement.scrollWidth, iw:window.innerWidth, sh:document.documentElement.scrollHeight, ih:window.innerHeight})")
    assert dims["sw"] <= dims["iw"] and dims["sh"] <= dims["ih"], f"page scrolls: {dims}"
    assert "Open Play" in pg.inner_text("#level-title")
    assert "#1" in pg.inner_text("#level-title")
    assert pg.inner_text("#step-counter") == "Steps: 0/25"
    assert pg.locator(".clue-badge").count() == 0
    full1 = click_order(solved[1][0])
    play_path(pg, full1[:4])
    assert pg.inner_text("#step-counter") == "Steps: 4/25"
    pg.click("#undo-button")
    pg.click("#undo-button")
    assert pg.inner_text("#step-counter") == "Steps: 2/25"
    assert pg.evaluate("window.__ww.snapshot()")["filled"] == 2
    play_path(pg, full1[2:4])
    assert pg.inner_text("#step-counter") == "Steps: 4/25"
    play_path(pg, full1[4:])
    pg.wait_for_selector("#level-completed-screen:visible")
    assert pg.inner_text("#step-counter") == "Steps: 25/25"
    pg.click("#next-level-button")
    assert "#2" in pg.inner_text("#level-title")
    assert pg.locator(".clue-badge").count() == 1
    assert pg.inner_text("#step-counter") == "Steps: 1/25"
    pg.click("#undo-button")  # fixed start: undo stops at the given 1
    assert pg.inner_text("#step-counter") == "Steps: 1/25"
    play_solution(pg, solved[2][0])
    # level 2 ends the tier -> chained straight into anchored_ends, no menu
    pg.wait_for_selector("#level-completed-screen:visible")
    assert "Next up: Anchored Ends" in pg.inner_text("#level-completed-title"), \
        pg.inner_text("#level-completed-title")
    assert "Â" not in pg.inner_text("#level-title"), "charset mojibake in title"
    pg.click("#next-level-button")
    pg.wait_for_selector("#game-screen:visible")
    assert "Anchored Ends" in pg.inner_text("#level-title")
    assert "#3" in pg.inner_text("#level-title")

    # ---- menu button quits back to the tier menu mid-tier ----
    pg.click("#menu-button")
    pg.wait_for_selector("#start-screen:visible")
    assert pg.locator(".tier-button").count() == 7

    # ---- anchored_ends clue level via solved path ----
    pg.evaluate("window.__ww.startTier('anchored_ends')")
    pg.wait_for_selector("#game-screen:visible")
    assert pg.locator(".clue-badge").count() == len(clues_of(levels[3])) == 2
    play_solution(pg, solved[3][0])
    pg.wait_for_selector("#level-completed-screen:visible")
    assert "Level Completed!" in pg.inner_text("#level-completed-title")
    pg.click("#next-level-button")  # back to game for next checks

    # ---- declare-impossible on a solvable level: scolded, stays ----
    pg.evaluate("window.__ww.startTier('dense_unique')")
    pg.evaluate("document.getElementById('impossible-button').click()")  # locked: no-op
    assert pg.inner_text("#message") == ""
    assert pg.locator("#game-screen").is_visible()
    pg.evaluate("window.__ww.allowImpossible()")
    assert pg.inner_text("#impossible-button") == "Declare Impossible"
    pg.click("#impossible-button")
    assert "Nope" in pg.inner_text("#message")
    assert pg.locator("#game-screen").is_visible()

    # ---- spot group 1: id14 solvable, id15 impossible ----
    pg.evaluate("window.__ww.startTier('spot_impossible')")
    assert "#14" in pg.inner_text("#level-title"), pg.inner_text("#level-title")
    assert levels[15]["label"] == "impossible" and len(solved[15]) == 0
    assert len(solved[14]) >= 1
    play_solution(pg, solved[14][0])
    pg.wait_for_selector("#level-completed-screen:visible")
    pg.click("#next-level-button")
    assert "#15" in pg.inner_text("#level-title")
    pg.evaluate("window.__ww.allowImpossible()")
    pg.click("#impossible-button")
    pg.wait_for_selector("#level-completed-screen:visible")
    assert "impossible" in pg.inner_text("#level-completed-title").lower()

    # ---- mismatch: reversed path fills grid but must NOT advance ----
    lv12 = levels[12]
    assert lv12["tier"] == "hidden_start" and lv12["label"] == "solvable"
    assert len(solved[12]) == 1
    assert not all(c["number"] == 13 for c in clues_of(lv12)), "reversed path would pass"
    pg.evaluate("window.__ww.startTier('hidden_start')")
    assert "#12" in pg.inner_text("#level-title"), pg.inner_text("#level-title")
    for (r, c) in reversed(click_order(solved[12][0])):
        pg.click(f'[elementNumber="{idx(r, c)}"]')
    assert pg.locator("#game-screen").is_visible()
    assert pg.locator("#level-completed-screen").is_hidden()
    assert "wrong step" in pg.inner_text("#message"), pg.inner_text("#message")

    # ---- live invalid-state: deviating flags failure before the grid fills ----
    def game_bad(clues, steps, head, current):
        """Mirror of badClues() in main.ts."""
        bad = []
        for cell, k in clues.items():
            s = steps.get(cell, 0)
            if s:
                if s != k:
                    bad.append(k)
                continue
            if k <= current:
                bad.append(k)
                continue
            d = abs(head[0] - cell[0]) + abs(head[1] - cell[1])
            if d > k - current or (k - current - d) % 2:
                bad.append(k)
        return bad

    def adj(cell):
        r, c = cell
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < 5 and 0 <= nc < 5:
                yield (nr, nc)

    def deviation_run(lv):
        """Wrong first move + greedy walk. Returns (seq, reason) where the
        game must flag failure live, or None if the walk fills the grid."""
        clues = {(c["row"], c["col"]): c["number"] for c in clues_of(lv)}
        if lv["startPosition"] < 0:
            return None
        P = (lv["startPosition"] // 5, lv["startPosition"] % 5)
        board = solved[lv["id"]][0]
        S = next((r, c) for r in range(5) for c in range(5) if board[r][c] == 2)
        W = next((nb for nb in adj(P) if nb != S))
        steps = {P: 1, W: 2}
        filled = {P, W}
        head, cur, seq = W, 2, [W]
        while len(filled) < 25:
            if game_bad(clues, steps, head, cur):
                return seq, "clue"
            opts = [nb for nb in adj(head) if nb not in filled]
            if not opts:
                return seq, "stuck"
            head = opts[0]
            cur += 1
            steps[head] = cur
            filled.add(head)
            seq.append(head)
        return None

    pick = None
    for lid in (6, 9, 3, 12, 7, 10):
        run = deviation_run(levels[lid])
        if run:
            pick = (lid,) + run
            break
    assert pick, "no level flags a deviating run live"
    lid, seq, reason = pick
    pg.evaluate(f"window.__ww.startTier('{levels[lid]['tier']}')")
    assert f"#{lid}" in pg.inner_text("#level-title"), pg.inner_text("#level-title")
    for (r, c) in seq:
        pg.click(f'[elementNumber="{idx(r, c)}"]')
    assert pg.evaluate("window.__ww.snapshot()")["filled"] < 25
    msg = pg.inner_text("#message")
    assert "Reset" in msg and "wrong step" not in msg, msg
    if reason == "clue":
        assert pg.locator(".clue-badge.clue-bad").count() >= 1
    else:
        assert "no moves" in msg, msg
    assert pg.locator("#game-screen").is_visible()
    assert pg.locator("#level-completed-screen").is_hidden()

    browser.close()

print("pageerrors:", errors)
assert not errors, errors
print("ALL TESTS PASSED")
