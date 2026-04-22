"""
DDA Connect 4 Battle Simulator
==============================

Watch two DDA agents battle it out in real-time on a visual Connect 4 board.
Optionally powered by Groq API for LLM-augmented decision making.

Usage:
    # Pure DDA vs DDA (no API needed)
    python dda_battle_sim.py
    
    # Groq-augmented DDA vs DDA
    python dda_battle_sim.py --groq-key YOUR_API_KEY --model llama-3.3-70b-versatile
    
    # Custom game speed
    python dda_battle_sim.py --delay 1.5
"""

import numpy as np
import time
import os
import sys
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict, Any

# Try to import Groq
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

from dda_connect4 import DDAConnect4, DDAConfig


# =============================================================================
# VISUAL RENDERER (Terminal-based for maximum compatibility)
# =============================================================================

class TerminalRenderer:
    """
    Beautiful terminal-based Connect 4 renderer with DDA telemetry.
    Works on any system without additional dependencies.
    """
    
    # ANSI color codes
    RESET = "\033[0m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Board symbols
    EMPTY = "○"
    P1 = "●"  # Red
    P2 = "●"  # Yellow
    
    def __init__(self):
        self.clear_count = 0
    
    def clear(self):
        """Clear terminal."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def render(self, board: np.ndarray, 
               p1_name: str, p2_name: str,
               p1_telem: Dict, p2_telem: Dict,
               current_player: int,
               move_num: int,
               last_move: Optional[int] = None):
        """Render the full game state."""
        self.clear()
        
        # Header
        print(f"\n{self.BOLD}{self.CYAN}╔══════════════════════════════════════════════════════════════╗{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}║{self.RESET}          {self.BOLD}DDA CONNECT 4 BATTLE SIMULATOR{self.RESET}                    {self.BOLD}{self.CYAN}║{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}╚══════════════════════════════════════════════════════════════╝{self.RESET}\n")
        
        # Player info
        p1_indicator = "▶ " if current_player == 1 else "  "
        p2_indicator = "▶ " if current_player == 2 else "  "
        
        print(f"  {p1_indicator}{self.RED}{self.BOLD}Player 1:{self.RESET} {p1_name}")
        print(f"  {p2_indicator}{self.YELLOW}{self.BOLD}Player 2:{self.RESET} {p2_name}")
        print(f"  {self.DIM}Move: {move_num}{self.RESET}\n")
        
        # Board
        self._render_board(board, last_move)
        
        # Telemetry panels
        print(f"\n{self.BOLD}{'─'*30} DDA TELEMETRY {'─'*30}{self.RESET}\n")
        self._render_telemetry_side_by_side(p1_telem, p2_telem, p1_name, p2_name)
    
    def _render_board(self, board: np.ndarray, last_move: Optional[int]):
        """Render the Connect 4 board."""
        print(f"  {self.BLUE}╔═══╦═══╦═══╦═══╦═══╦═══╦═══╗{self.RESET}")
        
        for row in range(6):
            line = f"  {self.BLUE}║{self.RESET}"
            for col in range(7):
                cell = board[row, col]
                
                # Highlight last move
                highlight = last_move == col and row == self._find_piece_row(board, col)
                
                if cell == 0:
                    symbol = f" {self.DIM}{self.EMPTY}{self.RESET} "
                elif cell == 1:
                    if highlight:
                        symbol = f"{self.BOLD}[{self.RED}{self.P1}{self.RESET}{self.BOLD}]{self.RESET}"
                    else:
                        symbol = f" {self.RED}{self.P1}{self.RESET} "
                else:
                    if highlight:
                        symbol = f"{self.BOLD}[{self.YELLOW}{self.P2}{self.RESET}{self.BOLD}]{self.RESET}"
                    else:
                        symbol = f" {self.YELLOW}{self.P2}{self.RESET} "
                
                line += symbol + f"{self.BLUE}║{self.RESET}"
            print(line)
            
            if row < 5:
                print(f"  {self.BLUE}╠═══╬═══╬═══╬═══╬═══╬═══╬═══╣{self.RESET}")
        
        print(f"  {self.BLUE}╚═══╩═══╩═══╩═══╩═══╩═══╩═══╝{self.RESET}")
        print(f"    {self.BOLD}1   2   3   4   5   6   7{self.RESET}")
    
    def _find_piece_row(self, board: np.ndarray, col: int) -> int:
        """Find topmost piece in column."""
        for row in range(6):
            if board[row, col] != 0:
                return row
        return -1
    
    def _render_telemetry_side_by_side(self, p1: Dict, p2: Dict, 
                                        p1_name: str, p2_name: str):
        """Render DDA telemetry for both players side by side."""
        
        def get_state(telem):
            state = telem.get('state', [0,0,0,0])
            if isinstance(state, list) and len(state) == 4:
                return state
            return [0, 0, 0, 0]
        
        def bar(val, width=15, color=""):
            filled = int(abs(val) * width)
            if val >= 0:
                return color + "█" * filled + self.DIM + "░" * (width - filled) + self.RESET
            else:
                return self.DIM + "░" * (width - filled) + self.RESET + color + "█" * filled + self.RESET
        
        s1 = get_state(p1)
        s2 = get_state(p2)
        r1 = p1.get('rigidity', 0)
        r2 = p2.get('rigidity', 0)
        
        # State bars
        labels = ['Center  ', 'Threat  ', 'Tempo   ', 'Aggress ']
        
        print(f"  {self.RED}{self.BOLD}{p1_name[:20]:^25}{self.RESET}   {self.YELLOW}{self.BOLD}{p2_name[:20]:^25}{self.RESET}")
        print()
        
        for i, label in enumerate(labels):
            v1 = s1[i] if i < len(s1) else 0
            v2 = s2[i] if i < len(s2) else 0
            print(f"  {label} {bar(v1, 12, self.RED)} {v1:+.2f}   "
                  f"{label} {bar(v2, 12, self.YELLOW)} {v2:+.2f}")
        
        print()
        
        # Rigidity meters (this is the key DDA feature)
        print(f"  {self.BOLD}RIGIDITY{self.RESET} {bar(r1, 12, self.MAGENTA)} {r1:.2f}   "
              f"{self.BOLD}RIGIDITY{self.RESET} {bar(r2, 12, self.MAGENTA)} {r2:.2f}")
        
        # Decision mode (EXPLORE vs EXPLOIT)
        mode1 = p1.get('decision_mode', 'EXPLOIT')
        mode2 = p2.get('decision_mode', 'EXPLOIT')
        explore_color = self.GREEN if 'EXPLORE' in str(mode1) else self.DIM
        exploit_color = self.GREEN if 'EXPLORE' in str(mode2) else self.DIM
        print(f"  {explore_color}{mode1:^25}{self.RESET}   {exploit_color}{mode2:^25}{self.RESET}")
        
        # Last scores
        scores1 = p1.get('scores', {})
        scores2 = p2.get('scores', {})
        
        if scores1 or scores2:
            print()
            print(f"  {self.DIM}Scores: ", end="")
            for col in range(1, 8):
                s = scores1.get(col-1, 0)
                print(f"{col}:{s:+.1f} ", end="")
            print(f"   Scores: ", end="")
            for col in range(1, 8):
                s = scores2.get(col-1, 0)
                print(f"{col}:{s:+.1f} ", end="")
            print(self.RESET)
    
    def render_winner(self, winner: Optional[int], p1_name: str, p2_name: str):
        """Render game over screen."""
        print(f"\n{self.BOLD}{'═'*60}{self.RESET}")
        
        if winner == 1:
            print(f"\n  {self.RED}{self.BOLD}🏆 WINNER: {p1_name} 🏆{self.RESET}\n")
        elif winner == 2:
            print(f"\n  {self.YELLOW}{self.BOLD}🏆 WINNER: {p2_name} 🏆{self.RESET}\n")
        else:
            print(f"\n  {self.CYAN}{self.BOLD}🤝 DRAW 🤝{self.RESET}\n")
        
        print(f"{self.BOLD}{'═'*60}{self.RESET}")


# =============================================================================
# GROQ LLM INTEGRATION
# =============================================================================

class GroqDDAPlayer:
    """
    DDA player augmented by Groq LLM.
    The LLM provides strategic suggestions, DDA provides adaptive hysteresis.
    
    Different personalities create strategic diversity that triggers the
    hysteresis mechanism - agents surprise each other and adapt!
    """
    
    # Different personalities to create strategic diversity
    PERSONALITIES = {
        "aggressive": """You are an AGGRESSIVE Connect 4 player. Your philosophy:
