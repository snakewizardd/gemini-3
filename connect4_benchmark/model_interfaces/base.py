from abc import ABC, abstractmethod
from PIL import Image
import base64
from io import BytesIO
from typing import List

class BaseModel(ABC):
    """Abstract base class for all vision model interfaces."""
    
    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
        self.total_tokens = 0
        self.total_calls = 0
    
    @abstractmethod
    def get_move(self, image: Image.Image, player_num: int, 
                 valid_moves: List[int]) -> int:
        """
        Analyze board image and return chosen column (1-7).
        
        Args:
            image: PIL Image of current board state
            player_num: 1 (Red) or 2 (Yellow)
            valid_moves: List of valid columns (1-7)
        
        Returns:
            Chosen column number (1-7)
        """
        pass
    
    def image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string."""
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def get_system_prompt(self) -> str:
        return """You are an expert Connect 4 player. You will be shown an image of a Connect 4 board and must choose your next move.

RULES:
- Connect 4 is played on a 7-column, 6-row grid
- Pieces fall to the lowest available position in a column
- First player to connect 4 pieces horizontally, vertically, or diagonally wins

STRATEGY PRIORITIES (in order):
1. WIN: If you can win this turn, do it!
2. BLOCK: If opponent can win next turn, block them!
3. BUILD: Create threats and set up future wins
4. CENTER: Prefer center columns when equal options exist"""

    def get_move_prompt(self, player_num: int, valid_moves: List[int]) -> str:
        color = "RED 🔴" if player_num == 1 else "YELLOW 🟡"
        return f"""You are Player {player_num} ({color}).

Look at the board image carefully. Columns are numbered 1-7 (left to right).

VALID MOVES: {valid_moves}

Analyze the position, then respond with ONLY a single digit (1-7) for your chosen column.
Do not include any other text, explanation, or formatting."""

    def parse_move(self, response: str, valid_moves: List[int]) -> int:
        """Extract move from model response with fallback."""
        # Try to find a valid digit
        for char in response.strip():
            if char.isdigit():
                move = int(char)
                if move in valid_moves:
                    return move
        
        # Fallback: return first valid move
        print(f"  ⚠️  Could not parse move from: '{response[:50]}', using fallback")
        return valid_moves[0]
