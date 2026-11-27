import argparse
import math
import random
import statistics
import time

import numpy as np

from Baghchal import Baghchal
from ImplicitMCTS import ImplicitMinimaxMCTS
from MCTS import MCTS_GOAT, MCTS_TIGER


def play_game(game_number, args):
    game = Baghchal()
    tigers = [(0, 0), (0, 4), (4, 0), (4, 4)]
    state = game.get_initial_state(1, tigers, -1)
    info = {
        'total_goats': 20,
        'goats_on_board': 0,
        'capture_goat': 0,
        'tigers': tigers,
    }

    current_args = {
        'C': args.exploration,
        'num_searches': args.searches,
        'max_depth': args.rollout_depth,
    }
    baseline_goat = MCTS_GOAT(game, current_args)
    baseline_tiger = MCTS_TIGER(game, current_args)
    implicit = ImplicitMinimaxMCTS(
        game,
        current_args,
        alpha=args.alpha,
        heuristic_scale=args.heuristic_scale,
    )

    implicit_side = 1 if game_number % 2 == 0 else -1
    to_move = 1
    seen_positions = {}
    response_times = {'implicit': [], 'baseline': []}

    for ply in range(args.ply_limit):
        if info['capture_goat'] >= 5:
            winner = -1
            break
        if game.are_tiger_blocked(state, info['tigers']):
            winner = 1
            break

        position_key = (
            tuple(map(tuple, state)),
            to_move,
            info['total_goats'],
            info['goats_on_board'],
            info['capture_goat'],
        )
        seen_positions[position_key] = seen_positions.get(position_key, 0) + 1
        if seen_positions[position_key] >= 3:
            winner = 0
            break

        is_implicit_turn = to_move == implicit_side
        search_started = time.perf_counter()
        if is_implicit_turn:
            action = implicit.search(state, info, -to_move)
        elif to_move == 1:
            action = baseline_goat.search(state, info, -1)
        else:
            action = baseline_tiger.search(state, info, 1)
        search_type = 'implicit' if is_implicit_turn else 'baseline'
        response_times[search_type].append(
            (time.perf_counter() - search_started) * 1000
        )

        if action is None:
            winner = -to_move
            break

        state, info['total_goats'], info['goats_on_board'], info['capture_goat'], info['tigers'] = (
            game.apply_move(
                state,
                player=to_move,
                total_goats=info['total_goats'],
                goats_on_board=info['goats_on_board'],
                move=action,
                capture_goat=info['capture_goat'],
                tigers=info['tigers'],
            )
        )
        to_move = -to_move
    else:
        winner = 0
        ply = args.ply_limit

    result = 'draw' if winner == 0 else ('goats' if winner == 1 else 'tigers')
    return {
        'game': game_number + 1,
        'implicit_side': 'goats' if implicit_side == 1 else 'tigers',
        'winner': result,
        'implicit_result': (
            'draw' if winner == 0 else ('win' if winner == implicit_side else 'loss')
        ),
        'plies': ply,
        'goats_captured': info['capture_goat'],
        'response_times': response_times,
    }


def print_response_summary(name, samples):
    if not samples:
        print(f'{name} search time: no samples')
        return

    ordered = sorted(samples)
    p95_index = min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)
    print(
        f'{name} search time: n={len(samples)}, '
        f'mean={statistics.mean(samples):.2f} ms, '
        f'median={statistics.median(samples):.2f} ms, '
        f'p95={ordered[p95_index]:.2f} ms'
    )


def main():
    parser = argparse.ArgumentParser(
        description='Play implicit-minimax MCTS against the existing MCTS.'
    )
    parser.add_argument('--games', type=int, default=2)
    parser.add_argument('--searches', type=int, default=80)
    parser.add_argument('--rollout-depth', type=int, default=6)
    parser.add_argument('--ply-limit', type=int, default=120)
    parser.add_argument('--alpha', type=float, default=0.25)
    parser.add_argument('--heuristic-scale', type=float, default=400.0)
    parser.add_argument('--exploration', type=float, default=1.2)
    parser.add_argument('--seed', type=int, default=17)
    args = parser.parse_args()

    results = []
    response_times = {
        'implicit': [],
        'baseline': [],
        'implicit_goats': [],
        'implicit_tigers': [],
    }
    for game_number in range(args.games):
        random.seed(args.seed + game_number)
        np.random.seed(args.seed + game_number)
        result = play_game(game_number, args)
        results.append(result)
        response_times['implicit'].extend(result['response_times']['implicit'])
        response_times['baseline'].extend(result['response_times']['baseline'])
        implicit_side_key = f"implicit_{result['implicit_side']}"
        response_times[implicit_side_key].extend(
            result['response_times']['implicit']
        )
        print(
            f"Game {result['game']}: implicit as {result['implicit_side']} - "
            f"{result['implicit_result']} (game result: {result['winner']}, "
            f"{result['plies']} plies, {result['goats_captured']} captures)"
        )

    wins = sum(result['implicit_result'] == 'win' for result in results)
    losses = sum(result['implicit_result'] == 'loss' for result in results)
    draws = sum(result['implicit_result'] == 'draw' for result in results)
    print(f"Implicit MCTS total: {wins} wins, {losses} losses, {draws} draws")
    print_response_summary('Implicit MCTS', response_times['implicit'])
    print_response_summary('Baseline MCTS', response_times['baseline'])
    print_response_summary('Implicit as goats', response_times['implicit_goats'])
    print_response_summary('Implicit as tigers', response_times['implicit_tigers'])


if __name__ == '__main__':
    main()
