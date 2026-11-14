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

