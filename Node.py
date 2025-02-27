import numpy as np
import math
import random
from StateDisplay import *
import json as JSON

class Node:
    def __init__(self, game, args, state, player, baghchalInforation, parent=None, action_taken=None):
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
    
    def evaluate(self):
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
        }, parent=self, action_taken=action)

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
        return self.evaluate()

    def backpropagate(self, value):
        self.value_sum += value
        self.visit_count += 1
        if self.parent is not None:
            self.parent.backpropagate(-value)
