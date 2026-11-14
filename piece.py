import random

class Piece:
    def __init__(self, destination:int, connected:bool):
        if destination < 0 or destination > 15:
            raise Exception("There are 16 pieces!")
        else:
            self.destination = destination

            # when "connected" the piece will automatically know where it goes
            # when not "connected" the piece will have to use our algorithm
            self.connected = connected

            # tracks if the piece has settled into a place or not
            self.finished = False

    def update(self, arr):
        if self.connected:
            finished = True
        else:
            raise NotImplementedError("We gotta write the algorithm dawg")

    
    # the first arr will have to be [[-1]*5]*5
    # -1 represents an empty space
    def initial_place(self, arr):
        placed = False
        while (not placed):
            x_index = random.randint(0,len(arr)-1)
            y_index = random.randint(0,len(arr)-1)
            if (arr[y_index][x_index] == -1):
                placed = True
                arr[y_index][x_index] = self
        return arr # returns the array to use for the next placement
