#!/usr/bin/env python
import time
import sys
import os
import random
import threading
import argparse
import math

sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/..'))
from rgbmatrix import RGBMatrix, RGBMatrixOptions

from evdev import InputDevice, categorize, ecodes

from PIL import Image

dev = InputDevice('/dev/input/by-id/usb-XGaming_X-Arcade-event-kbd')
escapeKeys = (124, 99)

titleImage = 'snek.bmp'
scoreBg = 'end.bmp'
gameoverBg = 'gameover.bmp'
p1Image = 'one.bmp'
p2Image = 'two.bmp'

class Display:
    def __init__(self, *args, **kwargs):
        self.parser = argparse.ArgumentParser()

        self.parser.add_argument("-r", "--led-rows", action="store", help="Display rows. 16 for 16x32, 32 for 32x32. Default: 32", default=32, type=int)
        self.parser.add_argument("--led-cols", action="store", help="Panel columns. Typically 32 or 64. (Default: 32)", default=32, type=int)
        self.parser.add_argument("-c", "--led-chain", action="store", help="Daisy-chained boards. Default: 1.", default=1, type=int)
        self.parser.add_argument("-P", "--led-parallel", action="store", help="For Plus-models or RPi2: parallel chains. 1..3. Default: 1", default=1, type=int)
        self.parser.add_argument("-p", "--led-pwm-bits", action="store", help="Bits used for PWM. Something between 1..11. Default: 11", default=11, type=int)
        self.parser.add_argument("-b", "--led-brightness", action="store", help="Sets brightness level. Default: 100. Range: 1..100", default=100, type=int)
        self.parser.add_argument("-m", "--led-gpio-mapping", help="Hardware Mapping: regular, adafruit-hat, adafruit-hat-pwm" , choices=['regular', 'adafruit-hat', 'adafruit-hat-pwm'], type=str)
        self.parser.add_argument("--led-scan-mode", action="store", help="Progressive or interlaced scan. 0 Progressive, 1 Interlaced (default)", default=1, choices=range(2), type=int)
        self.parser.add_argument("--led-pwm-lsb-nanoseconds", action="store", help="Base time-unit for the on-time in the lowest significant bit in nanoseconds. Default: 130", default=130, type=int)
        self.parser.add_argument("--led-show-refresh", action="store_true", help="Shows the current refresh rate of the LED panel")
        self.parser.add_argument("--led-slowdown-gpio", action="store", help="Slow down writing to GPIO. Range: 1..100. Default: 1", choices=range(3), type=int)
        self.parser.add_argument("--led-no-hardware-pulse", action="store", help="Don't use hardware pin-pulse generation")
        self.parser.add_argument("--led-rgb-sequence", action="store", help="Switch if your matrix has led colors swapped. Default: RGB", default="RGB", type=str)
        self.parser.add_argument("--led-pixel-mapper", action="store", help="Apply pixel mappers. e.g \"Rotate:90\"", default="", type=str)
        self.parser.add_argument("--led-row-addr-type", action="store", help="0 = default; 1=AB-addressed panels;2=row direct", default=0, type=int, choices=[0,1,2])
        self.parser.add_argument("--led-multiplexing", action="store", help="Multiplexing type: 0=direct; 1=strip; 2=checker; 3=spiral; 4=ZStripe; 5=ZnMirrorZStripe; 6=coreman; 7=Kaler2Scan; 8=ZStripeUneven (Default: 0)", default=0, type=int)
        self.parser.add_argument("--disp-width", action="store", help="Width of full display.  Default: 64.", default=64, type=int)
        self.parser.add_argument("--disp-height", action="store", help="Height of full display. Default: 64.", default=64, type=int)
        # self.parser.add_argument("--double-size", action="store", help="Whether the players and food on screen should be displayed in double size", default=False, type=bool)

    def create(self):
        self.args = self.parser.parse_args()

        options = RGBMatrixOptions()

        if self.args.led_gpio_mapping != None:
            options.hardware_mapping = self.args.led_gpio_mapping
            options.rows = self.args.led_rows
            options.cols = self.args.led_cols
            options.chain_length = self.args.led_chain
            options.parallel = self.args.led_parallel
            options.row_address_type = self.args.led_row_addr_type
            options.multiplexing = self.args.led_multiplexing
            options.pwm_bits = self.args.led_pwm_bits
            options.brightness = self.args.led_brightness
            options.pwm_lsb_nanoseconds = self.args.led_pwm_lsb_nanoseconds
            options.led_rgb_sequence = self.args.led_rgb_sequence
            options.pixel_mapper_config = self.args.led_pixel_mapper
        if self.args.led_show_refresh:
            options.show_refresh_rate = 1

        if self.args.led_slowdown_gpio != None:
            options.gpio_slowdown = self.args.led_slowdown_gpio
        if self.args.led_no_hardware_pulse:
            options.disable_hardware_pulsing = True

        self.matrix = RGBMatrix(options = options)
        self.displayWidth = self.args.disp_width
        self.displayHeight = self.args.disp_height
        # self.doubleSize = self.args.double_size
        self.doubleSize = True

        return True

