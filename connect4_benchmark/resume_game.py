"""
Resume a crashed Connect 4 game from the current board state.
Just edit the BOARD array below to match your game.
"""

from game.board import Connect4
from game.renderer import BoardRenderer
from model_interfaces.manual_model import ManualModel

# ============================================================
# EDIT THIS TO MATCH YOUR CURRENT BOARD STATE
# Use: 0 = empty, 1 = RED, 2 = YELLOW
# Row 0 is TOP, Row 5 is BOTTOM
# ============================================================

BOARD = [
    [0, 0, 0, 0, 0, 0, 0],  # Row 0 (top)
    [0, 0, 0, 2, 0, 0, 0],  # Row 1
    [0, 0, 0, 1, 1, 0, 0],  # Row 2
    [0, 2, 2, 2, 1, 0, 0],  # Row 3
    [2, 1, 2, 2, 1, 2, 0],  # Row 4
    [1, 1, 1, 2, 1, 2, 2],  # Row 5 (bottom)
]

# Whose turn is it? (1 = RED, 2 = YELLOW)
CURRENT_PLAYER = 2  # YELLOW's turn (8 reds, 7 yellows played)

# Player names
PLAYER1_NAME = "ChatGPT" 
PLAYER2_NAME = "Claude"

# ============================================================
# DON'T EDIT BELOW THIS LINE
# ============================================================

import numpy as np
import time
from datetime import datetime
import json
import os

def resume_game():
    # Create game and set state
    game = Connect4()
    game.board = np.array(BOARD, dtype=int)
    game.current_player = CURRENT_PLAYER
    
    # Count moves made
    red_count = np.sum(game.board == 1)
    yellow_count = np.sum(game.board == 2)
    move_count = red_count + yellow_count
    
    print(f"\n{'#'*60}")
    print(f"# RESUMING CONNECT 4 GAME")
    print(f"# Move {move_count + 1} and onwards")
    print(f"# Current turn: {'RED 🔴' if CURRENT_PLAYER == 1 else 'YELLOW 🟡'}")
    print(f"{'#'*60}")
    print(f"\nRecovered board state:")
    print(game)
    
    # Setup models and renderer
    models = {
        1: ManualModel(PLAYER1_NAME),
        2: ManualModel(PLAYER2_NAME)
    }
    renderer = BoardRenderer()
    
    move_log = []
    start_time = time.time()
    
    # Continue game
    while not game.game_over:
        move_count += 1
        current_player = game.current_player
        model = models[current_player]
        
        # Render and get move
        image = renderer.render(game)
        valid_moves = [c + 1 for c in game.get_valid_moves()]
        
        try:
            move = model.get_move(image, current_player, valid_moves)
            actual_col = move - 1
            
            color = "🔴" if current_player == 1 else "🟡"
            print(f"  Move {move_count}: {color} {model.model_name} → Column {move}")
            
        except KeyboardInterrupt:
            print("\n\n👋 Game saved and cancelled.")
            return
        except Exception as e:
            print(f"  ❌ Error: {e}")
            actual_col = game.get_valid_moves()[0]
            move = actual_col + 1
        
        move_log.append({
            "move_num": move_count,
            "player": current_player,
            "model": model.model_name,
            "column": move
        })
        
        game.make_move(actual_col)
    
    # Game over
    duration = time.time() - start_time
    
    if game.winner:
        winner_model = models[game.winner].model_name
        print(f"\n  🏆 Winner: {winner_model}")
    else:
        print(f"\n  🤝 Draw!")
    
    print(f"  Duration: {duration:.1f}s | Total moves: {move_count}")
    
    # Save result
    os.makedirs("results", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"results/resumed_game_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            "player1": PLAYER1_NAME,
            "player2": PLAYER2_NAME,
            "winner": game.winner,
            "winner_name": models[game.winner].model_name if game.winner else None,
            "total_moves": move_count,
            "move_log": move_log,
            "resumed": True
        }, f, indent=2)
    
    print(f"\nResults saved to: {filename}")


if __name__ == "__main__":
    resume_game()
