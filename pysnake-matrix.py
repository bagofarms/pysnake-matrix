#!/usr/bin/env python
import time
import sys
import os
import random
import threading
import argparse

sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/..'))
from rgbmatrix import RGBMatrix, RGBMatrixOptions

from evdev import InputDevice, categorize, ecodes

dev = InputDevice('/dev/input/event0')
escapeKeys = [124, 99]

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

        return True

class KeyboardThread(threading.Thread):
    escapeKeys = [29, 46]

    def __init__(self, updater):
        self.updater = updater
        super(KeyboardThread, self).__init__(target=None)

    def setUpdater(updater):
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
        self.grow = False 

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

class TitleScreen:
    sleepTime = 0.05
    options = ['Go', 'Stahp']
    upButton = 103  # up arrow
    downButton = 108  # down arrow
    selectButton = 2  # 1 button
    # TODO: Load in bmps for these. Maybe make them into a "sprite" class?
    snekSprite = [
        [[0,255,0],[0,255,0],[0,255,0]],
        [[0,255,0],[0,0,0],[0,0,0]],
        [[0,255,0],[0,255,0],[0,255,0]],
        [[0,0,0],[0,0,0],[0,255,0]],
        [[0,255,0],[0,255,0],[0,255,0]]
    ]
    snekPosition = [25, 0]
    arrowSprite = [
        [[0,0,0],[0,0,0],[255,255,255],[0,0,0]],
        [[255,255,255],[255,255,255],[255,255,255],[255,255,255]],
        [[0,0,0],[0,0,0],[255,255,255],[0,0,0]]
    ]
    arrowPosition1 = [25, 25]
    arrowPosition2 = [25, 35]
    
    def __init__(self, matrix, displayWidth, displayHeight):
        self.matrix = matrix
        self.displayWidth = displayWidth
        self.displayHeight = displayHeight
        
        self.cursorPosition = True

    def updateKeyboard(self, active_keys):
        if (self.upButton in active_keys) or (self.downButton in active_keys):
            self.cursorPosition = not self.cursorPosition
        if self.selectButton in active_keys:
            self.running = False

    def drawSprite(self, sprite, position):
        for y, row in enumerate(sprite):
            for x, pixel in enumerate(row):
                self.offset_canvas.SetPixel(x + position[0], y + position[1], *pixel)

    def updateScreen(self):
        self.offset_canvas.Clear()

        self.drawSprite(self.snekSprite, self.snekPosition)
        if self.cursorPosition:
            self.drawSprite(self.arrowSprite, self.arrowPosition1)
        else:
            self.drawSprite(self.arrowSprite, self.arrowPosition2)

        self.offset_canvas = self.matrix.SwapOnVSync(self.offset_canvas)

    def run(self):
        self.offset_canvas = self.matrix.CreateFrameCanvas()
        self.loop()
        return self.cursorPosition

    def loop(self):
        self.running = True
        while self.running:
            self.updateScreen()
            time.sleep(self.sleepTime)

class PySnake:
    foodMarker = 'O'
    spaceMarker = '-'
    snakeMarkers = ['1','2']

    # Player 1 = up, right, down, left arrow keys
    # Player 2 = r, g, f, d
    directionDicts = [
        {103: 0, 106: 1, 108: 2, 105: 3},
        {19: 0, 34: 1, 33: 2, 32: 3}
    ]

    # Time between frames (seconds)
    sleepTime = 0.05

    def __init__(self, matrix, displayWidth, displayHeight):
        self.matrix = matrix
        self.displayWidth = displayWidth
        self.displayHeight = displayHeight

    def initializeBoard(self):
        self.board = []
        for x in range(self.displayWidth):
            col = []
            for y in range(self.displayWidth):
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
                if self.board[x][y] == self.snakeMarkers[0]:
                    self.offset_canvas.SetPixel(x, y, 0, 255, 0)
                elif self.board[x][y] == self.snakeMarkers[1]:
                    self.offset_canvas.SetPixel(x, y, 255, 255, 0)
                elif self.board[x][y] == self.foodMarker:
                    self.offset_canvas.SetPixel(x, y, 0, 0, 255)
            # print out + "\r\n"
        self.offset_canvas = self.matrix.SwapOnVSync(self.offset_canvas)

    def placeSnake(self, coords, marker):
        self.board[coords[0]][coords[1]] = self.snakeMarkers[marker]

    def placeFood(self):
        while True:
            x = random.randint(0, self.displayWidth - 1)
            y = random.randint(0, self.displayHeight - 1)
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

    def run(self):
        self.offset_canvas = self.matrix.CreateFrameCanvas()

        # Place one snake on the left, and the other on the right.
        # One will be going up, the other down
        self.snakes = [
            Snake( head=(self.displayWidth/4, self.displayHeight/2), tail=(self.displayWidth/4, self.displayHeight/2+1), direction=0),
            Snake( head=((self.displayWidth/4)*3, self.displayHeight/2), tail=((self.displayWidth/4)*3, self.displayHeight/2-1), direction=2)
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
        return True

    def loop(self):
        self.running = True
        while self.running:
            for idx, snake in enumerate(self.snakes):
                # move snake in direction by 1
                newHead, oldTail = snake.move()

                # Check for going off the map
                if (newHead[0] >= self.displayWidth) or (newHead[0] < 0) or (newHead[1] >= self.displayHeight) or (newHead[1] < 0):
                    print "Snek out of bounds!  Loser is Player" + str(idx+1)
                    self.running = False
                    break

                # If space was food, set grow to True and place new food
                if self.board[newHead[0]][newHead[1]] == self.foodMarker:
                    snake.grow = True
                    self.placeFood()
                elif self.board[newHead[0]][newHead[1]] in self.snakeMarkers:
                    # If space was snake, the game is over
                    print "Snek collision!  Loser is Player " + str(idx+1)
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

    title = TitleScreen(display.matrix, display.displayWidth, display.displayHeight)
    # pysnake = PySnake(display.matrix, display.displayWidth, display.displayHeight)

    keyboard = KeyboardThread(updater=title.updateKeyboard)
    keyboard.start()

    # Put these in a while loop so it keeps going until someone hits exit on the title screen?
    # Maybe if title.run() returns False, exit?
    title.run()
    # pysnake.run()

    keyboard.stop()