class KeyboardThread(threading.Thread):
    escapeKeys = [29, 46]

    def __init__(self, updater):
        self.updater = updater
        super(KeyboardThread, self).__init__(target=None)

    def setUpdater(self, updater):
        self.updater = updater

    def run(self):
        print 'Starting Keyboard Thread'
        for event in dev.read_loop():
            if event.type == ecodes.EV_KEY:
                print(dev.active_keys())
                self.active_keys = dev.active_keys()
                self.updater(self.active_keys)

    def stop(self):
        print "Keyboard thread killing itself"
        super(KeyboardThread, self)._Thread__stop()

class Snake:
    def __init__(self, head, tail, direction):
        self.body = [head, tail]
        self.__direction = direction
        self.__newdirection = direction
        self.grow = False 
        self.length = 2

    # Changing direction isn't as simple as writing a value
    # We need to check for exact opposite directions first,
    # and ignore no-change or out-of-bounds conditions
    # 0 is up, 1 is right, 2 is down, 3 is left
    def changeDirection(self, command):
        if (command != self.__direction) and (command < 4):
            # Check for opposite directions and ignore
            if (command == 0) and (self.__direction == 2):
                return
            elif (command == 2) and (self.__direction == 0):
                return
            elif (command + self.__direction) == 4:
                return
            else:
                self.__newdirection = command

    def move(self):
        self.__direction = self.__newdirection
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
            self.length += 1
            oldTail = None
            self.grow = False
        else:
            oldTail = self.body.pop()

        # Return the new head and the old tail
        return self.body[0], oldTail

class TitleScreen:
    sleepTime = 0.05
    upButton = 72  # left joystick up
    downButton = 80  # left joystick down
    onePlayer = 2  # 1p button
    twoPlayer = 3  # 2p button
    arrowSprite = (
        ((0,0,0),(0,0,0),(255,255,255),(0,0,0)),
        ((255,255,255),(255,255,255),(255,255,255),(255,255,255)),
        ((0,0,0),(0,0,0),(255,255,255),(0,0,0)),
    )
    arrowPosition1 = (24, 39)
    arrowPosition2 = (24, 47)
    
    def __init__(self, matrix, displayWidth, displayHeight, titleImage):
        self.matrix = matrix
        self.displayWidth = displayWidth
        self.displayHeight = displayHeight

        self.titleImage = Image.open(titleImage)
        
        self.cursorPosition = True
        self.playerSelection = None

    def updateKeyboard(self, active_keys):
        if (self.upButton in active_keys) or (self.downButton in active_keys):
            self.cursorPosition = not self.cursorPosition
        if self.onePlayer in active_keys:
            self.playerSelection = 1
            self.running = False
        elif self.twoPlayer in active_keys:
            self.playerSelection = 2
            self.running = False

    def drawTitleImage(self):
        for y in range(self.displayHeight):
            for x in range(self.displayWidth):
                pixelval = self.titleImage.getpixel((x, y))
                self.offset_canvas.SetPixel(x, y, *pixelval)

    def drawSprite(self, sprite, position):
        for y, row in enumerate(sprite):
            for x, pixel in enumerate(row):
                self.offset_canvas.SetPixel(x + position[0], y + position[1], *pixel)

    def updateScreen(self):
        self.offset_canvas.Clear()

        self.drawTitleImage()
        if self.cursorPosition:
            self.drawSprite(self.arrowSprite, self.arrowPosition1)
        else:
            self.drawSprite(self.arrowSprite, self.arrowPosition2)

        self.offset_canvas = self.matrix.SwapOnVSync(self.offset_canvas)

    def run(self):
        self.offset_canvas = self.matrix.CreateFrameCanvas()
        self.loop()
        return self.cursorPosition, self.playerSelection

    def loop(self):
        self.running = True
        while self.running:
            self.updateScreen()
            time.sleep(self.sleepTime)

