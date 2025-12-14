import numpy as np
from typing import Optional, List, Tuple

class Connect4:
    """Connect 4 game engine with full game state management."""
    
    ROWS = 6
    COLS = 7
    EMPTY = 0
    PLAYER1 = 1  # Red
    PLAYER2 = 2  # Yellow
    
    def __init__(self):
        self.board = np.zeros((self.ROWS, self.COLS), dtype=int)
        self.current_player = self.PLAYER1
        self.game_over = False
        self.winner: Optional[int] = None
        self.move_history: List[Tuple[int, int]] = []
    
    def get_valid_moves(self) -> List[int]:
        """Return list of valid column indices (0-6)."""
        return [c for c in range(self.COLS) if self.board[0][c] == self.EMPTY]
    
    def make_move(self, col: int) -> bool:
        """Drop piece in column. Returns True if valid move."""
        if col not in self.get_valid_moves():
            return False
        
        # Find lowest empty row
        for row in range(self.ROWS - 1, -1, -1):
            if self.board[row][col] == self.EMPTY:
                self.board[row][col] = self.current_player
                self.move_history.append((self.current_player, col))
                
                if self._check_win(row, col):
                    self.game_over = True
                    self.winner = self.current_player
                elif len(self.get_valid_moves()) == 0:
                    self.game_over = True  # Draw
                else:
                    self._switch_player()
                return True
        return False
    
    def _switch_player(self):
        """Switch to the other player."""
        self.current_player = (
            self.PLAYER2 if self.current_player == self.PLAYER1 
            else self.PLAYER1
        )
    
    def _check_win(self, row: int, col: int) -> bool:
        """Check if last move at (row, col) won the game."""
        player = self.board[row][col]
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]  # horizontal, vertical, diagonals
        
        for dr, dc in directions:
            count = 1
            # Check both directions along this line
            for sign in [1, -1]:
                r, c = row + dr * sign, col + dc * sign
                while (0 <= r < self.ROWS and 0 <= c < self.COLS 
                       and self.board[r][c] == player):
                    count += 1
                    r += dr * sign
                    c += dc * sign
            if count >= 4:
                return True
        return False
    
    def copy(self) -> 'Connect4':
        """Create a deep copy of the game state."""
        new_game = Connect4()
        new_game.board = self.board.copy()
        new_game.current_player = self.current_player
        new_game.game_over = self.game_over
        new_game.winner = self.winner
        new_game.move_history = self.move_history.copy()
        return new_game
    
    def __str__(self) -> str:
        """String representation of the board for debugging."""
        symbols = {self.EMPTY: '.', self.PLAYER1: 'R', self.PLAYER2: 'Y'}
        lines = []
        for row in self.board:
            lines.append(' '.join(symbols[cell] for cell in row))
        lines.append('1 2 3 4 5 6 7')
        return '\n'.join(lines)
