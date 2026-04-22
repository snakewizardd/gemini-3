"""
Manual model interface for when you have web access to LLMs but not APIs.

Usage:
    The game will display/open each board image and prompt you to 
    copy it to your preferred LLM (ChatGPT, Claude, etc.) and enter 
    their move response.
"""

from .base import BaseModel
from PIL import Image
from typing import List
import os
import webbrowser
import tempfile


class ManualModel(BaseModel):
    """
    Manual/interactive model for playing via web interfaces.
    
    Each turn:
    1. Opens the board image for you to copy
    2. Shows the prompt to paste to the LLM
    3. Waits for you to enter the LLM's response
    """
    
    def __init__(self, model_name: str = "Human-assisted"):
        # No API key needed
        super().__init__(api_key="", model_name=model_name)
        self.temp_dir = tempfile.mkdtemp()
        self.image_count = 0
    
    def get_move(self, image: Image.Image, player_num: int,
                 valid_moves: List[int]) -> int:
        # Save and open the image
        self.image_count += 1
        img_path = os.path.join(self.temp_dir, f"board_{self.image_count}.png")
        image.save(img_path)
        
        # Open image in default viewer
        print(f"\n{'='*60}")
        print(f"🎮 Turn for: {self.model_name}")
        print(f"{'='*60}")
        print(f"\n📸 Opening board image: {img_path}")
        
        try:
            # Try to open in default image viewer
            if os.name == 'nt':  # Windows
                os.startfile(img_path)
            elif os.name == 'posix':  # macOS/Linux
                webbrowser.open(f'file://{img_path}')
        except:
            print(f"   (Couldn't auto-open, please open manually)")
        
        # Show the prompt to copy
        color = "RED 🔴" if player_num == 1 else "YELLOW 🟡"
        print(f"\n📋 Copy this prompt to {self.model_name}:")
        print("-" * 40)
        prompt = self.get_move_prompt(player_num, valid_moves)
        print(prompt)
        print("-" * 40)
        
        # Get the response
        while True:
            try:
                response = input(f"\n⌨️  Enter {self.model_name}'s move (1-7): ").strip()
                move = self.parse_move(response, valid_moves)
                if move in valid_moves:
                    self.total_calls += 1
                    return move
                else:
                    print(f"   ❌ Invalid move. Valid moves are: {valid_moves}")
            except KeyboardInterrupt:
                print("\n\n👋 Game cancelled.")
                raise
            except:
                print(f"   ❌ Please enter a number 1-7")


class ClipboardModel(ManualModel):
    """
    Like ManualModel, but copies the image to clipboard automatically.
    Requires: pip install pyperclip pillow
    """
    
    def __init__(self, model_name: str = "Clipboard-LLM"):
        super().__init__(model_name)
        try:
            import pyperclip
            self.has_clipboard = True
        except ImportError:
            self.has_clipboard = False
            print("⚠️  Install pyperclip for clipboard support: pip install pyperclip")
    
    def get_move(self, image: Image.Image, player_num: int,
                 valid_moves: List[int]) -> int:
        # Save image first
        self.image_count += 1
        img_path = os.path.join(self.temp_dir, f"board_{self.image_count}.png")
        image.save(img_path)
        
        print(f"\n{'='*60}")
        print(f"🎮 Turn for: {self.model_name}")
        print(f"{'='*60}")
        print(f"\n📸 Board saved to: {img_path}")
        
        # Open in viewer
        try:
            if os.name == 'nt':
                os.startfile(img_path)
            else:
                webbrowser.open(f'file://{img_path}')
            print("   ✅ Opened in image viewer - drag/paste into your LLM chat")
        except:
            print("   (Couldn't auto-open)")
        
        # Show prompt
        color = "RED 🔴" if player_num == 1 else "YELLOW 🟡"
        prompt = self.get_move_prompt(player_num, valid_moves)
        
        if self.has_clipboard:
            try:
                import pyperclip
                pyperclip.copy(prompt)
                print(f"\n📋 Prompt copied to clipboard! Just paste it after the image.")
            except:
                print(f"\n📋 Prompt:\n{prompt}")
        else:
            print(f"\n📋 Copy this prompt:\n{prompt}")
        
        # Get response
        while True:
            try:
                response = input(f"\n⌨️  Enter {self.model_name}'s move (1-7): ").strip()
                move = self.parse_move(response, valid_moves)
                if move in valid_moves:
                    self.total_calls += 1
                    return move
                print(f"   ❌ Invalid. Valid moves: {valid_moves}")
            except KeyboardInterrupt:
                raise
            except:
                print("   ❌ Enter a number 1-7")
