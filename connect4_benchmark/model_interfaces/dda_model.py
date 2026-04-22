"""
DDA Model Interface — BaseModel wrapper for DDA Connect 4
=========================================================

Allows the DDA algorithm to be used as a drop-in replacement
for any LLM model in the Connect 4 benchmark.
"""

from typing import List
from PIL import Image
import numpy as np

from model_interfaces.base import BaseModel
from dda_connect4 import DDAConnect4


class DDAModel(BaseModel):
    """
    DDA-powered Connect 4 player implementing the BaseModel interface.
    
    Can operate in two modes:
    1. Pure DDA: Uses only the DDA algorithm
    2. LLM-Augmented: Wraps another model and augments its decisions
    """
    
    def __init__(self, wrapped_model: BaseModel = None, model_name: str = None):
        """
        Args:
            wrapped_model: Optional LLM model to augment. If None, runs pure DDA.
            model_name: Display name. Defaults to "DDA" or "DDA+{wrapped_model}"
        """
        self.dda = DDAConnect4()
        self.wrapped_model = wrapped_model
        
        if model_name:
            self._model_name = model_name
        elif wrapped_model:
            self._model_name = f"DDA+{wrapped_model.model_name}"
        else:
            self._model_name = "DDA"
        
        self._last_board: np.ndarray = None
        self._last_player: int = None
    
    @property
    def model_name(self) -> str:
        return self._model_name
    
    def _image_to_board(self, image: Image.Image) -> np.ndarray:
        """
        Parse the board image to extract the game state.
        
        For the benchmark renderer, we can detect pieces by color:
        - Red: Player 1
        - Yellow: Player 2
        - Blue/Gray: Empty
        
        Returns 6x7 numpy array.
        """
        # Resize for consistent analysis
        img = image.resize((350, 300))
        pixels = np.array(img)
        
        board = np.zeros((6, 7), dtype=int)
        
        # Approximate cell positions (based on renderer's 50x50 cells)
        for row in range(6):
            for col in range(7):
                # Center of each cell
                cx = 25 + col * 50
                cy = 25 + row * 50
                
                # Sample a small region around center
                region = pixels[max(0,cy-10):cy+10, max(0,cx-10):cx+10]
                if region.size == 0:
                    continue
                    
                avg_color = region.mean(axis=(0, 1))
                
                # Detect by color (R, G, B)
                r, g, b = avg_color[0], avg_color[1], avg_color[2]
                
                if r > 180 and g < 100 and b < 100:
                    board[row, col] = 1  # Red = Player 1
                elif r > 200 and g > 180 and b < 100:
                    board[row, col] = 2  # Yellow = Player 2
                # else stays 0 (empty)
        
        return board
    
    def get_move(self, image: Image.Image, player: int, 
                 valid_moves: List[int]) -> int:
        """
        Get the next move.
        
        Args:
            image: PIL Image of current board state
            player: Current player (1 or 2)
            valid_moves: List of valid columns (1-indexed)
        
        Returns:
            Column to play (1-indexed)
        """
        # Parse board from image
        board = self._image_to_board(image)
        
        # Convert valid_moves to 0-indexed
        valid_moves_0 = [c - 1 for c in valid_moves]
        
        # Track opponent moves for rigidity calculation
        if self._last_board is not None and self._last_player != player:
            # Find what column opponent played
            diff = board - self._last_board
            opponent_cols = np.where(diff.sum(axis=0) != 0)[0]
            if len(opponent_cols) > 0:
                self.dda.observe_opponent(opponent_cols[0])
        
        # Get move
        if self.wrapped_model:
            # LLM-augmented mode
            llm_move = self.wrapped_model.get_move(image, player, valid_moves)
            llm_move_0 = llm_move - 1
            chosen_col = self.dda.augment(board, player, valid_moves_0, llm_move_0)
        else:
            # Pure DDA mode
            chosen_col = self.dda.decide(board, player, valid_moves_0)
        
        # Store state for next call
        self._last_board = board.copy()
        self._last_player = player
        
        # Return 1-indexed
        return chosen_col + 1
    
    def reset(self):
        """Reset for a new game."""
        self.dda.reset()
        self._last_board = None
        self._last_player = None


class DDADirectModel(BaseModel):
    """
    DDA model that works directly with board arrays instead of images.
    Use this when you have direct access to the game state.
    """
    
    def __init__(self, model_name: str = "DDA-Direct"):
        self.dda = DDAConnect4()
        self._model_name = model_name
        self._last_player: int = None
    
    @property
    def model_name(self) -> str:
        return self._model_name
    
    def get_move_from_board(self, board: np.ndarray, player: int,
                            valid_moves: List[int]) -> int:
        """
        Get move directly from board array.
        
        Args:
            board: 6x7 numpy array (0=empty, 1=player1, 2=player2)
            player: Current player (1 or 2)
            valid_moves: List of valid columns (0-indexed)
        
        Returns:
            Column to play (0-indexed)
        """
        return self.dda.decide(board, player, valid_moves)
    
    def observe_opponent(self, col: int):
        """Notify DDA of opponent's move for rigidity calculation."""
        self.dda.observe_opponent(col)
    
    def get_move(self, image: Image.Image, player: int,
                 valid_moves: List[int]) -> int:
        """BaseModel interface - not recommended, use get_move_from_board."""
        raise NotImplementedError(
            "DDADirectModel works with boards, not images. "
            "Use get_move_from_board() or DDAModel for image-based play."
        )
    
    def reset(self):
        """Reset for a new game."""
        self.dda.reset()
        self._last_player = None
    
    def get_telemetry(self):
        """Get DDA telemetry for visualization."""
        return self.dda.get_telemetry()
