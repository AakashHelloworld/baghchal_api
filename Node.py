import numpy as np
import math
import random
from StateDisplay import *
import json as JSON

class Node:
    def __init__(self, game, args, state, player, baghchalInforation, turn,  parent=None, action_taken=None):
        self.game = game
        self.args = args
        self.state = state
        self.parent = parent
        self.action_taken = action_taken
        self.player = player
        self.children = []
        self.baghchalInforation = baghchalInforation
        self.visit_count = 0
        self.value_sum = 0
        self.expandable_moves = game.get_possible_moves(state, -player, baghchalInforation['total_goats'], baghchalInforation['tigers'])
        self.turn = turn

        # 🔹 Track position history to prevent repeated states
        self.position_history = {} if parent is None else dict(parent.position_history)

        # 🔹 Track stagnation (if no progress, game might be a draw)
        self.moves_without_progress = parent.moves_without_progress if parent else 0
        

    def calculate_distance(self, pos1, pos2):
        return math.sqrt((pos1[0]-pos2[0])**2 + (pos1[1]-pos2[1])**2)
    def is_fully_expanded(self):
        return len(self.expandable_moves) == 0 and len(self.children) > 0

    def select(self):
        best_child = None
        best_ucb = -np.inf

        for child in self.children:
            ucb = self.get_ucb(child)
            if ucb > best_ucb:
                best_child = child
                best_ucb = ucb

        return best_child
    
    def to_react_d3_tree(self):
        """Convert node and its children into react-d3-tree format, including state."""
        return {
            "name": str(self.action_taken) if self.action_taken else "Root",
            "attributes": {
                "ucb": self.get_ucb(self),
                "visit_count": self.visit_count,
                "state": self.state
            },
            "children": [child.to_react_d3_tree() for child in self.children] if self.children else []
        }
    
    def evaluate_when_goat(self):
        # Base score
        score = 0
        
        # HIGHEST PRIORITY: Captured goats
        score += self.baghchalInforation['capture_goat'] * 150
        
        # SECOND PRIORITY: Potential captures
        potential_captures = 0
        for tiger_pos in self.baghchalInforation['tigers']:
            tx, ty = tiger_pos
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]:

                # Check adjacent space
                nx, ny = tx + dx, ty + dy
                if 0 <= nx < 5 and 0 <= ny < 5 and self.state[nx, ny] == 1:  # Goat in adjacent space
                    # Check space beyond for potential capture
                    jx, jy = tx + 2*dx, ty + 2*dy
                    if 0 <= jx < 5 and 0 <= jy < 5 and self.state[jx, jy] == 0:  # Empty space beyond
                        potential_captures += 1
        
        score += potential_captures * 50  # Very high reward for potential captures
        
        # THIRD PRIORITY: Tiger mobility
        mobile_tigers = 4 - self.game.tiger_blocked_num(self.state.copy(), self.baghchalInforation['tigers'].copy())
        score += mobile_tigers * 30
        
        # FOURTH PRIORITY: Position only matters if no captures are possible
        central_positions = [(2, 2)]
        diagonal_positions = [(1, 1), (3, 1), (1, 3), (3, 3)]
        edge_positions = [(0, 0), (4, 0), (0, 4), (4, 4)]
        
        center_tigers = sum(1 for pos in self.baghchalInforation['tigers'] if pos in central_positions)
        diagonal_tigers = sum(1 for pos in self.baghchalInforation['tigers'] if pos in diagonal_positions)
        corner_tigers = sum(1 for pos in self.baghchalInforation['tigers'] if pos in edge_positions)
        
        # Reduce the importance of positional play compared to captures
        score += center_tigers * 10
        score += diagonal_tigers * 5
        score += corner_tigers * 2
        
        # GOAT METRICS
        goat_positions = [(x, y) for x in range(5) for y in range(5) if self.state[x, y] == 1]
        
        # Goats on board and placement are important for goats
        goats_on_board = self.baghchalInforation['goats_on_board']
        score -= goats_on_board * 80
        
        goats_remaining = self.baghchalInforation['total_goats']
        score -= goats_remaining * 10
        
        # Check if goats are creating blocking formations around tigers
        tigers_being_surrounded = 0
        for tiger_pos in self.baghchalInforation['tigers']:
            tx, ty = tiger_pos
            goat_neighbors = 0
            possible_moves = 0
            
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]:
                # Only check valid directions
                if (tx + ty) % 2 != 0 and dx != 0 and dy != 0:
                    continue
                    
                nx, ny = tx + dx, ty + dy
                if 0 <= nx < 5 and 0 <= ny < 5:
                    possible_moves += 1
                    if self.state[nx, ny] == 1:  # Goat
                        goat_neighbors += 1
            
            # Calculate how surrounded this tiger is
            if possible_moves > 0:
                tiger_surrounded_ratio = goat_neighbors / possible_moves
                tigers_being_surrounded += tiger_surrounded_ratio
        
        # Reduce score for surrounded tigers (good for goats)
        score -= tigers_being_surrounded * 25
        
        # Special case: IMMEDIATE CAPTURE opportunity takes absolute precedence
        if potential_captures > 0:
            # Add a huge bonus to ensure capturing is always preferred
            score += 1000
        
        # Return score from perspective of current player
        return score * -self.player
    
    def evaluate_when_tiger(self):
        score = 0

        tiger_alive = 4 - self.game.tiger_blocked_num(self.state.copy(), self.baghchalInforation['tigers'].copy())
        score += tiger_alive * 10 

        score += self.baghchalInforation['capture_goat'] * 40  # Goats captured

        # Best tiger positions (central spots)
        best_positions = [(1, 1), (3, 1), (1, 3), (3, 3), (2, 2)]
        best_tiger_position_score = sum(1 for pos in self.baghchalInforation['tigers'] if pos in best_positions)
        score += best_tiger_position_score * 10  # Reward tigers in strategic positions

        # Goat clustering (punish dispersion)
        goat_positions = [(x, y) for x in range(5) for y in range(5) if self.state[x, y] == 1]
        goat_cluster_score = sum(self.calculate_distance(g1, g2) for g1 in goat_positions for g2 in goat_positions)
        score -= goat_cluster_score * 30  # Penalize goats for spreading out

        # Goat metrics
        goats_remaining = self.baghchalInforation['total_goats'] - self.baghchalInforation['goats_on_board'] - self.baghchalInforation['capture_goat']
        score -= goats_remaining * 10  # Penalize goats left off the board

        # Goat-tiger distance (penalize goats for being close to tigers)
        goat_tiger_proximity = 0
        for (gx, gy) in goat_positions:
            for (tx, ty) in self.baghchalInforation['tigers']:
                goat_tiger_proximity += abs(gx - tx) + abs(gy - ty)  # Manhattan distance

        score -= goat_tiger_proximity * 10  # Penalize goats being too close to tigers


        return score  * - self.player  # Perspective scaling
    
    def get_ucb(self, child):
        q_value = child.value_sum / child.visit_count 
        return q_value + self.args['C'] * math.sqrt(math.log(self.visit_count) / (child.visit_count ))

    def expand(self):
        action = self.expandable_moves.pop(random.randint(0, len(self.expandable_moves) - 1))
        child_state = self.state.copy()
        next_player = -self.player

        child_state, total_goats, goats_on_board, capture_goat, tigers = self.game.apply_move(
            child_state,
            player=next_player,
            total_goats=self.baghchalInforation['total_goats'],
            goats_on_board=self.baghchalInforation['goats_on_board'],
            move=action,
            capture_goat=self.baghchalInforation['capture_goat'],
            tigers=self.baghchalInforation['tigers'],
        )

        state_key = tuple(map(tuple, child_state))  
        new_position_history = dict(self.position_history)
        new_position_history[state_key] = new_position_history.get(state_key, 0) + 1

        if new_position_history[state_key] >= 3:
            self.moves_without_progress += 1  

        child = Node(self.game, self.args, child_state, next_player, {
            'total_goats': total_goats,
            'goats_on_board': goats_on_board,
            'capture_goat': capture_goat,
            'tigers': tigers.copy()
        }, turn=self.turn, parent=self, action_taken=action)

        # 🔹 Carry forward position history and stagnation
        child.position_history = new_position_history
        child.moves_without_progress = self.moves_without_progress

        self.children.append(child)
        return child

    def simulate(self):

        depth = 0
        max_depth = 10  # Prevent infinite simulations

        state = self.state.copy()
        baghchal = self.game  # Access game logic

        # Clone game state variables
        sim_goats = self.baghchalInforation['total_goats']
        sim_captured = self.baghchalInforation['capture_goat']
        sim_tigers = self.baghchalInforation['tigers'].copy()
        current_player = -self.player  # Start with opponent

        position_history = dict(self.position_history)  # Clone history

        while depth < max_depth:
            # Check if the game is over
            win, is_terminal = baghchal.is_terminal(state, sim_captured, sim_tigers)
            if is_terminal:
                return win * self.player  # Return a positive score for the winning player

            state_key = tuple(map(tuple, state))

            position_history[state_key] = position_history.get(state_key, 0) + 1
          
            if position_history[state_key] >= 3:
                return 0  # Draw

            # Get valid moves
            valid_moves = baghchal.get_possible_moves(state, current_player, sim_goats, sim_tigers)
            if not valid_moves:
                break  # No moves, stop simulation

            # Pick a random move
            action = random.choice(valid_moves)

            # Apply move
            prev_goat_captured = sim_captured
            state, sim_goats, _, sim_captured, sim_tigers = baghchal.apply_move(
                state, current_player, sim_goats, 0, action, sim_captured, sim_tigers
            )

            # 🔹 Stagnation Rule: If no goat was captured and tigers still have moves, increase stagnation
            if sim_captured == prev_goat_captured:
                self.moves_without_progress += 1
                if self.moves_without_progress >= 50:  # Set limit to declare a draw
                    return 0

            # Switch player
            current_player = -current_player
            depth += 1

        # If no winner, return evaluation score
        if(self.turn == -1):
            return self.evaluate_when_goat()
        else:
            return self.evaluate_when_tiger()

    def backpropagate(self, value):
        self.value_sum += value
        self.visit_count += 1
        if self.parent is not None:
            self.parent.backpropagate(-value)