class ScoreScreen:
    playerPosition = (48,32)
    sleepTime = 0.05
    
    def __init__(self, matrix, displayWidth, displayHeight, bgImage, gameOverImage, playerImages):
        self.matrix = matrix
        self.displayWidth = displayWidth
        self.displayHeight = displayHeight

        self.bgImage = Image.open(bgImage)
        self.gameOverImage = Image.open(gameOverImage)
        self.playerImages = []
        for img in playerImages:
            self.playerImages.append(Image.open(img))

        self.winner = 0
        
        self.cursorPosition = True

    def updateKeyboard(self, active_keys):
        # If any key is pressed, exit the score screen
        if len(active_keys) > 0:
            self.running = False

    def drawImage(self, image, position):
        width, height = image.size

        for y in range(height):
            for x in range(width):
                pixelval = image.getpixel((x, y))
                self.offset_canvas.SetPixel(x + position[0], y + position[1], *pixelval)

    def updateScreen(self):
        self.offset_canvas.Clear()

        self.drawImage(self.bgImage, (0, 0))

        if self.winner is not False:
            self.drawImage(self.playerImages[self.winner], self.playerPosition)
        else:
            self.drawImage(self.gameOverImage, (0, 31))

        self.offset_canvas = self.matrix.SwapOnVSync(self.offset_canvas)

    def run(self, winner):
        self.winner, self.score = winner
        self.offset_canvas = self.matrix.CreateFrameCanvas()
        self.loop()
        return True

    def loop(self):
        self.running = True
        self.updateScreen() # Only need to update the screen once for this one
        time.sleep(3)
        while self.running:
            time.sleep(self.sleepTime)

