import google.generativeai as genai
from .base import BaseModel
from PIL import Image
from typing import List
import time

class GoogleModel(BaseModel):
    """Google Gemini vision model interface."""
    
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-pro"):
        super().__init__(api_key, model_name)
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name,
            system_instruction=self.get_system_prompt()
        )
    
    def get_move(self, image: Image.Image, player_num: int,
                 valid_moves: List[int]) -> int:
        start_time = time.time()
        
        response = self.model.generate_content(
            [image, self.get_move_prompt(player_num, valid_moves)],
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=10,
                temperature=0.1
            )
        )
        
        elapsed = time.time() - start_time
        self.total_calls += 1
        
        move_text = response.text
        return self.parse_move(move_text, valid_moves)
