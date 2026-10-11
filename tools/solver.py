"""Backtracking solver with parity and distance pruning.

Quick impossibility checks on the givens, before any search. For two givens
a < b at Manhattan distance d, you need d <= b-a and (b-a-d) even. A path
alternates checkerboard colors, so the distance and the number gap must have
the same parity. Duplicate or out-of-range givens also fail here.

Place numbers in order (1, 2, 3, ...), extending the path one step at a time.
Prune every step. Count solutions up to `limit`: 0 = impossible, 1 = unique,
limit reached = ambiguous.
"""


def solve(grid, limit=2):
    """grid: NxN list of lists, 0 = blank. Returns up to `limit` solutions."""
    N = len(grid)
    T = N * N
    given = {}
    for r in range(N):
        for c in range(N):
            v = grid[r][c]
            if v:
                if v in given or not 1 <= v <= T:
                    return []
                given[v] = (r, c)

    keys = sorted(given)
    for a, b in zip(keys, keys[1:]):
        d = abs(given[a][0] - given[b][0]) + abs(given[a][1] - given[b][1])
        if d > b - a or (b - a - d) % 2:
            return []

    pinned = set(given.values())

    # nxt_given[k] = smallest given number > k, or None
    nxt_given, nxt = [None] * (T + 2), None
    for k in range(T, -1, -1):
        nxt_given[k] = nxt
        if k in given:
            nxt = k

    def feasible(k, r, c):
        if k in given:
            if (r, c) != given[k]:
                return False
        elif (r, c) in pinned:
            return False
        m = nxt_given[k]
        if m is not None:
            d = abs(r - given[m][0]) + abs(c - given[m][1])
            if d > m - k or (m - k - d) % 2:
                return False
        return True

    board = [[0] * N for _ in range(N)]
    sols = []

    def dfs(k, r, c):
        board[r][c] = k
        if k == T:
            sols.append([row[:] for row in board])
        else:
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < N and 0 <= nc < N and not board[nr][nc] \
                        and feasible(k + 1, nr, nc):
                    dfs(k + 1, nr, nc)
                    if len(sols) >= limit:
                        break
        board[r][c] = 0

    for r in range(N):
        for c in range(N):
            if feasible(1, r, c):
                dfs(1, r, c)
                if len(sols) >= limit:
                    return sols
    return sols


# ---- thin adapters for the repo's level format ----

def grid_from_clues(clues, n=5):
    """clues: iterable of {row, col, number} (or (row, col, number) tuples)."""
    grid = [[0] * n for _ in range(n)]
    for cl in clues:
        if isinstance(cl, dict):
            r, c, v = cl["row"], cl["col"], cl["number"]
        else:
            r, c, v = cl
        grid[r][c] = v
    return grid


def solve_level(level, limit=2):
    """level: dict with requirements.clues. Returns up to `limit` solution boards."""
    return solve(grid_from_clues(level["requirements"]["clues"]), limit)


def click_order(board):
    """Solution board -> [(row, col)] holding numbers 1..25, for playthroughs."""
    n = len(board)
    pos = {}
    for r in range(n):
        for c in range(n):
            pos[board[r][c]] = (r, c)
    return [pos[k] for k in range(1, n * n + 1)]
