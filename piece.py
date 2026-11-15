import dearpygui.dearpygui as dpg
from enum import Enum
import random

class Piece:
    clusters = 0
    def __init__(self, destination: int, connected: bool, parentWindow: int | str):
        if destination < 0 or destination > 15:
            raise Exception("There are 16 pieces!")
        else:
            self.destination = destination
            # Creating image to puzzle 
            filePath = "mona lisa 4x4 puzzle/piece{0}.png".format(destination)
            width, height, channels, data = dpg.load_image(filePath)
            with dpg.texture_registry():
                textureTag = dpg.add_static_texture(width=width, height=height, default_value=data)
            self.imageTag = dpg.add_image(textureTag, pos=(400 * destination, 600), parent=parentWindow)
            
            
            # when "connected" the piece will automatically know where it goes
            # when not "connected" the piece will have to use our algorithm
            self.connected = connected

            # tracks if the piece has settled into a place or not
            self.finished = False

            # A piece is always "seeking" a piece to attempt merge or "chasing" that piece
            # So if seeking is false we must be chasing (unless we are finished)
            self.seeking = True

            # Tracks which pieces we have attempted merging with
            self.attempted = [False]*16
            self.attempted[destination] = True

            # Being part of cluster "0" actually means not being a part of a cluster at all
            self.cluster = 0

            # Stores target when chasing
            self.target = self # Dummy; will get overwritten
    
    def getImageTag(self):
        return self.imageTag
    
    def update(self, arr):
        if self.finished:
            return;
        if self.connected:
            finished = True
            return;

        if seeking:
            # First, check if there are any other pieces in the grid
            # alone = True
            # for lst in arr:
            #     for i in lst:
            #         if (i != -1 and i != self):
            #             alone = False
            #             break
            # if (alone):
            #     self.finished = True
            #     return
            #
            # Pick a target
            for row in arr:
                for i in row:
                    if i != -1 and not self.attempted[i.destination]:
                        target = i
                        seeking = False
                        return

            # No target could be found: we are finished
            self.finished = True
        else:
            raise NotImplementedError("Not written chasing code yet")
            # Chasing phase code


            # TODO: What if they're not alone?
            # Cases to consider:
            # (1) Multiple singles that can not merge
            # (2) Multiple singles that can merge
            # (3) A cluster that can be merged with (need to write cluster class, which will have a list of positions rather than just one)
            #

            #Victor wrote pursue! Its in movingimg example though..

            # Need to write code for pursuing a piece and then we can call merge(p1, p2) with them both if they meet
            # Which will return a cluster if they are able to merge and False if they can't
            # That handles cases (1) and (2) ideally
            # Should we track failed merges? could help with case (1)

            # REVELATIONS:
            # we some way to communicate when a piece/group of pieces become(s) finished so they can be animated going in place
            # The cluster shouldn't be its own class: too complex. Lots of the behaviour assumes individual pieces
            # I just need some way of coupling the behaviour of pieces together: perhaps a "cluster" attribute that assigns each cluster a number (I DID THIS KINDA: SEE LINES 6 AND 36)
            # And when merging if a piece belongs to a cluster they join it, else they form a new one
            # Two merging clusters form a new cluster and each piece inside joins the new one (more complex, could just manually iterate through pieces but that's long)
            # Static var can keep track of how many clusters there are so they each have a unique ID
    
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

# If the merge succeeds (the two pieces belong next to each other) this returns True and makes the pieces form a cluster as described earlier
# Else this returns false
# Before calling this method make sure to change BOTH piece's self.attempted
def merge(p1, p2):
    raise NotImplementedError("Will need to handle merging pieces, pieces and clusters, and 2 clusters")
    # Example:
    # Imagine we have determined these two pieces should merge:
    # Also only handling the case where they are both single pieces here
    # if (p1.cluster == 0 and p2.cluster == 0):
    #     clusters += 1
    #     p1.cluster = clusters
    #     p2.cluster = clusters
