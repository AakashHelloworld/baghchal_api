import math
import random

from NodeGoat import NodeGoat


class _ImplicitNode:
    def __init__(self, search, state, info, to_move, parent=None, action=None):
        self.search = search
        self.game = search.game
        self.state = state
        self.info = info
        self.to_move = to_move
        self.parent = parent
        self.action = action
        self.children = []
        self.visit_count = 0
        self.value_sum = 0.0
        self.terminal_winner = search._terminal_winner(state, info)

        if self.terminal_winner is not None:
            self.unexpanded_moves = []
            self.heuristic_value = search._winner_value(self.terminal_winner, to_move)
        else:
            self.unexpanded_moves = self.game.get_possible_moves(
                state, to_move, info['total_goats'], info['tigers']
            )
            if self.unexpanded_moves:
                self.heuristic_value = search._heuristic_value(state, info, to_move)
            else:
                self.terminal_winner = -to_move
                self.heuristic_value = -1.0

        self.minimax_value = self.heuristic_value

    def expand(self):
        move_index = random.randrange(len(self.unexpanded_moves))
        action = self.unexpanded_moves.pop(move_index)
        child_state = self.state.copy()
        child_state, total_goats, goats_on_board, capture_goat, tigers = self.game.apply_move(
            child_state,
            player=self.to_move,
            total_goats=self.info['total_goats'],
            goats_on_board=self.info['goats_on_board'],
            move=action,
            capture_goat=self.info['capture_goat'],
            tigers=self.info['tigers'],
        )
        child_info = {
            'total_goats': total_goats,
            'goats_on_board': goats_on_board,
            'capture_goat': capture_goat,
            'tigers': tigers.copy(),
        }
        child = _ImplicitNode(
            self.search,
            child_state,
            child_info,
            -self.to_move,
            parent=self,
            action=action,
        )
        self.children.append(child)
        return child


class ImplicitMinimaxMCTS:
    """MCTS with separate Monte Carlo and implicit minimax value backups."""

    def __init__(self, game, args, alpha=0.25, heuristic_scale=400.0):
        if not 0.0 <= alpha <= 1.0:
            raise ValueError('alpha must be between 0 and 1')
        if heuristic_scale <= 0:
            raise ValueError('heuristic_scale must be positive')

        self.game = game
        self.args = args
        self.alpha = alpha
        self.heuristic_scale = heuristic_scale

    def search(self, state, baghchal_information, player):
        """Return a move using the existing API convention: to_move is -player."""
        root = _ImplicitNode(
            self,
            state.copy(),
            {
                **baghchal_information,
                'tigers': baghchal_information['tigers'].copy(),
            },
            to_move=-player,
        )
        if root.terminal_winner is not None:
            return None

        for _ in range(self.args['num_searches']):
            node = root
            while not node.unexpanded_moves and node.children:
                node = self._select_child(node)

            if node.unexpanded_moves:
                node = node.expand()

            value = self._rollout(node)
            self._backpropagate(node, value)

        if not root.children:
            return None
        return max(root.children, key=lambda child: child.visit_count).action

    def _select_child(self, node):
        exploration = self.args['C']
        parent_visits = max(1, node.visit_count)

        def score(child):
            monte_carlo_value = -child.value_sum / child.visit_count
            minimax_value = -child.minimax_value
            blended_value = (
                (1.0 - self.alpha) * monte_carlo_value
                + self.alpha * minimax_value
            )
            exploration_value = exploration * math.sqrt(
                math.log(parent_visits) / child.visit_count
            )
            return blended_value + exploration_value

        return max(node.children, key=score)

    def _backpropagate(self, node, value):
        current = node
        while current is not None:
            current.visit_count += 1
            current.value_sum += value
            current = current.parent
            value = -value

        current = node
        while current is not None:
            if current.terminal_winner is not None:
                current.minimax_value = self._winner_value(
                    current.terminal_winner, current.to_move
                )
            elif current.children:
                current.minimax_value = max(
                    -child.minimax_value for child in current.children
                )
            else:
                current.minimax_value = current.heuristic_value
            current = current.parent

    def _rollout(self, node):
        state = node.state.copy()
        info = {
            **node.info,
            'tigers': node.info['tigers'].copy(),
        }
        to_move = node.to_move
        rollout_player = node.to_move
        seen_positions = set()

        for _ in range(self.args['max_depth']):
            winner = self._terminal_winner(state, info)
            if winner is not None:
                return self._winner_value(winner, rollout_player)

            position_key = (
                tuple(map(tuple, state)),
                to_move,
                info['total_goats'],
                info['goats_on_board'],
                info['capture_goat'],
            )
            if position_key in seen_positions:
                return 0.0
            seen_positions.add(position_key)

            moves = self.game.get_possible_moves(
                state, to_move, info['total_goats'], info['tigers']
            )
            if not moves:
                return self._winner_value(-to_move, rollout_player)

            action = random.choice(moves)
            state, total_goats, goats_on_board, capture_goat, tigers = (
                self.game.apply_move(
                    state,
                    player=to_move,
                    total_goats=info['total_goats'],
                    goats_on_board=info['goats_on_board'],
                    move=action,
                    capture_goat=info['capture_goat'],
                    tigers=info['tigers'],
                )
            )
            info = {
                'total_goats': total_goats,
                'goats_on_board': goats_on_board,
                'capture_goat': capture_goat,
                'tigers': tigers,
            }
            to_move = -to_move

        winner = self._terminal_winner(state, info)
        if winner is not None:
            return self._winner_value(winner, rollout_player)
        return self._heuristic_value(state, info, rollout_player)

    def _heuristic_value(self, state, info, player):
        # NodeGoat's score is tiger-positive when evaluated with player=-1.
        evaluator = NodeGoat(self.game, self.args, state, -1, info)
        tiger_value = math.tanh(
            evaluator.evaluate_when_goat() / self.heuristic_scale
        )
        return tiger_value * -player

    def _terminal_winner(self, state, info):
        if info['capture_goat'] >= 5:
            return -1
        if self.game.are_tiger_blocked(state, info['tigers']):
            return 1
        return None

    @staticmethod
    def _winner_value(winner, player):
        return 1.0 if winner == player else -1.0
