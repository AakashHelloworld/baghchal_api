from Baghchal import *
from StateDisplay import *
from ClearTerminal import *
from AskForUser import *
from MCTS import *


# 1 for Goat and -1 for Tiger Always

baghchal = Baghchal()
player = 1
goat = 1
tiger = -1

args = {
    'C': 1.2,
    'num_searches': 30000,
    'max_depth' : 10
}



mcts = MCTS(baghchal, args)
tigers = [(0, 0), (0, 4), (4, 0), (4, 4)]
state =  baghchal.get_initial_state(player, tigers, tiger)
total_goats = 20
goats_on_board = 0
capture_goat =0



while True:
    stateDisplay(state)
    print('\n')
    moves = baghchal.get_possible_moves(state, player, total_goats, tigers)
    if not moves:
         print(f'No moves available for {player}')
         print('\n')
    if player == 1 and total_goats > 0:
        print("Place a goat in one of the available positions: ")
        print('\n')
        print(moves)
        print('\n')
        while True:
            try:
                action = input("Choose a move (row, column): ")
                print('\n')
                x, y = map(int, action.split(','))
                if (x, y) in moves:
                    move = [x,y]
                    state, total_goats, goats_on_board, capture_goat, tigers = baghchal.apply_move(state, player, total_goats, goats_on_board, move, capture_goat, tigers)
                    print("Now board look like ")
                    print('\n')
                    stateDisplay(state)
                    print('\n')
                    break
                    
                else:
                    print("Invalid move. Please choose a valid position.")
                    print('\n')

            except ValueError:
                print("Invalid input. Please enter coordinates in the format row,column (e.g., 0,1).")
                print('\n')
    elif player == 1 and total_goats == 0:
        print("Choose a Goat to move:")
        print('\n')
        state, total_goats, goats_on_board, capture_goat, tigers = AskForUser(moves, state, tigers, total_goats, goats_on_board,  baghchal, player, capture_goat)

    elif player == -1:
        baghchalInforation ={
            'tigers' : tigers.copy(),
            'total_goats': total_goats,
            'goats_on_board': goats_on_board,
            'capture_goat':capture_goat
        }
        
        mcts_probs = mcts.search(state.copy(), baghchalInforation, 1)

        state, total_goats, goats_on_board, capture_goat, tigers = baghchal.apply_move(state, player, total_goats, goats_on_board, move=mcts_probs, capture_goat=capture_goat, tigers=tigers)    

        stateDisplay(state)
    win, winner = baghchal.is_terminal(state, capture_goat, tigers)
    if(win):
        ClearTerminal()
        winner = 'Goat' if player == 1 else 'Tiger'
        stateDisplay(state)
        print(".............:Winner:.....................")
        print("..............", winner, ".............")
        break
    player = baghchal.get_opponent(player)
