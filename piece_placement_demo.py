from piece import Piece
arr = [[-1, -1, -1, -1, -1],
       [-1, -1, -1, -1, -1],
       [-1, -1, -1, -1, -1],
       [-1, -1, -1, -1, -1],
       [-1, -1, -1, -1, -1]]


for piece in [Piece(15, False), Piece(1, False), Piece(3, True)]:
    arr = piece.initial_place(arr)

print(arr)