class PySnake:
    foodMarker = 'O'
    spaceMarker = '-'
    snakeMarkers = ('1','2')

    # Player 1 = up, right, down, left arrow keys
    # Player 2 = r, g, f, d
    directionDicts = [
        {72: 0, 77: 1, 80: 2, 75: 3},
        {19: 0, 34: 1, 33: 2, 32: 3}
    ]

    # Time between frames (seconds)
    sleepTime = 0.05

    def __init__(self, matrix, displayWidth, displayHeight, doubleSize=False, players=1):
        self.matrix = matrix
        self.displayWidth = displayWidth
        self.displayHeight = displayHeight
        self.doubleSize = doubleSize
        self.players = players

    def initializeBoard(self):
        self.board = []
        if self.doubleSize:
            width = self.displayWidth/2
            height = self.displayHeight/2
        else:
            width = self.displayWidth
            height = self.displayHeight
        for x in range(width):
            col = []
            for y in range(height):
                col += [self.spaceMarker]
            self.board += [col]

    def printBoard(self):
        # print ('@' * self.displayWidth) + "\r\n"
        self.offset_canvas.Clear()
        for y in range(self.displayHeight):
            # out = ''
            for x in range(self.displayWidth):
                # out += str(self.board[x][y])
                # TODO: Make these snake colors configurable
                if self.doubleSize:
                    brdy = int(math.ceil(y/2))
                    brdx = int(math.ceil(x/2))
                else:
                    brdy = y
                    brdx = x
                if self.board[brdx][brdy] == self.snakeMarkers[0]:
                    self.offset_canvas.SetPixel(x, y, 34, 177, 76)
                elif self.board[brdx][brdy] == self.snakeMarkers[1]:
                    self.offset_canvas.SetPixel(x, y, 255, 242, 0)
                elif self.board[brdx][brdy] == self.foodMarker:
                    self.offset_canvas.SetPixel(x, y, 0, 0, 255)
            # print out + "\r\n"
        self.offset_canvas = self.matrix.SwapOnVSync(self.offset_canvas)

    def placeSnake(self, coords, marker):
        self.board[coords[0]][coords[1]] = self.snakeMarkers[marker]

    def placeFood(self):
        if self.doubleSize:
            width = self.displayWidth/2
            height = self.displayHeight/2
        else:
            width = self.displayWidth
            height = self.displayHeight
        while True:
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)
            if self.board[x][y] == self.spaceMarker:
                break
        self.board[x][y] = self.foodMarker

    def deleteMarker(self, coords):
        self.board[coords[0]][coords[1]] = self.spaceMarker

    def updateKeyboard(self, active_keys):
        for idx, snake in enumerate(self.snakes):
            for char in active_keys:
                if char in self.directionDicts[idx]:
                    snake.changeDirection(self.directionDicts[idx][char])

    def populateWinner(self, loser):
        if self.players == 1:
            self.winner = (False, self.snakes[0].length)
        if self.players == 2:
            if loser == 0:
                self.winner = (1, self.snakes[1].length)
            else:
                self.winner = (0, self.snakes[0].length)

    def run(self):
        self.offset_canvas = self.matrix.CreateFrameCanvas()

        # Place one snake on the left, and the other on the right.
        # One will be going up, the other down
        if self.doubleSize:
            width = self.displayWidth/2
            height = self.displayHeight/2
        else:
            width = self.displayWidth
            height = self.displayHeight

        self.snakes = []

        # for x in range(self.players):
        #     self.snakes.append(Snake( head=(width/(2 * self.players), height/2), tail=(width/(2 * self.players), height/2+1), direction=0))
        
        if self.players == 1:
            self.snakes = [
                Snake( head=(width/2, height/2), tail=(width/2, height/2+1), direction=0)
            ]
        elif self.players == 2:
            self.snakes = [
                Snake( head=(width/4, height/2), tail=(width/4, height/2+1), direction=0),
                Snake( head=((width/4)*3, height/2), tail=((width/4)*3, height/2-1), direction=2)
            ]

        self.initializeBoard()

        # Populate the initial two blocks of the snakes
        for idx, snake in enumerate(self.snakes):
            self.placeSnake(snake.body[0], marker=idx)
            self.placeSnake(snake.body[1], marker=idx)

        # Place food for the snakes
        self.placeFood()
        self.placeFood()

        self.printBoard()
        time.sleep(1) # Sleep for a sec to let the user get oriented

        # Start loop
        self.loop()
        return self.winner

    def loop(self):
        self.running = True
        while self.running:
            for idx, snake in enumerate(self.snakes):
                # move snake in direction by 1
                newHead, oldTail = snake.move()

                if self.doubleSize:
                    width = self.displayWidth/2
                    height = self.displayHeight/2
                else:
                    width = self.displayWidth
                    height = self.displayHeight

                # Check for going off the map
                if (newHead[0] >= width) or (newHead[0] < 0) or (newHead[1] >= height) or (newHead[1] < 0):
                    print "Snek out of bounds!  Loser is Player" + str(idx+1)
                    self.populateWinner(idx)
                    self.running = False
                    break

                # If space was food, set grow to True and place new food
                if self.board[newHead[0]][newHead[1]] == self.foodMarker:
                    snake.grow = True
                    self.placeFood()
                elif self.board[newHead[0]][newHead[1]] in self.snakeMarkers:
                    # If space was snake, the game is over
                    print "Snek collision!  Loser is Player " + str(idx+1)
                    self.populateWinner(idx)
                    self.running = False
                    break

                # Remove tail unless the snake grew
                if oldTail is not None:
                    self.deleteMarker(oldTail)

                # Draw the snake
                self.placeSnake(newHead, marker=idx)

            self.printBoard()
            time.sleep(self.sleepTime)

# Main function
if __name__ == "__main__":
    display = Display()
    if (not display.create()):
        display.parser.print_help()
        sys.exit(0)

    title = TitleScreen(display.matrix, display.displayWidth, display.displayHeight, titleImage)
    pysnakeone = PySnake(display.matrix, display.displayWidth, display.displayHeight, display.doubleSize, players=1)
    pysnaketwo = PySnake(display.matrix, display.displayWidth, display.displayHeight, display.doubleSize, players=2)
    score = ScoreScreen(display.matrix, display.displayWidth, display.displayHeight, scoreBg, gameoverBg, (p1Image, p2Image))

    keyboard = KeyboardThread(updater=title.updateKeyboard)
    keyboard.start()

    # Title screen returns false when user selects exit
    running = True
    while running:
        running, players = title.run()
        if running:
            if players == 1:
                keyboard.setUpdater(pysnakeone.updateKeyboard)
                winner = pysnakeone.run()
            elif players == 2:
                keyboard.setUpdater(pysnaketwo.updateKeyboard)
                winner = pysnaketwo.run()
            keyboard.setUpdater(score.updateKeyboard)
            score.run(winner)
            keyboard.setUpdater(title.updateKeyboard)

    keyboard.stop()
