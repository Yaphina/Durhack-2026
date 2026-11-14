import random
class Piece:
    def __init__(self, position:int, connected:bool):
        if position < 0 or position > 15:
            raise Exception("There are 16 pieces!")
        else:
            self.position = position
            # when "connected" the piece will automatically know where it goes
            # when not "connected" the piece will have to use our algorithm
            self.connected = connected
            # tracks if the piece has settled into a place or not
            self.finished = False

    def update(self):
        if self.connected:
            finished = True
        else:
            raise NotImplementedError("We gotta write the algorithm dawg")

    
    # the first arr will have to be [[]*5]*5
    # or whatever size we make the board but rn the fucntion assumes it's square
    def initial_place(self, arr):
        placed = False
        while (not placed):
            index = random.randint(0,len(arr)-1)
            if (len(arr[index]) < len(arr)):
                placed = True
                arr[index] = arr[index] + [self]
        return arr # returns the array to use for the next placement
