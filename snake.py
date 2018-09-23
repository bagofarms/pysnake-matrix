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
        print 'command = ' + str(command) + ', direction = ' + str(self.__direction)
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