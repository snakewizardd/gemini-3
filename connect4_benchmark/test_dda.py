"""
DDA Connect 4 Win Rate Test
===========================

Tests the DDA algorithm against random opponents to verify it achieves
a high win rate as expected for a well-tuned algorithm.
"""

import numpy as np
import random
from dda_connect4 import DDAConnect4


def play_game(dda_plays_first: bool = True) -> tuple:
    """
    Play a full game between DDA and random opponent.
    
    Returns: (winner, move_count, rigidity_history)
        winner: 1 = DDA, 2 = Random, None = draw
    """
    board = np.zeros((6, 7), dtype=int)
    dda = DDAConnect4()
    
    dda_player = 1 if dda_plays_first else 2
    random_player = 2 if dda_plays_first else 1
    
    current_player = 1  # Player 1 always starts
    move_count = 0
    rigidity_history = []
    
    while True:
        # Get valid moves
        valid_moves = [c for c in range(7) if board[0, c] == 0]
        if not valid_moves:
            return (None, move_count, rigidity_history)  # Draw
        
        # Get move
        if current_player == dda_player:
            col = dda.decide(board, current_player, valid_moves)
            rigidity_history.append(dda.rho_t)
        else:
            col = random.choice(valid_moves)
            dda.observe_opponent(col)
        
        # Make move
        for row in range(5, -1, -1):
            if board[row, col] == 0:
                board[row, col] = current_player
                break
        
        move_count += 1
        
        # Check win
        if check_win(board, row, col, current_player):
            winner = 1 if current_player == dda_player else 2
            return (winner, move_count, rigidity_history)
        
        # Switch player
        current_player = 3 - current_player


def check_win(board: np.ndarray, row: int, col: int, player: int) -> bool:
    """Check if move at (row, col) wins for player."""
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
    
    for dr, dc in directions:
        count = 1
        for sign in [1, -1]:
            r, c = row + dr * sign, col + dc * sign
            while (0 <= r < 6 and 0 <= c < 7 and board[r, c] == player):
                count += 1
                r += dr * sign
                c += dc * sign
        if count >= 4:
            return True
    return False


def run_benchmark(num_games: int = 100):
    """Run full benchmark suite."""
    print("=" * 60)
    print("DDA Connect 4 — Win Rate Benchmark")
    print("=" * 60)
    
    results = {"dda_wins": 0, "random_wins": 0, "draws": 0}
    total_moves = 0
    rigidity_samples = []
    
    for i in range(num_games):
        # Alternate who plays first
        dda_first = (i % 2 == 0)
        winner, moves, rigidity = play_game(dda_plays_first=dda_first)
        
        total_moves += moves
        rigidity_samples.extend(rigidity)
        
        if winner == 1:
            results["dda_wins"] += 1
        elif winner == 2:
            results["random_wins"] += 1
        else:
            results["draws"] += 1
        
        # Progress indicator
        if (i + 1) % 10 == 0:
            print(f"  Completed {i+1}/{num_games} games...")
    
    # Calculate stats
    win_rate = results["dda_wins"] / num_games * 100
    avg_moves = total_moves / num_games
    avg_rigidity = np.mean(rigidity_samples) if rigidity_samples else 0
    max_rigidity = np.max(rigidity_samples) if rigidity_samples else 0
    
    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Games played:      {num_games}")
    print(f"DDA wins:          {results['dda_wins']} ({win_rate:.1f}%)")
    print(f"Random wins:       {results['random_wins']} ({results['random_wins']/num_games*100:.1f}%)")
    print(f"Draws:             {results['draws']}")
    print()
    print(f"Avg game length:   {avg_moves:.1f} moves")
    print(f"Avg rigidity:      {avg_rigidity:.3f}")
    print(f"Max rigidity:      {max_rigidity:.3f}")
    print("=" * 60)
    
    # Validate expected performance
    if win_rate >= 70:
        print("✅ PASS: DDA achieves >70% win rate against random")
    else:
        print("⚠️  WARN: Win rate below 70% — consider tuning parameters")
    
    return results


if __name__ == "__main__":
    run_benchmark(num_games=50)
