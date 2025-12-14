from PIL import Image, ImageDraw, ImageFont
from .board import Connect4

class BoardRenderer:
    """Renders Connect 4 board state as PIL Images."""
    
    def __init__(self, cell_size: int = 100):
        self.cell_size = cell_size
        self.padding = 30
        self.piece_margin = 8
        
        # Colors
        self.BOARD_COLOR = (0, 100, 200)      # Blue board
        self.BG_COLOR = (40, 40, 40)          # Dark background
        self.EMPTY_COLOR = (255, 255, 255)    # White empty slots
        self.PLAYER1_COLOR = (220, 50, 50)    # Red
        self.PLAYER2_COLOR = (255, 220, 0)    # Yellow
        self.TEXT_COLOR = (255, 255, 255)
        
    def render(self, game: Connect4, 
               highlight_last_move: bool = True,
               show_column_numbers: bool = True) -> Image.Image:
        """Render the current board state as a PIL Image."""
        
        width = self.cell_size * game.COLS + self.padding * 2
        height = self.cell_size * game.ROWS + self.padding * 2
        
        if show_column_numbers:
            height += 50  # Space for column labels
        
        # Create image
        img = Image.new('RGB', (width, height), self.BG_COLOR)
        draw = ImageDraw.Draw(img)
        
        # Draw board background
        board_rect = [
            self.padding, 
            self.padding,
            width - self.padding, 
            self.padding + self.cell_size * game.ROWS
        ]
        draw.rounded_rectangle(board_rect, radius=15, fill=self.BOARD_COLOR)
        
        # Draw pieces
        last_move_col = game.move_history[-1][1] if game.move_history else -1
        
        for row in range(game.ROWS):
            for col in range(game.COLS):
                cx = self.padding + col * self.cell_size + self.cell_size // 2
                cy = self.padding + row * self.cell_size + self.cell_size // 2
                radius = self.cell_size // 2 - self.piece_margin
                
                # Determine color
                cell = game.board[row][col]
                if cell == game.EMPTY:
                    color = self.EMPTY_COLOR
                elif cell == game.PLAYER1:
                    color = self.PLAYER1_COLOR
                else:
                    color = self.PLAYER2_COLOR
                
                # Draw piece
                bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
                draw.ellipse(bbox, fill=color)
                
                # Highlight last move
                if highlight_last_move and col == last_move_col:
                    if cell != game.EMPTY:
                        # Find if this is the last placed piece
                        for check_row in range(game.ROWS):
                            if game.board[check_row][col] != game.EMPTY:
                                if check_row == row:
                                    draw.ellipse(bbox, outline=(255, 255, 255), width=3)
                                break
        
        # Draw column numbers
        if show_column_numbers:
            font = self._get_font(32)
            
            for col in range(game.COLS):
                x = self.padding + col * self.cell_size + self.cell_size // 2
                y = height - 40
                text = str(col + 1)  # 1-indexed for humans/models
                
                # Center text
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                draw.text((x - text_width // 2, y), text, 
                         fill=self.TEXT_COLOR, font=font)
        
        return img
    
    def render_with_info(self, game: Connect4, 
                         player1_name: str, 
                         player2_name: str) -> Image.Image:
        """Render board with player information header."""
        board_img = self.render(game)
        
        # Create header
        header_height = 60
        width = board_img.width
        full_img = Image.new('RGB', (width, board_img.height + header_height), self.BG_COLOR)
        
        draw = ImageDraw.Draw(full_img)
        font = self._get_font(20)
        
        # Player 1 info (left)
        draw.ellipse([20, 15, 50, 45], fill=self.PLAYER1_COLOR)
        draw.text((60, 20), player1_name, fill=self.TEXT_COLOR, font=font)
        
        # Player 2 info (right)
        draw.ellipse([width - 50, 15, width - 20, 45], fill=self.PLAYER2_COLOR)
        p2_bbox = draw.textbbox((0, 0), player2_name, font=font)
        p2_width = p2_bbox[2] - p2_bbox[0]
        draw.text((width - 60 - p2_width, 20), player2_name, fill=self.TEXT_COLOR, font=font)
        
        # Current turn indicator
        if not game.game_over:
            indicator_x = 55 if game.current_player == game.PLAYER1 else width - 55
            draw.text((indicator_x, 18), "●", 
                     fill=self.PLAYER1_COLOR if game.current_player == game.PLAYER1 else self.PLAYER2_COLOR, 
                     font=font)
        
        # Paste board below header
        full_img.paste(board_img, (0, header_height))
        
        return full_img
    
    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Get a font with fallback to default."""
        # Try common font paths on different systems
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:/Windows/Fonts/arial.ttf",  # Windows
            "C:/Windows/Fonts/segoeui.ttf",
            "/System/Library/Fonts/Helvetica.ttc",  # macOS
            "/System/Library/Fonts/SFNSText.ttf",
        ]
        
        for path in font_paths:
            try:
                return ImageFont.truetype(path, size)
            except (OSError, IOError):
                continue
        
        # Fallback to default
        return ImageFont.load_default()
