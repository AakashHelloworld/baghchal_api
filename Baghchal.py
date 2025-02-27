import numpy as np


# Class to represent the Baghchal game
class Baghchal:
    def __init__(self):
        self.row_count = 5
        self.column_cout = 5
        
    def get_initial_state(self, player,tigers,tiger ):
        state =  np.zeros((self.row_count, self.column_cout))
        for tiger_position in tigers:
            x, y = tiger_position
            state[x,y] = tiger   
        return state
    
    
    def apply_move(self, state, player,total_goats, goats_on_board, move, capture_goat, tigers):

        if player == 1:   
            if total_goats >0:
                x, y = move
                state[x, y] = 1 
                total_goats -=1
                goats_on_board +=1
            else:
                (src_x, src_y), (dest_x, dest_y) = move

                state[src_x, src_y] = 0
                state[dest_x, dest_y] = 1
        else:
            (src_x, src_y), (dest_x, dest_y) = move

            state[src_x, src_y] = 0

            if abs(src_x - dest_x) == 2 or abs(src_y - dest_y) == 2:
                mid_x, mid_y = (src_x + dest_x) // 2, (src_y + dest_y) // 2
                state[mid_x, mid_y] =0
                capture_goat +=1
                goats_on_board -=1
            state[dest_x, dest_y] = -1
            tigers = [(x, y) for x, y in tigers]
            for i, (x, y) in enumerate(tigers):
                if (x, y) == (src_x, src_y):
                    tigers[i] = (dest_x, dest_y)
                    break
        return state, total_goats, goats_on_board, capture_goat, tigers
    
    def get_possible_moves(self, state, player, total_goats, tigers):
        moves = []
        if player == 1:  # Goat   # gonna change
            # If goats are not on board, place them on empty cells
            if total_goats > 0:
                moves = [(x,y) for x in range(5) for y in range(5) if state[x,y] == 0]
            else:
                moves = self.get_moves_for_goats(state) 
        else:
            moves = self.get_moves_for_tigers(state, tigers)

        return moves
    
    def get_moves_for_goats(self, state):
        return [move for x in range(5) for y in range(5) if state[x,y] == 1 for move in self.get_adjacent_moves(state,x,y,jump=False)]
        
    
    def get_moves_for_tigers(self, state, tigers):
        return [move for x, y in tigers for move in self.get_adjacent_moves(state, x, y,  jump=True)]
    
    def get_adjacent_moves(self, state, x,y, jump=False,):

        directions = []

        if (x + y) % 2 != 0:
            directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        else:
            directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]
        
        moves = []

        for dx, dy in directions:
            nx, ny = x+dx, y+dy
            if 0 <= nx < 5 and 0 <= ny < 5 and state[nx, ny] == 0:
                moves.append(((x,y), (nx, ny)))
            if jump:
                jump_x, jump_y = x+ 2* dx, y + 2*dy
                if (
                    0 <= jump_x < 5
                    and 0 <= jump_y < 5
                    and state[nx, ny] == 1
                    and state[jump_x, jump_y] == 0
                ):
                    moves.append(((x, y), (jump_x, jump_y)))

        return moves

    def are_tiger_blocked(self,state, tigers):
        for tiger in tigers:
            x, y = tiger
            if self.get_adjacent_moves(state, x, y, jump=True):
                return False
        return True

    def tiger_blocked_num(self, state, tigers):
        count = 0
        for tiger in tigers:
            x, y = tiger
            if not self.get_adjacent_moves(state, x, y, jump=True):
                count += 1
        return count
   
    def is_terminal(self, state, captpure_goat, tigers):        
        if captpure_goat >= 5:     
            return 1, True
        if self.are_tiger_blocked(state, tigers):
            return 1, True
        
        return 0, False


    def get_opponent(self, player):
        return -player
    
    def get_opponent_value(self, value):
        return -value
    
    def change_perspective(self, state, player):
        return state* player
    