- Attack relentlessly, create multiple threats
- Force opponent to react to YOU
- Center control is KEY - dominate columns 3,4,5
- Take calculated risks for winning positions
- "The best defense is a good offense"

PRIORITIES: WIN > ATTACK > THREATEN > CENTER > BLOCK
Respond with ONLY a single digit 1-7.""",

        "defensive": """You are a DEFENSIVE Connect 4 player. Your philosophy:
- Never let opponent get 3-in-a-row
- Block every threat, even minor ones
- Build solid foundations before attacking
- Patience wins games - wait for opponent mistakes
- "He who makes the last mistake loses"

PRIORITIES: WIN > BLOCK > SAFE > CENTER > THREATEN
Respond with ONLY a single digit 1-7.""",

        "chaotic": """You are an UNPREDICTABLE Connect 4 player. Your philosophy:
- Mix up your strategy constantly
- Sometimes attack, sometimes defend
- Don't be predictable - confuse your opponent
- Occasionally make "weird" moves to create chaos
- "In chaos, there is opportunity"

PRIORITIES: WIN > BLOCK > (RANDOM: ATTACK or DEFEND or CENTER)
Respond with ONLY a single digit 1-7.""",

        "center": """You are a CENTER-OBSESSED Connect 4 player. Your philosophy:
