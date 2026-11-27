# Bagh-Chal: Depth-Limited Monte Carlo Tree Search

## Research overview

This project explores a practical search strategy for **Bagh-Chal**, the
traditional Nepalese strategy game in which four tigers hunt a larger group of
goats. Rather than requiring every Monte Carlo Tree Search (MCTS) rollout to
reach a win or loss, the search uses a configurable depth limit. When a rollout
reaches that limit without ending the game, a hand-designed heuristic evaluates
the resulting position and supplies a shaped reward to MCTS.

This repository is an experimental implementation, not a report of benchmarked
playing strength. The heuristic weights are manually selected and have not
been established through a controlled tournament or statistical evaluation.

## Game and state representation

The board is represented as a 5 × 5 NumPy array:

Game metadata is tracked alongside the board, including goats left to place,
goats on the board, goats captured, and tiger coordinates. Goats first enter
the board by placement and later move along available adjacent connections.
Tigers move similarly and can capture goats by jumping over them. In the
current terminal check, five captured goats or all tigers being blocked ends
the game.

## Methodology

### 1. MCTS for candidate moves

For each move decision, MCTS builds a search tree from the current position.
It repeatedly selects a promising child using an Upper Confidence Bound (UCB)
score, expands an untried move, simulates from the resulting position, and
backpropagates the returned value through the tree. The move with the greatest
visit count is selected after the configured number of searches.

The current search settings are defined in `main.py`: `C = 1.2`,
`num_searches = 10000`, and `max_depth = 12`. These are implementation
defaults, not experimentally optimized parameters.

### 2. Bounded simulation instead of full-game rollouts

A rollout starts from an expanded node and alternates players, selecting a
legal move at random. It stops early if a terminal position is reached. It also
stops when the configured `max_depth` number of rollout plies is reached. This
bound limits the work spent simulating a single branch and avoids requiring a
random rollout to play an entire game before returning a value.

Repetition and prolonged lack of progress are treated as draws by the rollout
logic and return `0`. If the rollout reaches its depth limit (or has no legal
move to continue with) while the position remains non-terminal, it evaluates
the resulting position heuristically instead of returning a binary
win-or-loss value.

### 3. Heuristic reward at the cutoff

The heuristic returns a signed scalar score. Its purpose is to rank positions
and provide MCTS with a learning signal before a terminal result is available;
it is not a probability of winning. The Goat-oriented evaluator considers
features including:

- tiger mobility and captured goats;
- tiger control of central, diagonal, and corner intersections;
- immediate potential captures;
- goat defensive groupings and board control;
- goats placed versus goats still awaiting placement; and
- separation between tigers.

The Tiger-oriented evaluator also defines a weighted score using tiger
mobility, captures, positional control, goat clustering, goats awaiting
placement, and goat–tiger distance. These manually chosen terms encode
strategic intuitions as a first approximation. Their weights and even the
usefulness of individual features should be tested empirically before drawing
claims about playing strength.

At terminal positions the rollout returns a terminal value; at non-terminal
cutoffs it returns the heuristic value. Thus, the search can distinguish
positions that appear strategically favorable even when no simulated win or
loss has occurred within the rollout horizon.

## Algorithm sketch

```text
for each MCTS search:
    select a tree node using UCB
    expand one legal action
    simulate from the expanded position for at most max_depth plies
        if a terminal position is reached:
            return terminal value
        if repetition or stagnation is detected:
            return draw value (0)
        if the depth limit is reached:
            return heuristic(position)
    backpropagate the returned value, alternating its sign by tree level
choose the root action with the highest visit count
```

In this design, `max_depth` is a rollout horizon (plies), not a limit on the
number of MCTS tree levels or on the total number of searches.

## Experimental considerations

To evaluate this approach rigorously, compare it against full-game rollouts
and simpler baselines under the same compute budget. Useful measurements
include win rate by side, average decision time, rollout length, and outcomes
across different depth limits and heuristic-weight settings. Use multiple
random seeds and report uncertainty; a single game or anecdotal result is not
evidence of an improvement.

The current implementation has several limitations to account for when
interpreting results:

- Rollout moves are selected randomly, so simulation quality depends on the
  rollout policy as well as the cutoff evaluator.
- Heuristic values are hand-weighted, and the Goat and Tiger evaluators are
  not calibrated to a shared scale.
- Repetition and stagnation handling are simplified and should be validated
  against the complete rules used for any evaluation.
- The search and evaluator wiring should be checked when comparing both sides;
  in particular, `MCTS_TIGER` currently creates a `NodeGoat` root, although a
  separate `NodeTiger` evaluator exists.
- Results from the included match script are exploratory only; the script does
  not constitute a statistically meaningful benchmark.

## Implicit minimax experiment

`ImplicitMCTS.py` contains a separate MCTS implementation based on Lanctot et
al.'s implicit minimax backups. It keeps rollout estimates and heuristic
minimax values as separate statistics. At a selection step, it blends the
child's Monte Carlo value with its backed-up minimax value:

```text
selection value = (1 - alpha) * Q + alpha * V + exploration
```

The minimax value is backed up from expanded children, while rollout values
continue to be averaged independently. The current heuristic is mapped through
`tanh(score / heuristic_scale)` so its values fit the same `[-1, 1]` range as
win/loss outcomes. The defaults are `alpha = 0.25` and
`heuristic_scale = 400`; these are starting points for experiments, not tuned
parameters. The implicit implementation follows the existing search method's
player argument convention.

Use `play_implicit_match.py` to play the new implementation against the
existing MCTS, switching the implicit player between goats and tigers across
games:

