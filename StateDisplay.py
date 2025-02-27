import numpy as np

def stateDisplay(state):
    boardState =  np.full((5, 5), '.', dtype=object)
    for x in range(5):
        for y in range(5):
            if(state[x,y] == 1):
                boardState[x,y] = 'G'
            elif(state[x,y] == -1):
                boardState[x,y] = 'T'
            else:
                boardState[x, y] = '.'
    print(boardState)