- Column 4 is EVERYTHING
- Control the middle, control the game
- Build vertical and diagonal threats from center
- Only play edges if absolutely necessary
- "All roads lead through the center"

PRIORITIES: WIN > BLOCK > CENTER > THREATEN
Respond with ONLY a single digit 1-7.""",
    }

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile", 
                 name: str = "Groq-DDA", personality: str = "aggressive",
                 temperature: float = 0.7):
        if not GROQ_AVAILABLE:
            raise ImportError("groq package not installed. Run: pip install groq")
        
        self.client = Groq(api_key=api_key)
        self.model = model
        self.name = name
        self.personality = personality
        self.temperature = temperature  # Higher = more variety = more surprises
        self.system_prompt = self.PERSONALITIES.get(personality, self.PERSONALITIES["aggressive"])
        
        # Give DDA matching identity based on personality
        config = DDAConfig()
        if personality == "aggressive":
            config.identity = np.array([0.4, 0.4, 0.3, 0.8])  # High aggression
        elif personality == "defensive":
            config.identity = np.array([0.2, 0.6, 0.1, 0.3])  # Low aggression, high threat awareness
        elif personality == "chaotic":
            config.identity = np.array([0.3, 0.5, 0.5, 0.5])  # Balanced but high tempo
        else:  # center
            config.identity = np.array([0.6, 0.4, 0.2, 0.5])  # High center focus
        
        self.dda = DDAConnect4(config)
    
    def _board_to_string(self, board: np.ndarray) -> str:
        """Convert board to string for LLM."""
        symbols = {0: '.', 1: 'R', 2: 'Y'}
        lines = []
        for row in board:
            lines.append(' '.join(symbols[c] for c in row))
        lines.append('1 2 3 4 5 6 7')
        return '\n'.join(lines)
    
    def _get_llm_suggestion(self, board: np.ndarray, player: int, 
                            valid_moves: List[int]) -> Optional[int]:
        """Query Groq LLM for move suggestion."""
        try:
            board_str = self._board_to_string(board)
            player_color = "Red" if player == 1 else "Yellow"
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"You are {player_color}. Board:\n{board_str}\n\nValid columns: {[c+1 for c in valid_moves]}\n\nYour move:"}
                ],
                max_tokens=5,
                temperature=self.temperature  # Higher temp = more variety
            )
            
            # Parse response
            text = response.choices[0].message.content.strip()
            col = int(text[0]) - 1  # Convert to 0-indexed
            
            if col in valid_moves:
                return col
            return None
            
        except Exception as e:
            print(f"  [Groq error: {e}]")
            return None
    
    def get_move(self, board: np.ndarray, player: int, 
                 valid_moves: List[int]) -> int:
        """Get move using DDA + LLM augmentation."""
        
        # Get LLM suggestion
        llm_suggestion = self._get_llm_suggestion(board, player, valid_moves)
        
        if llm_suggestion is not None:
            # Use DDA augmentation
            return self.dda.augment(board, player, valid_moves, llm_suggestion)
        else:
            # Fall back to pure DDA
            return self.dda.decide(board, player, valid_moves)
    
    def observe_opponent(self, col: int):
        """Notify DDA of opponent move."""
        self.dda.observe_opponent(col)
    
    def get_telemetry(self) -> Dict:
        """Get DDA telemetry."""
        return self.dda.get_telemetry()
    
    def reset(self):
        """Reset for new game."""
        self.dda.reset()


class PureDDAPlayer:
    """Pure DDA player (no LLM)."""
    
    def __init__(self, name: str = "DDA", config: Optional[DDAConfig] = None):
        self.name = name
        self.dda = DDAConnect4(config)
    
    def get_move(self, board: np.ndarray, player: int, 
                 valid_moves: List[int]) -> int:
        return self.dda.decide(board, player, valid_moves)
    
    def observe_opponent(self, col: int):
        self.dda.observe_opponent(col)
    
    def get_telemetry(self) -> Dict:
        return self.dda.get_telemetry()
    
    def reset(self):
        self.dda.reset()


# =============================================================================
# BATTLE SIMULATOR
# =============================================================================

class BattleSimulator:
    """
    Main battle simulator orchestrating the game between two DDA agents.
    """
    
    def __init__(self, player1, player2, delay: float = 1.0):
        self.player1 = player1
        self.player2 = player2
        self.delay = delay
        self.renderer = TerminalRenderer()
    
    def run_game(self) -> Tuple[Optional[int], int]:
        """
        Run a single game and return (winner, move_count).
        winner: 1, 2, or None for draw
        """
        board = np.zeros((6, 7), dtype=int)
        current_player = 1
        move_count = 0
        last_move = None
        
        self.player1.reset()
        self.player2.reset()
        
        players = {1: self.player1, 2: self.player2}
        
        while True:
            # Get valid moves
            valid_moves = [c for c in range(7) if board[0, c] == 0]
            
            if not valid_moves:
                # Draw
                self._render_state(board, current_player, move_count, last_move)
                self.renderer.render_winner(None, self.player1.name, self.player2.name)
                return (None, move_count)
            
            # Render current state
            self._render_state(board, current_player, move_count, last_move)
            
            # Get move from current player
            player = players[current_player]
            col = player.get_move(board, current_player, valid_moves)
            
            # Make move
            for row in range(5, -1, -1):
                if board[row, col] == 0:
                    board[row, col] = current_player
                    break
            
            move_count += 1
            last_move = col
            
            # Check win
            if self._check_win(board, row, col, current_player):
                self._render_state(board, current_player, move_count, last_move)
                self.renderer.render_winner(current_player, 
                                           self.player1.name, self.player2.name)
                return (current_player, move_count)
            
            # Notify opponent's DDA
            opponent = 3 - current_player
            players[opponent].observe_opponent(col)
            
            # Switch player
            current_player = opponent
            
            # Delay for visual effect
            time.sleep(self.delay)
    
    def _render_state(self, board: np.ndarray, current_player: int,
                      move_num: int, last_move: Optional[int]):
        """Render the full game state."""
        self.renderer.render(
            board,
            self.player1.name,
            self.player2.name,
            self.player1.get_telemetry(),
            self.player2.get_telemetry(),
            current_player,
            move_num,
            last_move
        )
    
    def _check_win(self, board: np.ndarray, row: int, col: int, 
                   player: int) -> bool:
        """Check if last move won."""
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
    
    def run_tournament(self, num_games: int = 5) -> Dict:
        """Run multiple games and track stats."""
        stats = {
            self.player1.name: {"wins": 0, "as_p1": 0, "as_p2": 0},
            self.player2.name: {"wins": 0, "as_p1": 0, "as_p2": 0},
            "draws": 0,
            "total_moves": 0
        }
        
        for i in range(num_games):
            print(f"\n{'='*60}")
            print(f"  GAME {i+1} of {num_games}")
            print(f"{'='*60}")
            time.sleep(1)
            
            # Alternate starting player
            if i % 2 == 1:
                self.player1, self.player2 = self.player2, self.player1
            
            winner, moves = self.run_game()
            stats["total_moves"] += moves
            
            if winner == 1:
                stats[self.player1.name]["wins"] += 1
                stats[self.player1.name]["as_p1"] += 1
            elif winner == 2:
                stats[self.player2.name]["wins"] += 1
                stats[self.player2.name]["as_p2"] += 1
            else:
                stats["draws"] += 1
            
            # Swap back if we swapped
            if i % 2 == 1:
                self.player1, self.player2 = self.player2, self.player1
            
            print("\nPress Enter for next game...")
            input()
        
        return stats


# =============================================================================
# MAIN
# =============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="DDA Connect 4 Battle Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Pure DDA vs DDA (no API needed)
  python dda_battle_sim.py
  
  # Groq-augmented agents
  python dda_battle_sim.py --groq-key YOUR_KEY --model llama-3.3-70b-versatile
  
  # Slower game for observation
  python dda_battle_sim.py --delay 2.0
  
  # Tournament mode
  python dda_battle_sim.py --games 5
        """
    )
    
    parser.add_argument("--groq-key", type=str, default=None,
                        help="Groq API key for LLM augmentation")
    parser.add_argument("--model", type=str, default="llama-3.3-70b-versatile",
                        help="Groq model for Player 1 (default: llama-3.3-70b-versatile)")
    parser.add_argument("--model2", type=str, default=None,
                        help="Groq model for Player 2 (default: same as --model)")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Seconds between moves (default: 1.0)")
    parser.add_argument("--games", type=int, default=1,
                        help="Number of games to play (default: 1)")
    
    args = parser.parse_args()
    
    # Create players
    if args.groq_key:
        model2 = args.model2 or args.model  # Use model2 if specified, else same as model
        
        if model2 != args.model:
            print(f"🚀 Initializing Groq battle: {args.model} vs {model2}")
        else:
            print("🚀 Initializing Groq-powered DDA agents with DIFFERENT personalities...")
            print("   (Different strategies = more surprises = hysteresis in action!)")
        
        try:
            # Player 1: Aggressive with first model
            player1 = GroqDDAPlayer(
                args.groq_key, args.model, 
                name=f"AGGRESSOR ({args.model[:20]})", 
                personality="aggressive",
                temperature=0.9  # High variety
            )
            # Player 2: Defensive with second model (may be different!)
            player2 = GroqDDAPlayer(
                args.groq_key, model2, 
                name=f"DEFENDER ({model2[:20]})", 
                personality="defensive",
                temperature=0.9  # High variety  
            )
        except ImportError as e:
            print(f"Error: {e}")
            print("Install groq: pip install groq")
            sys.exit(1)
    else:
        print("🤖 Initializing pure DDA agents (no API needed)...")
        # Give them slightly different personalities for variety
        config1 = DDAConfig()
        config1.identity = np.array([0.4, 0.5, 0.3, 0.7])  # More aggressive
        
        config2 = DDAConfig()
        config2.identity = np.array([0.2, 0.5, 0.1, 0.4])  # More defensive
        
        player1 = PureDDAPlayer("DDA-Aggressor", config1)
        player2 = PureDDAPlayer("DDA-Defender", config2)
    
    # Create simulator
    sim = BattleSimulator(player1, player2, delay=args.delay)
    
    print(f"\n{'='*60}")
    print(f"  Player 1: {player1.name}")
    print(f"  Player 2: {player2.name}")
    print(f"  Games: {args.games}")
    print(f"  Delay: {args.delay}s between moves")
    print(f"{'='*60}")
    print("\nPress Enter to start...")
    input()
    
    if args.games == 1:
        winner, moves = sim.run_game()
        print(f"\nGame ended in {moves} moves.")
    else:
        stats = sim.run_tournament(args.games)
        
        print(f"\n{'='*60}")
        print("  TOURNAMENT RESULTS")
        print(f"{'='*60}")
        for name in [player1.name, player2.name]:
            s = stats[name]
            print(f"\n  {name}:")
            print(f"    Wins: {s['wins']}/{args.games}")
            print(f"    As P1: {s['as_p1']}, As P2: {s['as_p2']}")
        print(f"\n  Draws: {stats['draws']}")
        print(f"  Avg moves: {stats['total_moves']/args.games:.1f}")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
