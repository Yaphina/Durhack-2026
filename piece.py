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
        else: # Naive implementation: performance could be better but likely not an issue
            # First, check if there are any other pieces in the grid
            alone = True
            for lst in arr:
                for i in lst:
                    if (i != -1 and i != self):
                        alone = False
                        break
            if (alone):
                self.finished = True
                return

            # TODO: What if they're not alone?
            # Cases to consider:
            # (1) Multiple singles that can not merge
            # (2) Multiple singles that can merge
            # (3) A cluster that can be merged with (need to write cluster class, which will have a list of positions rather than just one)
            #
            # Need to write code for pursuing a piece and then we can call merge(p1, p2) with them both if they meet
            # Which will return a cluster if they are able to merge and False if they can't
            # That handles cases (1) and (2) ideally
            # Should we track failed merges? could help with case (1)
    
    # Assumes the shape of the grid is square
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

def merge(p1, p2):
    raise NotImplementedError("Will need to handle merging pieces, pieces and clusters, and 2 clusters")
