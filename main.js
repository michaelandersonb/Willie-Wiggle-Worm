"use strict";
/// <reference path="levels.ts" />
const TIER_NAMES = {
    open_play: "Open Play",
    anchored_ends: "Anchored Ends",
    dense_unique: "Dense & Unique",
    sparse_unique: "Sparse & Unique",
    hidden_start: "Hidden Start",
    spot_impossible: "Spot the Impossible",
    hard: "Hard",
};
const TIER_ORDER = [
    "open_play",
    "anchored_ends",
    "dense_unique",
    "sparse_unique",
    "hidden_start",
    "spot_impossible",
    "hard",
];
const cellIndex = (row, col) => row * 5 + col;
let allLevels = [];
let playlist = [];
let playlistPos = 0;
let selectedTier = TIER_ORDER[0];
let pendingNextTier = null;
let clueOfCell = [];
let stepOfCell = [];
let freeStart = false;
let path = [];
let lastClickedElement = -1;
let secondToLastClickedElement = -1;
let direction = 0;
let previousDirection = 0;
let currentNumber = 0;
const startScreen = document.getElementById("start-screen");
const tierList = document.getElementById("tier-list");
const playButton = document.getElementById("play-button");
const gameScreen = document.getElementById("game-screen");
const levelTitle = document.getElementById("level-title");
const stepCounter = document.getElementById("step-counter");
const messageBox = document.getElementById("message");
const impossibleButton = document.getElementById("impossible-button");
const levelCompletedScreen = document.getElementById("level-completed-screen");
const levelCompletedTitle = document.getElementById("level-completed-title");
const gameCompletedScreen = document.getElementById("game-completed-screen");
const gameCompletedTitle = document.getElementById("game-completed-title");
const restartGameButton = document.getElementById("restart-button");
const resetButton = document.getElementById("reset");
const undoButton = document.getElementById("undo-button");
const nextLevelButton = document.getElementById("next-level-button");
const menuButton = document.getElementById("menu-button");
const IMPOSSIBLE_WAIT = 60;
let impossibleTimer = 0;
function enableImpossibleButton() {
    if (impossibleTimer) {
        clearInterval(impossibleTimer);
        impossibleTimer = 0;
    }
    impossibleButton.disabled = false;
    impossibleButton.textContent = "Declare Impossible";
}
// Declaring impossible is locked for the first 60 seconds of each level so
// the level gets a fair attempt first.
function lockImpossibleButton() {
    if (impossibleTimer) {
        clearInterval(impossibleTimer);
    }
    const btn = impossibleButton;
    btn.disabled = true;
    let remaining = IMPOSSIBLE_WAIT;
    btn.textContent = `Declare Impossible (${remaining})`;
    impossibleTimer = window.setInterval(() => {
        remaining--;
        if (remaining <= 0) {
            enableImpossibleButton();
        }
        else {
            btn.textContent = `Declare Impossible (${remaining})`;
        }
    }, 1000);
}
function currentLevel() {
    return playlist[playlistPos];
}
function tierName(key) {
    return TIER_NAMES[key] || key;
}
function setMessage(text) {
    messageBox.textContent = text;
}
function playStepSound(step) {
    try {
        const clickSound = new Audio("sounds/" + step + ".mp3");
        const p = clickSound.play();
        if (p && typeof p.catch === "function") {
            p.catch(() => undefined);
        }
    }
    catch (e) {
        // Sound is decorative; never break the game over it.
    }
}
function updateCounter() {
    stepCounter.textContent = `Steps: ${currentNumber}/25`;
}
function updateTitle() {
    const lv = currentLevel();
    levelTitle.textContent = `${tierName(lv.tier)} · Level ${playlistPos + 1} of ${playlist.length} (#${lv.id})`;
}
// ---- menu ----
function buildTierMenu() {
    tierList.innerHTML = "";
    const present = TIER_ORDER.filter(t => allLevels.some(l => l.tier === t));
    if (present.indexOf(selectedTier) === -1) {
        selectedTier = present[0] || TIER_ORDER[0];
    }
    present.forEach(t => {
        const count = allLevels.filter(l => l.tier === t).length;
        const btn = document.createElement("button");
        btn.className = "tier-button" + (t === selectedTier ? " selected" : "");
        btn.textContent = `${tierName(t)} (${count})`;
        btn.addEventListener("click", () => {
            selectedTier = t;
            Array.from(tierList.children).forEach(child => child.classList.remove("selected"));
            btn.classList.add("selected");
        });
        tierList.appendChild(btn);
    });
}
playButton.addEventListener("click", () => {
    if (allLevels.length === 0) {
        return;
    }
    startTier(selectedTier);
});
function startTier(tier) {
    playlist = allLevels.filter(l => l.tier === tier).sort((a, b) => a.id - b.id);
    if (playlist.length === 0) {
        return;
    }
    playlistPos = 0;
    startScreen.style.display = "none";
    gameCompletedScreen.style.display = "none";
    levelCompletedScreen.style.display = "none";
    gameScreen.style.display = "block";
    initializeGameState();
}
// ---- grid ----
function clearGrid() {
    const elements = document.getElementsByClassName("grid-item");
    Array.from(elements).forEach(element => {
        while (element.firstChild) {
            element.removeChild(element.firstChild);
        }
        element.removeAttribute("filled");
        element.classList.remove("has-clue");
    });
}
function dirBetween(a, b) {
    if (b === a + 1)
        return 1;
    if (b === a + 5)
        return 2;
    if (b === a - 1)
        return 3;
    return 4;
}
function headRotation(d) {
    if (d === 1)
        return "rotate(90deg)";
    if (d === 2)
        return "rotate(180deg)";
    if (d === 3)
        return "rotate(270deg)";
    return "";
}
function tailRotation(d) {
    if (d === 1)
        return "rotate(180deg)";
    if (d === 2)
        return "rotate(270deg)";
    if (d === 4)
        return "rotate(90deg)";
    return "";
}
function cornerRotation(prev, d) {
    if ((prev === 1 && d === 2) || (prev === 4 && d === 3))
        return "rotate(90deg)";
    if ((prev === 2 && d === 1) || (prev === 3 && d === 4))
        return "rotate(270deg)";
    if ((prev === 1 && d === 4) || (prev === 2 && d === 3))
        return "rotate(180deg)";
    return "";
}
function paintCell(idx, src, rotation) {
    const element = document.querySelector(`[elementNumber="${idx}"]`);
    const img = document.createElement("img");
    if (rotation) {
        img.style.transform = rotation;
    }
    img.src = src;
    element.appendChild(img);
    element.setAttribute("filled", "true");
}
// Re-render the whole worm from the move history. Undo is just path.pop()
// followed by this.
function renderPath() {
    const elements = document.getElementsByClassName("grid-item");
    Array.from(elements).forEach(element => {
        Array.from(element.querySelectorAll("img")).forEach(img => element.removeChild(img));
        element.removeAttribute("filled");
    });
    stepOfCell = new Array(25).fill(0);
    path.forEach((idx, i) => {
        stepOfCell[idx] = i + 1;
        document.querySelector(`[elementNumber="${idx}"]`).setAttribute("filled", "true");
    });
    currentNumber = path.length;
    secondToLastClickedElement = -1;
    previousDirection = 0;
    direction = 0;
    if (path.length === 1) {
        paintCell(path[0], "single tile worm.png", "");
    }
    else if (path.length > 1) {
        paintCell(path[0], "worm-end02.png", tailRotation(dirBetween(path[0], path[1])));
        for (let i = 1; i < path.length - 1; i++) {
            const prev = dirBetween(path[i - 1], path[i]);
            const d = dirBetween(path[i], path[i + 1]);
            if (prev === d) {
                paintCell(path[i], "tube-segment.png", (d === 2 || d === 4) ? "rotate(90deg)" : "rotate(180deg)");
            }
            else {
                paintCell(path[i], "corner-segment.png", cornerRotation(prev, d));
            }
        }
        const last = path.length - 1;
        const d = dirBetween(path[last - 1], path[last]);
        paintCell(path[last], "head02.png", headRotation(d));
        secondToLastClickedElement = path[last - 1];
        previousDirection = d;
        direction = d;
    }
    lastClickedElement = path.length > 0 ? path[path.length - 1] : -1;
    updateCounter();
    updateClueStatus();
}
function undoMove() {
    if (playlist.length === 0) {
        return;
    }
    const minLen = currentLevel().startPosition >= 0 ? 1 : 0;
    if (path.length <= minLen) {
        return;
    }
    path.pop();
    renderPath();
}
function initializeGameState() {
    const lv = currentLevel();
    clearGrid();
    setMessage("");
    updateTitle();
    clueOfCell = new Array(25).fill(null);
    stepOfCell = new Array(25).fill(0);
    secondToLastClickedElement = -1;
    lv.requirements.clues.forEach(cl => {
        const idx = cellIndex(cl.row, cl.col);
        clueOfCell[idx] = cl.number;
        const cell = document.querySelector(`[elementNumber="${idx}"]`);
        cell.classList.add("has-clue");
        const badge = document.createElement("span");
        badge.className = "clue-badge";
        badge.textContent = String(cl.number);
        cell.appendChild(badge);
    });
    path = lv.startPosition >= 0 ? [lv.startPosition] : [];
    freeStart = lv.startPosition < 0;
    renderPath();
    lockImpossibleButton();
    // The 1 is announced only when it is actually on the board: pre-filled
    // here, or placed by the player's first move on free-start levels.
    if (path.length > 0) {
        playStepSound(1);
    }
}
// wire up grid elements to click function
const gridElements = document.getElementsByClassName("grid-item");
let gridIndex = 0;
Array.from(gridElements).forEach(element => {
    element.setAttribute("elementNumber", gridIndex.toString());
    gridIndex++;
    element.addEventListener("click", function () {
        if (element.getAttribute("filled") == "true") {
            return;
        }
        const elementNumber = parseInt(element.getAttribute("elementNumber"));
        // Free start (levels with no 1 clue): first click may be anywhere.
        if (freeStart && currentNumber === 0) {
            path.push(elementNumber);
            renderPath();
            playStepSound(1);
            return;
        }
        let fillElement = false;
        let rotation = "";
        if (elementNumber == lastClickedElement + 1 && elementNumber % 5 != 0) {
            fillElement = true;
            rotation = "rotate(90deg)";
            direction = 1;
        }
        else if (elementNumber == lastClickedElement + 5) {
            fillElement = true;
            rotation = "rotate(180deg)";
            direction = 2;
        }
        else if (elementNumber == lastClickedElement - 1 && elementNumber % 5 != 4) {
            fillElement = true;
            rotation = "rotate(270deg)";
            direction = 3;
        }
        else if (elementNumber == lastClickedElement - 5) {
            fillElement = true;
            rotation = "";
            direction = 4;
        }
        if (fillElement) {
            const step = currentNumber + 1;
            playStepSound(step);
            path.push(elementNumber);
            renderPath();
            checkCompletion();
        }
    });
});
function filledCount() {
    const elements = document.getElementsByClassName("grid-item");
    let count = 0;
    Array.from(elements).forEach(element => {
        if (element.getAttribute("filled") == "true") {
            count++;
        }
    });
    return count;
}
function mismatchedClues() {
    const lv = currentLevel();
    return lv.requirements.clues.filter(cl => stepOfCell[cellIndex(cl.row, cl.col)] !== cl.number);
}
// Clues that are already failed, live: filled on the wrong step, had their
// step pass while unfilled, or are unreachable from the head by distance or
// checkerboard parity. Any of these means the level can't be finished:
// hit Reset and try again.
function badClues() {
    const lv = currentLevel();
    const head = lastClickedElement;
    const bad = [];
    lv.requirements.clues.forEach(cl => {
        const idx = cellIndex(cl.row, cl.col);
        const step = stepOfCell[idx];
        if (step !== 0) {
            if (step !== cl.number) {
                bad.push(cl);
            }
            return;
        }
        if (cl.number <= currentNumber) {
            bad.push(cl);
            return;
        }
        if (head >= 0) {
            const d = Math.abs(Math.floor(head / 5) - cl.row) + Math.abs((head % 5) - cl.col);
            if (d > cl.number - currentNumber || (cl.number - currentNumber - d) % 2 !== 0) {
                bad.push(cl);
            }
        }
    });
    return bad;
}
let clueWarning = "";
function updateClueStatus() {
    const bad = badClues();
    const badCells = {};
    bad.forEach(cl => {
        badCells[cellIndex(cl.row, cl.col)] = true;
    });
    const elements = document.getElementsByClassName("grid-item");
    Array.from(elements).forEach(element => {
        const badge = element.querySelector(".clue-badge");
        if (badge) {
            const idx = parseInt(element.getAttribute("elementNumber"));
            if (badCells[idx]) {
                badge.classList.add("clue-bad");
            }
            else {
                badge.classList.remove("clue-bad");
            }
        }
    });
    if (bad.length === 0) {
        if (messageBox.textContent === clueWarning) {
            setMessage("");
        }
        clueWarning = "";
        // Dead end: grid unfinished but the head has nowhere to go.
        if (lastClickedElement >= 0 && filledCount() < 25) {
            const hr = Math.floor(lastClickedElement / 5);
            const hc = lastClickedElement % 5;
            const offsets = [[1, 0], [-1, 0], [0, 1], [0, -1]];
            let moves = false;
            for (let i = 0; i < offsets.length; i++) {
                const nr = hr + offsets[i][0];
                const nc = hc + offsets[i][1];
                if (nr >= 0 && nr < 5 && nc >= 0 && nc < 5 && stepOfCell[cellIndex(nr, nc)] === 0) {
                    moves = true;
                    break;
                }
            }
            if (!moves) {
                setMessage("Stuck with no moves left — hit Reset and try again.");
            }
        }
    }
    else {
        const nums = bad.map(cl => cl.number).sort((a, b) => a - b).join(", ");
        clueWarning = `Clue${bad.length === 1 ? "" : "s"} ${nums} ${bad.length === 1 ? "is" : "are"} unreachable — hit Reset and try again.`;
        setMessage(clueWarning);
    }
}
function checkCompletion() {
    if (filledCount() < 25) {
        return;
    }
    const bad = mismatchedClues();
    if (bad.length === 0) {
        levelCompletedTitle.textContent = "Level Completed!";
        advance();
    }
    else {
        const nums = bad.map(cl => cl.number).sort((a, b) => a - b).join(", ");
        setMessage(`Grid full, but clue${bad.length === 1 ? "" : "s"} ${nums} ${bad.length === 1 ? "is" : "are"} on the wrong step. Hit Reset and try again.`);
    }
}
function tierAfter(key) {
    const i = TIER_ORDER.indexOf(key);
    for (let j = i + 1; j < TIER_ORDER.length; j++) {
        if (allLevels.some(l => l.tier === TIER_ORDER[j])) {
            return TIER_ORDER[j];
        }
    }
    return null;
}
function advance() {
    const finishedTier = currentLevel().tier;
    playlistPos++;
    gameScreen.style.display = "none";
    if (playlistPos < playlist.length) {
        pendingNextTier = null;
        levelCompletedScreen.style.display = "block";
        return;
    }
    // Tier done: roll straight into the next tier. Menu only at the very end.
    const next = tierAfter(finishedTier);
    if (next) {
        pendingNextTier = next;
        levelCompletedTitle.textContent = `Tier Completed! Next up: ${tierName(next)}`;
        levelCompletedScreen.style.display = "block";
    }
    else {
        pendingNextTier = null;
        gameCompletedTitle.textContent = "Game Completed!";
        gameCompletedScreen.style.display = "block";
    }
}
impossibleButton.addEventListener("click", () => {
    if (currentLevel().label === "impossible") {
        levelCompletedTitle.textContent = "Correct — that one is impossible!";
        advance();
    }
    else {
        setMessage("Nope — this one can be solved. Keep wiggling!");
    }
});
resetButton.addEventListener("click", () => {
    initializeGameState();
});
undoButton.addEventListener("click", () => {
    undoMove();
});
menuButton.addEventListener("click", () => {
    showStartScreen();
});
// Wire up the next level button
nextLevelButton.addEventListener("click", () => {
    // Hide the level completed screen
    levelCompletedScreen.style.display = "none";
    // Show the game screen
    gameScreen.style.display = "block";
    if (pendingNextTier) {
        // Move on to the next tier
        const t = pendingNextTier;
        pendingNextTier = null;
        startTier(t);
    }
    else {
        // Move on to the next level
        initializeGameState();
    }
});
// Back to the tier menu
function showStartScreen() {
    if (impossibleTimer) {
        clearInterval(impossibleTimer);
        impossibleTimer = 0;
    }
    gameScreen.style.display = "none";
    gameCompletedScreen.style.display = "none";
    levelCompletedScreen.style.display = "none";
    startScreen.style.display = "flex";
    buildTierMenu();
}
// Restart game
function restartGame() {
    showStartScreen();
}
// Add event listener to restart button
restartGameButton.addEventListener("click", restartGame);
// Show game completed screen
function showGameCompletedScreen() {
    gameScreen.style.display = "none";
    gameCompletedScreen.style.display = "block";
}
// Boot: the static level pack is the `const levels` in levels.js (loaded
// before this script). No fetch, no fallback.
allLevels = levels.slice().sort((a, b) => a.id - b.id);
buildTierMenu();
// Debug/testing hook (used by headless tests; harmless in production).
window.__ww = {
    snapshot: () => ({
        tier: playlistPos < playlist.length ? currentLevel().tier : selectedTier,
        pos: playlistPos,
        playlistLength: playlist.length,
        currentNumber,
        filled: filledCount(),
        title: levelTitle.textContent,
        message: messageBox.textContent,
        gameVisible: gameScreen.style.display,
    }),
    startTier,
    menu: showStartScreen,
    allowImpossible: enableImpossibleButton,
};
//# sourceMappingURL=main.js.map