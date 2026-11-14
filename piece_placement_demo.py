from piece import Piece
arr = [[-1]*5]*5

for piece in [Piece(15, False), Piece(1, False), Piece(3, True)]:
    arr = piece.initial_place(arr)

print(arr)
