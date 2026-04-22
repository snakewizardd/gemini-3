"""
Connect 4 Vision Benchmark
===========================

Two multimodal AI models battle in Connect 4, using only vision to analyze
the board state. Each turn, the current player receives an image of the 
board and must respond with their move.

Usage:
    python benchmark.py --games 10 --model1 gpt-4o --model2 claude-sonnet-4-20250514
    python benchmark.py --games 20 --save-images --model1 gpt-4o --model2 gemini-1.5-pro
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import time

from game.board import Connect4
from game.renderer import BoardRenderer
from model_interfaces.base import BaseModel


@dataclass
class GameResult:
    """Result of a single game."""
    game_id: int
    player1_model: str
    player2_model: str
    winner: Optional[int]  # 1, 2, or None for draw
    winner_model: Optional[str]
    total_moves: int
    move_log: List[Dict]
    duration_seconds: float
    timestamp: str


@dataclass 
class TournamentStats:
    """Statistics from a tournament of games."""
    total_games: int
    model_stats: Dict[str, Dict]
    draws: int
    avg_game_length: float
    total_duration: float


class Connect4Benchmark:
    """Main benchmark runner for Connect 4 vision tournaments."""
    
    def __init__(self, model1: BaseModel, model2: BaseModel,
                 save_images: bool = False,
                 output_dir: str = "results"):
        self.model1 = model1
        self.model2 = model2
        self.renderer = BoardRenderer()
        self.save_images = save_images
        self.output_dir = output_dir
        self.results: List[GameResult] = []
        
        if save_images:
            os.makedirs(f"{output_dir}/games", exist_ok=True)
    
    def play_game(self, game_id: int = 0, 
                  swap_players: bool = False,
                  verbose: bool = True) -> GameResult:
        """Play a single game between the two models."""
        
        game = Connect4()
        
        # Optionally swap who plays first
        if swap_players:
            models = {1: self.model2, 2: self.model1}
        else:
            models = {1: self.model1, 2: self.model2}
        
        move_log = []
        start_time = time.time()
        
        if verbose:
            print(f"\n{'='*50}")
            print(f"Game {game_id}")
            print(f"Player 1 (Red):    {models[1].model_name}")
            print(f"Player 2 (Yellow): {models[2].model_name}")
            print('='*50)
        
        move_num = 0
        while not game.game_over:
            move_num += 1
            current_player = game.current_player
            model = models[current_player]
            
            # Render current board state
            image = self.renderer.render(game)
            
            # Save image if requested
            if self.save_images:
                image.save(f"{self.output_dir}/games/game{game_id}_move{move_num:02d}.png")
            
            # Get valid moves (1-indexed for models)
            valid_moves = [c + 1 for c in game.get_valid_moves()]
            
            # Query model for move
            try:
                move = model.get_move(image, current_player, valid_moves)
                actual_col = move - 1  # Convert to 0-indexed
                
                if verbose:
                    color = "🔴" if current_player == 1 else "🟡"
                    print(f"  Move {move_num}: {color} {model.model_name} → Column {move}")
                
            except Exception as e:
                print(f"  ❌ Error from {model.model_name}: {e}")
                actual_col = game.get_valid_moves()[0]
                move = actual_col + 1
            
            # Record move
            move_log.append({
                "move_num": move_num,
                "player": current_player,
                "model": model.model_name,
                "column": move
            })
            
            # Make the move
            game.make_move(actual_col)
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
        
        duration = time.time() - start_time
        
        # Determine winner
        winner_model = None
        if game.winner:
            winner_model = models[game.winner].model_name
        
        result = GameResult(
            game_id=game_id,
            player1_model=models[1].model_name,
            player2_model=models[2].model_name,
            winner=game.winner,
            winner_model=winner_model,
            total_moves=len(move_log),
            move_log=move_log,
            duration_seconds=round(duration, 2),
            timestamp=datetime.now().isoformat()
        )
        
        if verbose:
            if game.winner:
                print(f"\n  🏆 Winner: {winner_model}")
            else:
                print(f"\n  🤝 Draw!")
            print(f"  Duration: {duration:.1f}s | Moves: {len(move_log)}")
        
        # Save final board
        if self.save_images:
            final_img = self.renderer.render_with_info(
                game, models[1].model_name, models[2].model_name
            )
            final_img.save(f"{self.output_dir}/games/game{game_id}_final.png")
        
        self.results.append(result)
        return result
    
    def run_tournament(self, num_games: int = 10, 
                       verbose: bool = True) -> TournamentStats:
        """Run a tournament with alternating first-player advantage."""
        
        print(f"\n{'#'*60}")
        print(f"# CONNECT 4 VISION BENCHMARK")
        print(f"# {self.model1.model_name} vs {self.model2.model_name}")
        print(f"# Games: {num_games}")
        print(f"{'#'*60}")
        
        stats = {
            self.model1.model_name: {"wins": 0, "as_p1": 0, "as_p2": 0},
            self.model2.model_name: {"wins": 0, "as_p1": 0, "as_p2": 0},
        }
        draws = 0
        total_moves = 0
        start_time = time.time()
        
        for i in range(num_games):
            # Alternate who goes first
            swap = (i % 2 == 1)
            result = self.play_game(game_id=i+1, swap_players=swap, verbose=verbose)
            
            total_moves += result.total_moves
            
            if result.winner:
                winner = result.winner_model
                stats[winner]["wins"] += 1
                
                # Track first-player advantage
                if result.winner == 1:
                    stats[result.player1_model]["as_p1"] += 1
                else:
                    stats[result.player2_model]["as_p2"] += 1
            else:
                draws += 1
        
        total_duration = time.time() - start_time
        
        tournament_stats = TournamentStats(
            total_games=num_games,
            model_stats=stats,
            draws=draws,
            avg_game_length=round(total_moves / num_games, 1),
            total_duration=round(total_duration, 1)
        )
        
        self._print_summary(tournament_stats)
        return tournament_stats
    
    def _print_summary(self, stats: TournamentStats):
        """Print tournament summary."""
        print(f"\n{'='*60}")
        print("TOURNAMENT RESULTS")
        print('='*60)
        
        for model_name, model_stats in stats.model_stats.items():
            win_rate = model_stats['wins'] / stats.total_games * 100
            print(f"\n{model_name}:")
            print(f"  Wins: {model_stats['wins']}/{stats.total_games} ({win_rate:.1f}%)")
            print(f"  As Player 1: {model_stats['as_p1']} wins")
            print(f"  As Player 2: {model_stats['as_p2']} wins")
        
        print(f"\nDraws: {stats.draws}")
        print(f"Avg game length: {stats.avg_game_length} moves")
        print(f"Total duration: {stats.total_duration:.1f}s")
        print('='*60)
    
    def save_results(self, filename: str = None):
        """Save all game results to JSON."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.output_dir}/benchmark_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
        
        data = {
            "models": [self.model1.model_name, self.model2.model_name],
            "games": [asdict(r) for r in self.results],
            "summary": {
                "total_games": len(self.results),
                "model1_wins": sum(1 for r in self.results if r.winner_model == self.model1.model_name),
                "model2_wins": sum(1 for r in self.results if r.winner_model == self.model2.model_name),
                "draws": sum(1 for r in self.results if r.winner is None)
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\nResults saved to: {filename}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def create_model(name: str, openai_key: str = None, anthropic_key: str = None, google_key: str = None) -> BaseModel:
    """Factory function to create model instances."""
    from model_interfaces.manual_model import ManualModel, ClipboardModel
    
    name_lower = name.lower()
    
    # DDA (Dynamic Decision Algorithm) - standalone or wrapped
    if name_lower == "dda":
        from model_interfaces.dda_model import DDAModel
        return DDAModel()
    elif name_lower.startswith("dda+"):
        # LLM augmentation mode: dda+gpt-4o, dda+claude-sonnet-4-20250514, etc.
        from model_interfaces.dda_model import DDAModel
        wrapped_name = name[4:]  # Remove "dda+" prefix
        wrapped_model = create_model(wrapped_name, openai_key, anthropic_key, google_key)
        return DDAModel(wrapped_model=wrapped_model)
    
    # Manual modes for web-based LLM access (no API needed)
    if name_lower == "manual" or name_lower.startswith("manual:"):
        display_name = name.split(":", 1)[1] if ":" in name else "Manual-LLM"
        return ManualModel(display_name)
    elif name_lower == "clipboard" or name_lower.startswith("clipboard:"):
        display_name = name.split(":", 1)[1] if ":" in name else "Clipboard-LLM"
        return ClipboardModel(display_name)
    
    # API-based models (lazy import to avoid requiring all libraries)
    if "gpt" in name_lower or "o1" in name_lower or "o3" in name_lower:
        if not openai_key:
            raise ValueError("OpenAI API key required for GPT models")
        from model_interfaces.openai_model import OpenAIModel
        return OpenAIModel(openai_key, name)
    elif "claude" in name_lower:
        if not anthropic_key:
            raise ValueError("Anthropic API key required for Claude models")
        from model_interfaces.anthropic_model import AnthropicModel
        return AnthropicModel(anthropic_key, name)
    elif "gemini" in name_lower:
        if not google_key:
            raise ValueError("Google API key required for Gemini models")
        from model_interfaces.google_model import GoogleModel
        return GoogleModel(google_key, name)
    else:
        raise ValueError(f"Unknown model: {name}. Use 'gpt-*', 'claude-*', 'gemini-*', 'manual', or 'manual:Name'")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Connect 4 Vision Benchmark - AI models play Connect 4 using vision",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python benchmark.py --games 10 --model1 gpt-4o --model2 claude-sonnet-4-20250514
  python benchmark.py --games 20 --save-images --model1 gpt-4o --model2 gemini-1.5-pro
  
Supported Models:
  OpenAI:    gpt-4o, gpt-4o-mini, gpt-4-turbo, o1, o3
  Anthropic: claude-sonnet-4-20250514, claude-3-5-sonnet-20241022, claude-3-opus-20240229
  Google:    gemini-1.5-pro, gemini-1.5-flash, gemini-2.0-flash-exp

Environment Variables:
  OPENAI_API_KEY    - Required for GPT models
  ANTHROPIC_API_KEY - Required for Claude models  
  GOOGLE_API_KEY    - Required for Gemini models
        """
    )
    parser.add_argument("--games", type=int, default=10, help="Number of games to play (default: 10)")
    parser.add_argument("--save-images", action="store_true", help="Save board images for each move")
    parser.add_argument("--model1", type=str, default="gpt-4o", help="First model (default: gpt-4o)")
    parser.add_argument("--model2", type=str, default="claude-sonnet-4-20250514", help="Second model (default: claude-sonnet-4-20250514)")
    parser.add_argument("--output-dir", type=str, default="results", help="Output directory for results (default: results)")
    parser.add_argument("--quiet", action="store_true", help="Reduce output verbosity")
    args = parser.parse_args()
    
    # Load API keys from environment
    OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
    ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
    GOOGLE_KEY = os.environ.get("GOOGLE_API_KEY")
    
    # Create models
    try:
        model1 = create_model(args.model1, OPENAI_KEY, ANTHROPIC_KEY, GOOGLE_KEY)
        model2 = create_model(args.model2, OPENAI_KEY, ANTHROPIC_KEY, GOOGLE_KEY)
    except ValueError as e:
        print(f"Error: {e}")
        print("\nMake sure to set the required API key environment variables.")
        exit(1)
    
    # Run benchmark
    benchmark = Connect4Benchmark(
        model1, model2,
        save_images=args.save_images,
        output_dir=args.output_dir
    )
    
    stats = benchmark.run_tournament(num_games=args.games, verbose=not args.quiet)
    benchmark.save_results()
