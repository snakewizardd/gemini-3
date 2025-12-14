import anthropic
from .base import BaseModel
from PIL import Image
from typing import List
import time

class AnthropicModel(BaseModel):
    """Anthropic Claude vision model interface."""
    
    def __init__(self, api_key: str, model_name: str = "claude-sonnet-4-20250514"):
        super().__init__(api_key, model_name)
        self.client = anthropic.Anthropic(api_key=api_key)
    
    def get_move(self, image: Image.Image, player_num: int,
                 valid_moves: List[int]) -> int:
        base64_image = self.image_to_base64(image)
        
        start_time = time.time()
        
        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=10,
            system=self.get_system_prompt(),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": self.get_move_prompt(player_num, valid_moves)
                        }
                    ]
                }
            ]
        )
        
        elapsed = time.time() - start_time
        self.total_calls += 1
        self.total_tokens += response.usage.input_tokens + response.usage.output_tokens
        
        move_text = response.content[0].text
        return self.parse_move(move_text, valid_moves)
