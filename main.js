const levels = [
    {
        startPosition: 12
    },
    {
        startPosition: 10,
        requirements: {
        // add specific requirements for level 2 here
        }
    },
    {
        startPosition: 6,
        requirements: {
        // add specific requirements for level 3 here
        }
    }, {
        startPosition: 8,
        requirements: {
        // add specific requirements for level 3 here
        }
    }, {
        startPosition: 14,
        requirements: {
        // add specific requirements for level 3 here
        }
    }, {
        startPosition: 18,
        requirements: {
        // add specific requirements for level 3 here
        }
    }, {
        startPosition: 22,
        requirements: {
        // add specific requirements for level 3 here
        }
    },
    // add more levels here
];
const startScreen = document.getElementById("start-screen");
const playButton = document.getElementById("play-button");
const gameScreen = document.getElementById("game-screen");
const levelCompletedScreen = document.getElementById("level-completed-screen");
const gameCompletedScreen = document.getElementById("game-completed-screen");
const restartGameButton = document.getElementById("restart-button");
playButton.addEventListener("click", () => {
    startScreen.style.display = "none";
    gameScreen.style.display = "block";
    initializeGameState();
});
let currentLevel = 0;
let startPosition = levels[currentLevel].startPosition;
let lastClickedElement;
let secondToLastClickedElement = -1;
let direction;
let previousDirection;
let currentNumber;
// wire up grid elements to click function
var elements = document.getElementsByClassName("grid-item");
let x = 0;
Array.from(elements).forEach(element => {
    element.setAttribute("elementNumber", x.toString());
    element.addEventListener("click", function () {
        let fillElement = false;
        let rotation;
        if (element.getAttribute("filled") == "true") {
            return;
        }
        var elementNumber = parseInt(element.getAttribute("elementNumber"));
        if (elementNumber == lastClickedElement + 1 && elementNumber % 5 != 0) {
            fillElement = true;
            rotation = 'rotate(90deg)';
            direction = 1;
        }
        else if (elementNumber == lastClickedElement + 5) {
            fillElement = true;
            rotation = 'rotate(180deg)';
            direction = 2;
        }
        else if (elementNumber == lastClickedElement - 1 && elementNumber % 5 != 4) {
            fillElement = true;
            rotation = 'rotate(270deg)';
            direction = 3;
        }
        else if (elementNumber == lastClickedElement - 5) {
            fillElement = true;
            direction = 4;
        }
        if (fillElement) {
            currentNumber++;
            var clickSound = new Audio('.\\sounds\\' + currentNumber + '.mp3');
            clickSound.play();
            var elem = document.createElement("img");
            elem.style.transform = rotation;
            elem.src = 'Head.png';
            element.appendChild(elem);
            element.setAttribute("filled", "true");
            let elementQuery = `[elementNumber="${lastClickedElement}"]`;
            var previousElement = document.querySelector(elementQuery);
            if (secondToLastClickedElement == -1) {
                //place and rotate tail image
                previousElement.firstChild.src = 'Tail.png';
                switch (direction) {
                    case 1:
                        previousElement.firstChild.style.transform = 'rotate(180deg)';
                        break;
                    case 2:
                        previousElement.firstChild.style.transform = 'rotate(270deg)';
                        break;
                    case 3:
                        break;
                    case 4:
                        previousElement.firstChild.style.transform = 'rotate(90deg)';
                        break;
                }
            }
            else {
                if (previousDirection == direction) {
                    previousElement.firstChild.src = 'Straight.png';
                    if (direction == 2 || direction == 4) {
                        previousElement.firstChild.style.transform = 'rotate(90deg)';
                    }
                    else {
                        previousElement.firstChild.style.transform = 'rotate(180deg)';
                    }
                }
                else {
                    previousElement.firstChild.src = 'Corner.png';
                    if ((previousDirection == 1 && direction == 2) || (previousDirection == 4 && direction == 3)) {
                        previousElement.firstChild.style.transform = 'rotate(90deg)';
                    }
                    else if ((previousDirection == 2 && direction == 1) || (previousDirection == 3 && direction == 4)) {
                        previousElement.firstChild.style.transform = 'rotate(270deg)';
                    }
                    else if ((previousDirection == 4 && direction == 1) || (previousDirection == 3 && direction == 2)) {
                        previousElement.firstChild.style.transform = '';
                    }
                    else if ((previousDirection == 1 && direction == 4) || (previousDirection == 2 && direction == 3)) {
                        previousElement.firstChild.style.transform = 'rotate(180deg)';
                    }
                }
            }
            secondToLastClickedElement = lastClickedElement;
            lastClickedElement = elementNumber;
            previousDirection = direction;
            checkCompletion();
        }
    });
    x++;
});
var firstElement = document.querySelector(`[elementNumber="${startPosition}"]`);
var elem = document.createElement("img");
elem.src = 'Mini.png';
firstElement.appendChild(elem);
firstElement.setAttribute("filled", "true");
var resetButton = document.getElementById('reset');
resetButton.addEventListener('click', () => {
    initializeGameState();
});
function checkCompletion() {
    var elements = document.getElementsByClassName("grid-item");
    var count = 0;
    Array.from(elements).forEach(element => {
        if (element.getAttribute("filled") == "true") {
            count++;
        }
    });
    if (count == elements.length) {
        console.log("Level complete!");
        currentLevel++;
        if (currentLevel == levels.length) {
            gameCompletedScreen.style.display = "block";
        }
        else {
            levelCompletedScreen.style.display = "block";
        }
        // Hide the game screen
        gameScreen.style.display = "none";
    }
}
// Wire up the next level button
const nextLevelButton = document.getElementById("next-level-button");
nextLevelButton.addEventListener("click", () => {
    // Hide the level completed screen
    levelCompletedScreen.style.display = "none";
    // Show the game screen
    gameScreen.style.display = "block";
    // Move on to the next level
    initializeGameState();
});
function initializeGameState() {
    // reset the game state here
    console.log('setting up game...');
    if (currentLevel == levels.length) {
        console.log("All levels complete!");
        return;
    }
    startPosition = levels[currentLevel].startPosition;
    lastClickedElement = startPosition;
    secondToLastClickedElement = -1;
    currentNumber = 1;
    var clickSound = new Audio('.\\sounds\\1.mp3');
    clickSound.play();
    var elements = document.getElementsByClassName("grid-item");
    Array.from(elements).forEach(element => {
        var child = element.firstChild;
        if (child != null) {
            element.removeChild(element.firstChild); // remove snake images
            element.removeAttribute("filled"); // remove "filled" attribute
        }
    });
    var firstElement = document.querySelector(`[elementNumber="${startPosition}"]`);
    var elem = document.createElement("img");
    elem.src = 'Mini.png';
    firstElement.appendChild(elem);
    firstElement.setAttribute("filled", "true");
}
// Show game completed screen
function showGameCompletedScreen() {
    gameScreen.style.display = "none";
    gameCompletedScreen.style.display = "block";
}
// Restart game
function restartGame() {
    gameCompletedScreen.style.display = "none";
    levelCompletedScreen.style.display = "none";
    startScreen.style.display = "flex";
    currentLevel = 0;
    initializeGameState();
}
// Add event listener to restart button
restartGameButton.addEventListener("click", restartGame);
//# sourceMappingURL=main.js.map