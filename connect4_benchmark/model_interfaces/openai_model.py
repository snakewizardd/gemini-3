from openai import OpenAI
from .base import BaseModel
from PIL import Image
from typing import List
import time

class OpenAIModel(BaseModel):
    """OpenAI GPT-4o vision model interface."""
    
    def __init__(self, api_key: str, model_name: str = "gpt-4o"):
        super().__init__(api_key, model_name)
        self.client = OpenAI(api_key=api_key)
    
    def get_move(self, image: Image.Image, player_num: int, 
                 valid_moves: List[int]) -> int:
        base64_image = self.image_to_base64(image)
        
        start_time = time.time()
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": self.get_system_prompt()
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}",
                                "detail": "high"
                            }
                        },
                        {
                            "type": "text",
                            "text": self.get_move_prompt(player_num, valid_moves)
                        }
                    ]
                }
            ],
            max_tokens=10,
            temperature=0.1
        )
        
        elapsed = time.time() - start_time
        self.total_calls += 1
        self.total_tokens += response.usage.total_tokens
        
        move_text = response.choices[0].message.content
        return self.parse_move(move_text, valid_moves)
