from StateDisplay import *

def AskForUser(moves, state, tigers, total_goats, goats_on_board,  baghchal, player, capture_goat):
    playername = 'Tiger' if player == -1 else 'Goat'
    users_moves = {}
    for move in moves:
            src, dest = move
            if src not in users_moves:
                users_moves[src] = []
            users_moves[src].append(move)
    users_positions = list(users_moves.keys())
    print(users_positions)
    while True:
            try:
                action = input("Choose a Position ( row, column): ")
                print("\n")
                x, y = map(int, action.split(','))

                if(x,y) in users_positions:
                    selected_goat = (x,y)

                    available_moves = [move[1] for move in users_moves[selected_goat]]

                    print(available_moves)
                    print('\n')

                    selected_position = input("Choose a Position to move (row, column): ")
                    print('\n')

                    move_x, move_y = map(int, selected_position.split(','))

                    if (move_x, move_y) in available_moves:
                        
                        print(f"Move to ({move_x}, {move_y}) is valid.")
                        print('\n')

                        pass_move  = [(x, y) , (move_x, move_y)]
                        print(pass_move, "pass_move")

                        print('\n')
                        print("Now board look like ")
                        print('\n')
                        print("You placed a at", "(", x, ",", y, ")")
                        state, total_goats, goats_on_board, capture_goat, tigers = baghchal.apply_move(state, player, total_goats, goats_on_board, move=pass_move, capture_goat=capture_goat, tigers=tigers)
                        stateDisplay(state)
                        print('\n')
                        return state, total_goats, goats_on_board, capture_goat, tigers

                    else:
                        print("Invalid move. Please choose a valid destination from the available moves.")
                        print('\n')

                    break
                else:
                    print("Invalid choice. Please select a valid tiger position.")
                    print('\n')

            except ValueError:
                print("Invalid input. Please enter coordinates in the format row,column (e.g., 0,1).")
                print('\n')