```bash
uv run python play_implicit_match.py --games 100 --searches 80 --rollout-depth 6
```

The 100-game exploratory comparison and search-time measurements are recorded
below. Results are not evidence of a general strength improvement: the game
limit creates many draws, and the existing tiger search currently instantiates
`NodeGoat`, so the match compares against the actual current wiring rather than
the separate `NodeTiger` evaluator.

Reference: Marc Lanctot, Mark H. M. Winands, Tom Pepels, and Nathan R.
Sturtevant, “Monte Carlo Tree Search with Heuristic Evaluations using Implicit
Minimax Backups,” [arXiv:1406.0486](https://arxiv.org/abs/1406.0486).

## Development history and preliminary results

This section records the project's development stages and the available
evidence. The early observations below are qualitative; only the implicit
MCTS-versus-current-MCTS experiment has reproducible game and timing data.

### Stage 1: conventional MCTS

The initial approach used conventional MCTS rollouts that continued toward
terminal outcomes. At the configured search volume, completing a move took too
long for a responsive live game. No per-move timing log was retained for this
version, so its latency cannot be compared numerically with the later versions.

### Stage 2: depth-limited rollouts and heuristic evaluation

The next version bounded each rollout with `max_depth` and evaluated
non-terminal positions with a hand-designed heuristic instead of waiting for a
win or loss. This reduced the work needed for a move and made live gameplay
noticeably more responsive. Informal human play also suggested improved move
quality, but those plays were not conducted as a controlled or recorded
experiment. No numeric latency or win-rate result is available for this stage.

### Stage 3: implicit minimax backups

The implicit implementation keeps Monte Carlo rollout estimates separate from
heuristic minimax values. It blends the two during selection, with `alpha =
0.25`, and normalizes the heuristic to `[-1, 1]` using
`tanh(score / 400)`. This avoids letting the raw heuristic scale directly
dominate the rollout estimate, while retaining the exploration term.

### 100-game comparison

The match runner alternated which side used implicit MCTS and used the
following settings for both players:

| Setting | Value |
| --- | ---: |
| Games | 100 (50 as goats, 50 as tigers) |
| MCTS searches per decision | 80 |
| Rollout depth | 6 plies |
| Exploration constant | 1.2 |
| Implicit minimax weight (`alpha`) | 0.25 |
| Heuristic scale | 400 |
| Maximum game length | 120 plies |
| Seed | 17 |

| Implicit player's side | Wins | Draws | Losses |
| --- | ---: | ---: | ---: |
| Goats (50 games) | 4 | 45 | 1 |
| Tigers (50 games) | 46 | 2 | 2 |
| **Total** | **50** | **47** | **3** |

Draws include games reaching the 120-ply cap as well as repetition draws. The
strongly different results by side mean the overall record should not be read
as evidence that implicit MCTS is uniformly stronger. In particular, implicit
MCTS won most games as tigers, while most games as goats were drawn.

### Search response time

The same 100-game run timed each call to `search()` with Python's
`perf_counter`; these measurements cover search computation only, not HTTP,
network, or UI overhead. The local run used Python 3.13.13 and 80 searches per
decision.

| Search implementation / side | Decisions | Mean | Median | 95th percentile |
| --- | ---: | ---: | ---: | ---: |
| Implicit MCTS, both sides | 3,852 | 24.53 ms | 23.55 ms | 31.77 ms |
| Implicit MCTS as goats | 2,870 | 24.83 ms | 24.18 ms | 31.39 ms |
| Implicit MCTS as tigers | 982 | 23.67 ms | 22.20 ms | 32.03 ms |
| Current depth-limited MCTS baseline | 3,849 | 17.96 ms | 17.01 ms | 23.08 ms |

Under these settings, implicit MCTS took about 37% longer on average per
decision than the current depth-limited baseline. The implicit search is still
in the tens-of-milliseconds range locally, but the measurement is
machine-dependent. This comparison does not provide a timing for the original
full-rollout version from Stage 1.

### Conclusion and next directions

Depth-limited heuristic evaluation addressed the practical response-time
problem reported with the original full-rollout approach and made live play
possible. The informal human feedback is encouraging but not controlled
evidence. Implicit minimax backups provide a distinct, bounded-value search
alternative; in the 100-game run they added modest per-decision cost and showed
a pronounced side-dependent result, with many draws.

The next experiments should:

1. Validate terminal outcomes, repetition handling, legal moves, and draw
   rules before interpreting win rates.
2. Connect `MCTS_TIGER` to the intended tiger evaluator, or deliberately use a
   single shared evaluator for both players.
3. Compare full rollouts, depth-limited heuristic MCTS, and implicit MCTS on
   identical seeds and opening states, with equal compute or wall-clock
   budgets.
4. Tune `alpha`, heuristic scaling, rollout depth, and search count on separate
   development games, then report results on held-out games with uncertainty.
5. Record human-play protocols and end-to-end UI response times separately
   from the search-only timings above.

## Running the project

The project requires Python 3.13 or newer. Install the dependencies declared
in `pyproject.toml`, then run the FastAPI application with Uvicorn:

```bash
uv sync
uv run uvicorn main:app --reload
```

This section is only a minimal way to launch the implementation; the focus of
this README is the search methodology rather than the HTTP interface.

## Project files

- `Baghchal.py` — board transitions, legal-move generation, and terminal checks.
- `MCTS.py` — MCTS search entry points for the two players.
- `NodeGoat.py` and `NodeTiger.py` — tree-node logic, rollout simulation, and
  heuristic evaluation.
- `main.py` — application setup and the default search configuration.
