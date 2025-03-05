from Node import *
import json
import numpy as np

class MCTS:
    def __init__(self, game, args, turn):
        self.game = game
        self.args = args
        self.turn = turn
        
    def search(self, state, baghchalInforation, player):
        turn = player
        root = Node(self.game, self.args, state, player, baghchalInforation, self.turn)

        for _ in range(self.args['num_searches']):

            node = root

            while node.is_fully_expanded():
                node = node.select()

            
            value, is_terminal = self.game.is_terminal(
                node.state,
                node.baghchalInforation['capture_goat'],
                node.baghchalInforation['tigers'],
            )
        
            if not is_terminal:

                node = node.expand() 
                
                value = node.simulate()

            node.backpropagate(value)   

        best_action_count = 1
        best_action = None

        for child in root.children:
            if child.visit_count > best_action_count:
                best_action_count = child.visit_count
                best_action = child.action_taken

        return best_action
  