<<<<<<< HEAD
cd from piece import Piece
arr = [[-1]*5]*5
=======
from piece import Piece
arr = [[-1, -1, -1, -1, -1],
       [-1, -1, -1, -1, -1],
       [-1, -1, -1, -1, -1],
       [-1, -1, -1, -1, -1],
       [-1, -1, -1, -1, -1]]

>>>>>>> a7df6cc94dad76bd4cbf9e1a69c608612a9e8491

for piece in [Piece(15, False), Piece(1, False), Piece(3, True)]:
    arr = piece.initial_place(arr)

print(arr)
