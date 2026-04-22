"""
DDA Connect 4 — Dynamic Decision Algorithm for Real-Time Win Optimization
===========================================================================

A self-contained, pluggable DDA implementation that can:
1. Run standalone as a complete Connect 4 player
2. Augment any LLM's decision-making in real-time
3. Be dropped into any system with minimal integration

Based on the DDA Formal Specification:
- Identity persistence (consistent play style)
- Reality integration (board state parsing)  
- Surprise → rigidity adaptation (defensive crouch when surprised)

Usage:
    # Standalone mode
    dda = DDAConnect4()
    column = dda.decide(board, player, valid_moves)
    
    # LLM augmentation mode
    dda = DDAConnect4()
    llm_suggestion = some_llm.get_move(...)
    augmented_move = dda.augment(board, player, valid_moves, llm_suggestion)
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field
import math


@dataclass
class DDAState:
    """Internal state vector x_t ∈ ℝ^4"""
    center_control: float = 0.0   # [-1, 1] our center advantage
    threat_level: float = 0.0     # [0, 1] urgency of immediate threats
    tempo: float = 0.0            # [-1, 1] who has initiative
    aggression: float = 0.5       # [0, 1] attack vs defense posture
    
    def to_vector(self) -> np.ndarray:
        return np.array([self.center_control, self.threat_level, 
                         self.tempo, self.aggression])
    
    @classmethod
    def from_vector(cls, v: np.ndarray) -> 'DDAState':
        return cls(
            center_control=float(np.clip(v[0], -1, 1)),
            threat_level=float(np.clip(v[1], 0, 1)),
            tempo=float(np.clip(v[2], -1, 1)),
            aggression=float(np.clip(v[3], 0, 1))
        )


@dataclass
class DDAConfig:
    """Tunable algorithm parameters"""
    # Identity attractor x* (preferred play style)
    identity: np.ndarray = field(default_factory=lambda: np.array([0.3, 0.5, 0.2, 0.6]))
    
    # Core dynamics
    gamma: float = 0.3          # Identity stiffness
    m: float = 0.5              # External pressure/gain
    k_base: float = 0.2         # Base step size
    
    # Rigidity adaptation - TUNED FOR EXPLORATION
    epsilon_0: float = 0.15     # Lower threshold = more sensitive to surprise
    s: float = 0.15             # Sharper response to surprise
    alpha: float = 0.25         # Faster rigidity changes
    delta: float = 0.05         # Slower decay = sustain exploration longer
    
    # Decision making
    tau: float = 2.0            # Decision sharpness (softmax temperature)
    w_obj: float = 0.7          # Objective score weight
    w_subj: float = 0.3         # Subjective/identity weight
    
    # LLM augmentation
    llm_trust: float = 0.6      # How much to trust LLM suggestions


class DDAConnect4:
    """
    Dynamic Decision Algorithm for Connect 4
    
    The DDA governs agent behavior through three forces:
    1. Identity pull (self-preservation toward x*)
    2. Truth channel (world forcing from board state)
    3. Reflection channel (strategic evaluation of moves)
    
    Key property: Surprise increases rigidity, making the agent more
    conservative and identity-preserving when predictions fail.
    """
    
    ROWS = 6
    COLS = 7
    CENTER_COL = 3  # 0-indexed center
    
    def __init__(self, config: Optional[DDAConfig] = None):
        self.config = config or DDAConfig()
        
        # State variables
        self.x_t = DDAState()                    # Current state
        self.rho_t: float = 0.0                  # Rigidity [0,1]
        self.last_prediction: Optional[int] = None
        self.epsilon_history: List[float] = []   # Track prediction errors
        self.move_count: int = 0
        
        # Telemetry for visualization/debugging
        self.telemetry: Dict[str, Any] = {}
    
    def reset(self):
        """Reset for a new game."""
        self.x_t = DDAState()
        self.rho_t = 0.0
        self.last_prediction = None
        self.epsilon_history = []
        self.move_count = 0
        self.telemetry = {}
    
    # =========================================================================
    # TRUTH CHANNEL: Parse board state into target vector
    # =========================================================================
    
    def _truth_channel(self, board: np.ndarray, player: int) -> np.ndarray:
        """
        T(I_t, ΔI_t) = f_parse(I_t) + λ * f_Δ(ΔI_t)
        
        Extract the "truth" of the current board state.
        """
        opponent = 3 - player
        
        # Feature extraction
        center_ctrl = self._eval_center_control(board, player, opponent)
        threat_lvl = self._eval_threat_level(board, player, opponent)
        tempo = self._eval_tempo(board, player, opponent)
        
        # Aggression target based on game phase
        pieces = np.sum(board > 0)
        if pieces < 10:
            target_aggr = 0.7  # Early: be aggressive
        elif pieces < 25:
            target_aggr = 0.5  # Mid: balanced
        else:
            target_aggr = 0.3  # Late: careful
        
        return np.array([center_ctrl, threat_lvl, tempo, target_aggr])
    
    def _eval_center_control(self, board: np.ndarray, player: int, opponent: int) -> float:
        """Evaluate center column control advantage."""
        # Weight columns by distance from center (center = highest weight)
        col_weights = np.array([1, 2, 3, 4, 3, 2, 1])  # Center column = 4
        
        player_score = 0
        opp_score = 0
        
        for col in range(self.COLS):
            col_data = board[:, col]
            player_score += np.sum(col_data == player) * col_weights[col]
            opp_score += np.sum(col_data == opponent) * col_weights[col]
        
        total = player_score + opp_score
        if total == 0:
            return 0.0
        return (player_score - opp_score) / max(total, 1)
    
    def _eval_threat_level(self, board: np.ndarray, player: int, opponent: int) -> float:
        """Evaluate immediate threat urgency (0-1)."""
        our_threats = self._count_threats(board, player)
        their_threats = self._count_threats(board, opponent)
        
        # Urgency increases with opponent threats
        urgency = min(1.0, their_threats * 0.25 + our_threats * 0.1)
        return urgency
    
    def _count_threats(self, board: np.ndarray, player: int) -> int:
        """Count 3-in-a-row threats with open end."""
        threats = 0
        
        # Horizontal
        for r in range(self.ROWS):
            for c in range(self.COLS - 3):
                window = board[r, c:c+4]
                if np.sum(window == player) == 3 and np.sum(window == 0) == 1:
                    threats += 1
        
        # Vertical
        for r in range(self.ROWS - 3):
            for c in range(self.COLS):
                window = board[r:r+4, c]
                if np.sum(window == player) == 3 and np.sum(window == 0) == 1:
                    threats += 1
        
        # Diagonals
        for r in range(self.ROWS - 3):
            for c in range(self.COLS - 3):
                # Main diagonal
                window = [board[r+i, c+i] for i in range(4)]
                if window.count(player) == 3 and window.count(0) == 1:
                    threats += 1
                # Anti diagonal
                window = [board[r+i, c+3-i] for i in range(4)]
                if window.count(player) == 3 and window.count(0) == 1:
                    threats += 1
        
        return threats
    
    def _eval_tempo(self, board: np.ndarray, player: int, opponent: int) -> float:
        """Evaluate who has initiative (forcing moves)."""
        our_threats = self._count_threats(board, player)
        their_threats = self._count_threats(board, opponent)
        
        # Positive = we have initiative
        diff = our_threats - their_threats
        return np.clip(diff * 0.3, -1, 1)
    
    # =========================================================================
    # REFLECTION CHANNEL: Score actions based on objectives + identity
    # =========================================================================
    
    def _reflection_channel(self, board: np.ndarray, player: int, 
                            valid_moves: List[int]) -> Tuple[np.ndarray, Dict[int, float]]:
        """
        R(A_t, Φ_t, L) = x_t + Σ π(a) * d(a)
        
        Returns (reflection_target, action_scores)
        """
        x_vec = self.x_t.to_vector()
        
        # Score each action
        scores = {}
        directions = {}
        
        for col in valid_moves:
            q_score = self._objective_score(board, player, col)
            s_score = self._identity_score(col)
            
            combined = self.config.w_obj * q_score + self.config.w_subj * s_score
            scores[col] = combined
            
            # Action direction in state space
            directions[col] = self._action_direction(col, q_score)
        
        # Softmax to get preference distribution
        score_vals = np.array([scores[c] for c in valid_moves])
        exp_scores = np.exp(self.config.tau * (score_vals - np.max(score_vals)))
        probs = exp_scores / np.sum(exp_scores)
        
        # Weighted sum of directions
        reflection_target = x_vec.copy()
        for i, col in enumerate(valid_moves):
            reflection_target += probs[i] * directions[col]
        
        return reflection_target, scores
    
    def _objective_score(self, board: np.ndarray, player: int, col: int) -> float:
        """Q(a): Objective/tactical score for placing in column."""
        opponent = 3 - player
        score = 0.0
        
        # Find landing row
        row = self._get_landing_row(board, col)
        if row is None:
            return -10.0  # Invalid move
        
        # 1. Winning move? (highest priority)
        test_board = board.copy()
        test_board[row, col] = player
        if self._check_win(test_board, row, col, player):
            return 10.0
        
        # 2. Block opponent win? (second highest)
        test_board[row, col] = opponent
        if self._check_win(test_board, row, col, opponent):
            score += 5.0
        
        # 3. Creates threat
        test_board[row, col] = player
        new_threats = self._count_threats(test_board, player)
        old_threats = self._count_threats(board, player)
        score += (new_threats - old_threats) * 1.5
        
        # 4. Center control bonus
        center_dist = abs(col - self.CENTER_COL)
        score += (3 - center_dist) * 0.3
        
        # 5. Don't give opponent winning move above
        if row > 0:
            test_board[row-1, col] = opponent
            if self._check_win(test_board, row-1, col, opponent):
                score -= 3.0
        
        return score
    
    def _identity_score(self, col: int) -> float:
        """S(a): How well does this action align with our identity?"""
        # Aggressive identity prefers center, attacking moves
        aggression = self.x_t.aggression
        
        # Center bias (aggressive play loves center)
        center_dist = abs(col - self.CENTER_COL)
        center_score = (3 - center_dist) / 3.0
        
        # Blend based on aggression level
        return aggression * center_score + (1 - aggression) * 0.5
    
    def _action_direction(self, col: int, q_score: float) -> np.ndarray:
        """d(a): Direction in state space for this action."""
        # Each column "pushes" the state in different directions
        # Center moves → more center control
        # High Q moves → more tempo
        # Aggressive moves → more aggression
        
        center_push = (self.CENTER_COL - abs(col - self.CENTER_COL)) / self.CENTER_COL
        tempo_push = np.clip(q_score / 5.0, -1, 1)
        aggr_push = 0.1 if col in [2, 3, 4] else -0.1
        
        return np.array([center_push * 0.1, 0.0, tempo_push * 0.1, aggr_push])
    
    def _get_landing_row(self, board: np.ndarray, col: int) -> Optional[int]:
        """Find the row where a piece would land in given column."""
        for row in range(self.ROWS - 1, -1, -1):
            if board[row, col] == 0:
                return row
        return None
    
    def _check_win(self, board: np.ndarray, row: int, col: int, player: int) -> bool:
        """Check if position (row, col) creates a win for player."""
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        
        for dr, dc in directions:
            count = 1
            for sign in [1, -1]:
                r, c = row + dr * sign, col + dc * sign
                while (0 <= r < self.ROWS and 0 <= c < self.COLS 
                       and board[r, c] == player):
                    count += 1
                    r += dr * sign
                    c += dc * sign
            if count >= 4:
                return True
        return False
    
    # =========================================================================
    # PREDICTION + RIGIDITY
    # =========================================================================
    
    def _predict_opponent(self, board: np.ndarray, opponent: int, 
                          valid_moves: List[int]) -> int:
        """Predict opponent's most likely move."""
        best_col = valid_moves[0]
        best_score = float('-inf')
        
        for col in valid_moves:
            score = self._objective_score(board, opponent, col)
            if score > best_score:
                best_score = score
                best_col = col
        
        return best_col
    
    def _compute_prediction_error(self, actual_move: int) -> float:
        """ε_t = ||predicted - actual||"""
        if self.last_prediction is None:
            return 0.0
        
        # Distance between predicted and actual column (normalized)
        error = abs(self.last_prediction - actual_move) / (self.COLS - 1)
        return error
    
    def _update_rigidity(self, epsilon_t: float):
        """
        ρ_{t+1} = clip(ρ_t + α * tanh((ε_t - ε_0) / s), 0, 1)
        
        Bidirectional update: low error relaxes, high error tightens.
        """
        cfg = self.config
        
        # Centered update (can go up or down)
        delta_rho = cfg.alpha * math.tanh((epsilon_t - cfg.epsilon_0) / cfg.s)
        self.rho_t = np.clip(self.rho_t + delta_rho, 0, 1)
        
        # Apply decay (recovery when safe)
        self.rho_t *= (1 - cfg.delta)
        
        self.epsilon_history.append(epsilon_t)
    
    # =========================================================================
    # CORE DDA UPDATE
    # =========================================================================
    
    def _update_state(self, truth_target: np.ndarray, 
                      reflection_target: np.ndarray):
        """
        x_{t+1} = x_t + k_eff * (γ(x* - x_t) + m(F_T + F_R))
        
        where k_eff = k_base * (1 - ρ_t)
        """
        cfg = self.config
        x_vec = self.x_t.to_vector()
        
        # Effective step size (rigidity reduces it)
        k_eff = cfg.k_base * (1 - self.rho_t)
        
        # Identity force
        F_id = cfg.gamma * (cfg.identity - x_vec)
        
        # Truth force
        F_T = truth_target - x_vec
        
        # Reflection force  
        F_R = reflection_target - x_vec
        
        # Combined update
        delta_x = k_eff * (F_id + cfg.m * (F_T + F_R))
        
        # Apply update
        new_vec = x_vec + delta_x
        self.x_t = DDAState.from_vector(new_vec)
        
        # Store telemetry
        self.telemetry['k_eff'] = k_eff
        self.telemetry['F_id'] = np.linalg.norm(F_id)
        self.telemetry['F_T'] = np.linalg.norm(F_T)
        self.telemetry['F_R'] = np.linalg.norm(F_R)
    
    # =========================================================================
    # DECISION SELECTION
    # =========================================================================
    
    def _select_action(self, valid_moves: List[int], scores: Dict[int, float],
                       truth_target: np.ndarray, 
                       reflection_target: np.ndarray) -> int:
        """
        HYSTERESIS-DRIVEN EXPLORATION/EXPLOITATION
        
        The key insight: rigidity should make agents MORE CAPABLE by:
        - LOW rigidity (predictable opponent) → EXPLOIT: pick highest-scored move
        - HIGH rigidity (surprised by opponent) → EXPLORE: sample alternatives
        
        This prevents getting stuck in predictable patterns!
        
        When opponent surprises us, we explore NEW strategies.
        When opponent is predictable, we exploit our best known move.
        """
        import random
        
        cfg = self.config
        
        # Always take winning moves immediately
        for col in valid_moves:
            if scores.get(col, 0) >= 9.5:  # Winning move threshold
                return col
        
        # Always block losing moves
        for col in valid_moves:
            if scores.get(col, 0) >= 4.5:  # Blocking threshold
                row = self._get_landing_row(self.telemetry.get('board', np.zeros((6,7))), col)
                if row is not None:
                    return col
        
        # EXPLORATION vs EXPLOITATION based on rigidity
        exploration_prob = self.rho_t  # High rigidity = high exploration
        
        if random.random() < exploration_prob:
            # EXPLORE: Sample from softmax distribution (not just argmax)
            # This is the hysteresis magic - surprising situations trigger creativity!
            
            score_vals = np.array([scores.get(c, 0) for c in valid_moves])
            
            # Temperature increases with rigidity (more surprise = more random)
            temp = 1.0 + self.rho_t * 3.0  # Range 1-4
            
            # Softmax with temperature
            exp_scores = np.exp((score_vals - np.max(score_vals)) / temp)
            probs = exp_scores / np.sum(exp_scores)
            
            # Sample from distribution
            chosen_idx = np.random.choice(len(valid_moves), p=probs)
            chosen = valid_moves[chosen_idx]
            
            self.telemetry['decision_mode'] = f'EXPLORE (ρ={self.rho_t:.2f})'
            return chosen
        else:
            # EXPLOIT: Pick the highest-scoring move deterministically
            chosen = max(valid_moves, key=lambda c: scores.get(c, 0))
            self.telemetry['decision_mode'] = f'EXPLOIT (ρ={self.rho_t:.2f})'
            return chosen
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    def decide(self, board: np.ndarray, player: int, 
               valid_moves: List[int]) -> int:
        """
        Main decision function — standalone mode.
        
        Args:
            board: 6x7 numpy array (0=empty, 1=player1, 2=player2)
            player: Current player (1 or 2)
            valid_moves: List of valid column indices (0-6)
        
        Returns:
            Column index to play
        """
        if not valid_moves:
            raise ValueError("No valid moves available")
        
        self.move_count += 1
        
        # Truth channel: parse board state
        truth_target = self._truth_channel(board, player)
        
        # Reflection channel: evaluate actions
        reflection_target, scores = self._reflection_channel(board, player, valid_moves)
        
        # Update internal state
        self._update_state(truth_target, reflection_target)
        
        # Select action
        chosen_col = self._select_action(valid_moves, scores, 
                                         truth_target, reflection_target)
        
        # Predict opponent's next move (for rigidity calculation)
        opponent = 3 - player
        opponent_valid = [c for c in range(self.COLS) 
                        if c != chosen_col or board[0, c] == 0]
        if opponent_valid:
            self.last_prediction = self._predict_opponent(board, opponent, opponent_valid)
        
        # Update telemetry
        self.telemetry.update({
            'move': self.move_count,
            'chosen_col': chosen_col,
            'scores': scores,
            'state': self.x_t.to_vector().tolist(),
            'rigidity': self.rho_t,
            'prediction': self.last_prediction
        })
        
        return chosen_col
    
    def observe_opponent(self, opponent_move: int):
        """
        Call this after opponent makes their move.
        Updates rigidity based on prediction error.
        """
        epsilon_t = self._compute_prediction_error(opponent_move)
        self._update_rigidity(epsilon_t)
        
        self.telemetry['epsilon'] = epsilon_t
    
    def augment(self, board: np.ndarray, player: int,
                valid_moves: List[int], llm_suggestion: int) -> int:
        """
        LLM augmentation mode — blend DDA with LLM suggestion.
        
        The DDA can override or defer to the LLM based on:
        - How "surprising" the LLM's choice is to DDA
        - Current rigidity level (high rigidity = trust DDA more)
        - Move urgency (winning/blocking moves always taken)
        
        Args:
            board: 6x7 numpy array
            player: Current player (1 or 2)
            valid_moves: List of valid column indices
            llm_suggestion: The column the LLM wants to play
        
        Returns:
            Final column to play (may differ from LLM suggestion)
        """
        # Get DDA's pure decision
        dda_choice = self.decide(board, player, valid_moves)
        
        # If DDA found a winning move, always take it
        row = self._get_landing_row(board, dda_choice)
        if row is not None:
            test_board = board.copy()
            test_board[row, dda_choice] = player
            if self._check_win(test_board, row, dda_choice, player):
                return dda_choice
        
        # If LLM suggestion blocks a loss, take it
        if llm_suggestion in valid_moves:
            row = self._get_landing_row(board, llm_suggestion)
            if row is not None:
                test_board = board.copy()
                opponent = 3 - player
                test_board[row, llm_suggestion] = opponent
                if self._check_win(test_board, row, llm_suggestion, opponent):
                    return llm_suggestion
        
        # Blend based on trust and rigidity
        # High rigidity = trust DDA more (surprise → conservatism)
        dda_trust = (1 - self.config.llm_trust) + self.rho_t * self.config.llm_trust
        
        # If DDA and LLM agree, easy choice
        if dda_choice == llm_suggestion:
            return dda_choice
        
        # Otherwise, pick based on trust weighting
        if dda_trust > 0.5:
            self.telemetry['llm_override'] = 'dda'
            return dda_choice
        else:
            self.telemetry['llm_override'] = 'llm'
            return llm_suggestion if llm_suggestion in valid_moves else dda_choice
    
    def get_telemetry(self) -> Dict[str, Any]:
        """Get current telemetry for visualization/debugging."""
        return self.telemetry.copy()
    
    def get_state_summary(self) -> str:
        """Human-readable state summary."""
        return (f"State: center={self.x_t.center_control:.2f}, "
                f"threat={self.x_t.threat_level:.2f}, "
                f"tempo={self.x_t.tempo:.2f}, "
                f"aggr={self.x_t.aggression:.2f} | "
                f"Rigidity: {self.rho_t:.2f}")


