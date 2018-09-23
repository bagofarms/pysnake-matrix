import time
import sys
import random
import keyboard

class Snake:
    def __init__(self, head, tail, direction):
        self.body = [head, tail]
        self.__direction = direction
        self.grow = False 

    # Changing direction isn't as simple as writing a value
    # We need to check for exact opposite directions first,
    # and ignore no-change or out-of-bounds conditions
    # 0 is up, 1 is right, 2 is down, 3 is left
    def changeDirection(self, command):
        if (command != self.__direction) and (command < 4):
            total = command + self.__direction
            # Check for opposite directions and ignore
            if (total != 2) or (total != 5):
                self.__direction = command

    def move(self):
        if self.__direction == 0:
            self.body.insert(0, (self.body[0][0], self.body[0][1] - 1))
        elif self.__direction == 1:
            self.body.insert(0, (self.body[0][0] + 1, self.body[0][1]))
        elif self.__direction == 2:
            self.body.insert(0, (self.body[0][0], self.body[0][1] + 1))
        else:
            self.body.insert(0, (self.body[0][0] - 1, self.body[0][1]))

        if self.grow:
            # return None since we are growing and don't want the tail deleted
            oldTail = None
            self.grow = False
        else:
            oldTail = self.body.pop()

        # Return the new head and the old tail
        return self.body[0], oldTail

foodMarker = 'O'
snakeMarker = 'X'
spaceMarker = '-'

directionDict = {
    'up': 0,
    'right': 1,
    'down': 2,
    'left': 3
}

# from rgbmatrix import RGBMatrix, RGBMatrixOptions

# # Configuration for the matrix
# options = RGBMatrixOptions()
# # Display rows. 16 for 16x32, 32 for 32x32.
# options.rows = 16
# # Panel columns. Typically 32 or 64.
# options.cols = 32
# options.pixel_mapper_config = "Snake:4"
# options.chain_length = 8
# options.parallel = 1
# options.hardware_mapping = 'adafruit-hat'

# matrix = RGBMatrix(options = options)

# How many loops before the next food appears
foodFreq = 10

# The maximum number of food pellets on the screen
maxFood = 5

# Time between frames (seconds)
sleepTime = 1

# Set number of snakes (max 4)
# players = 1
# snakes = []
# for x in range(snakes):
#     snakes[x] = Snake(head, tail, direction)

displayWidth = 24
displayHeight = 24

board = []
# TODO: Convert to "initialize board" subroutine
for x in range(displayWidth):
    col = []
    for y in range(displayWidth):
        col += [spaceMarker]
    board += [col]

def printBoard():
    for y in range(displayHeight):
        out = ''
        for x in range(displayWidth):
            out += str(board[x][y])
        print out

def placeSnake(coords):
    board[coords[0]][coords[1]] = snakeMarker

def placeFood():
    while True:
        x = random.randint(0,displayWidth-1)
        y = random.randint(0,displayHeight-1)
        if board[x][y] == spaceMarker:
            break
    board[x][y] = foodMarker

def deleteMarker(coords):
    board[coords[0]][coords[1]] = spaceMarker

def handleKeyEvent(e):
    print e.name
    if e.name in directionDict:
        snake.changeDirection(directionDict[e.name])

snake = Snake(
    (displayWidth/2, displayHeight/2),
    (displayWidth/2, displayHeight/2+1),
    0
    )

# Populate the initial two blocks of the snake
placeSnake(snake.body[0])
placeSnake(snake.body[1])
placeFood()

printBoard()

# Set up keyboard listener
keyboard.on_press(handleKeyEvent)

# The Render Loop
try:
    while True:
        # move snake in direction by 1
        newHead, oldTail = snake.move()

        # Check for going off the map
        if (newHead[0] >= displayWidth) or (newHead[0] < 0) or (newHead[1] >= displayHeight) or (newHead[1] < 0):
            break

        # If space was food, set grow to True and place new food
        if board[newHead[0]][newHead[1]] == foodMarker:
            snake.grow = True
            placeFood()
        elif board[newHead[0]][newHead[1]] == snakeMarker:
            # If space was snake, the game is over
            break

        # Remove tail unless the snake grew
        if oldTail is not None:
            deleteMarker(oldTail)
        
        # Draw the snake
        placeSnake(newHead)

        printBoard()
        time.sleep(sleepTime)
except KeyboardInterrupt:
    sys.exit(0)
