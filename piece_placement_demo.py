from piece import Piece
p = Piece(0, False)
arr = [[]*5]*5

for piece in [p, Piece(1, False), Piece(3, True)]:
    arr = piece.initial_place(arr)

print(arr)