# =============================================================================
# DEMO / TEST
# =============================================================================

if __name__ == "__main__":
    import random
    
    print("=" * 60)
    print("DDA Connect 4 — Self-Test")
    print("=" * 60)
    
    # Create DDA player
    dda = DDAConnect4()
    
    # Simple board setup
    board = np.zeros((6, 7), dtype=int)
    
    # Play a few moves
    moves_played = []
    current_player = 1
    
    for turn in range(10):
        valid_moves = [c for c in range(7) if board[0, c] == 0]
        if not valid_moves:
            break
        
        if current_player == 1:
            # DDA plays
            col = dda.decide(board, current_player, valid_moves)
            print(f"Turn {turn+1}: DDA → Column {col+1}")
            print(f"  {dda.get_state_summary()}")
        else:
            # Random opponent
            col = random.choice(valid_moves)
            dda.observe_opponent(col)  # DDA learns from opponent
            print(f"Turn {turn+1}: Random → Column {col+1}")
            print(f"  Pred error: {dda.telemetry.get('epsilon', 0):.2f}, "
                  f"Rigidity: {dda.rho_t:.2f}")
        
        # Make move
        for row in range(5, -1, -1):
            if board[row, col] == 0:
                board[row, col] = current_player
                break
        
        current_player = 3 - current_player
    
    print("\n" + "=" * 60)
    print("Final Board:")
    symbols = {0: '.', 1: 'D', 2: 'R'}
    for row in board:
        print(' '.join(symbols[c] for c in row))
    print('1 2 3 4 5 6 7')
    print("=" * 60)
