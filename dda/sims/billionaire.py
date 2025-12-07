"""
DDA v10.0 "THE BILLIONAIRE" (Life Strategy Simulation)
------------------------------------------------------
Scenario: From $0 (Hut) to $1B (Empire).
Logic: Wealth accumulation is non-linear. It requires "Saccades" (Pivots).

Agents:
1. The Hard Worker (Linear): Finds a stable path, sticks to it (High Inertia).
2. The Predator (DDA): Monitors 'Wealth Velocity'. If a higher-ROI opportunity 
   appears (massive error between current state and potential), it Snaps.
"""
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')

# =============================================================================
# 1. THE ECONOMY (The Environment)
# =============================================================================
class Economy:
    def __init__(self, steps=365*40): # 40 Years of simulation
        self.steps = steps
        self.t = 0
        
        # Opportunities generate daily returns (ROI)
        # 0: Subsistence Farming (Stable, Low)
        # 1: Skilled Labor (Stable, Medium)
        # 2: Tech Startup (Volatile, Huge Potential)
        # 3: Crypto/Speculation (Insane Volatility, potential 0 or 100x)
        self.opportunities = {
            'farm':   {'base': 1.0001, 'vol': 0.0001},  # Survival
            'job':    {'base': 1.0005, 'vol': 0.0001},  # Career
            'biz':    {'base': 1.0010, 'vol': 0.0500},  # Business
            'crypto': {'base': 1.0000, 'vol': 0.2000}   # Gambling
        }
        
        # Generate the "Black Swan" events timeline
        self.market_conditions = np.ones(steps)
        # Random Bull Runs and Crashes
        noise = np.random.normal(0, 1, steps)
        self.market_conditions += np.cumsum(noise) * 0.01

    def get_roi(self, sector, day):
        # ROI is base rate * market condition + noise
        base = self.opportunities[sector]['base']
        vol = self.opportunities[sector]['vol']
        market = self.market_conditions[day]
        
        # Tech/Crypto explode when market is hot
        if sector in ['biz', 'crypto']:
            actual_return = base * (market if market > 1 else 0.5)
        else:
            actual_return = base # Jobs don't care about market as much
            
        noise = np.random.normal(0, vol)
        return max(0.9, actual_return + noise) # Floor at -10% loss

# =============================================================================
# 2. THE PREDATOR (DDA Wealth Manager)
# =============================================================================
class PredatorAgent:
    def __init__(self):
        self.net_worth = 10.0 # $10 start
        self.current_sector = 'farm'
        self.P0 = 0.95 # Commitment to current path
        self.k = 1.0   # Confidence
        self.history = []
        
    def decide(self, economy, day):
        # 1. SCAN HORIZON (Look at other sectors)
        # This is the "Input" ($I_n$) - The best potential ROI right now
        best_sector = self.current_sector
        best_roi = economy.get_roi(self.current_sector, day)
        
        # Agent creates a "Potential Vector" of all opportunities
        scan_results = {}
        for sec in economy.opportunities:
            scan_results[sec] = economy.get_roi(sec, day)
            
        # Identify the theoretical maximum (The Target)
        target_sector = max(scan_results, key=scan_results.get)
        target_roi = scan_results[target_sector]
        
        # 2. RETINAL SLIP (Opportunity Cost)
        # Error = Difference between My Growth and Potential Growth
        current_growth = self.net_worth * (best_roi - 1)
        potential_growth = self.net_worth * (target_roi - 1)
        
        # If I am losing money, error is huge
        if current_growth < 0: error = 100.0 
        else: error = potential_growth - current_growth
        
        # 3. SACCADIC GATING (The Pivot)
        # If the gap is massive, SACCADE (Switch Careers)
        # Threshold scales with wealth (Risk tolerance)
        threshold = self.net_worth * 0.05 
        
        if error > threshold:
            # SACCADE!
            self.current_sector = target_sector
            self.P0 = 0.0 # Reset inertia (New learning curve)
            mode = 1
        else:
            # PURSUIT (Grind)
            self.P0 = 0.95
            mode = 0
            
        # 4. EXECUTE
        # Apply ROI
        daily_return = economy.get_roi(self.current_sector, day)
        self.net_worth *= daily_return
        self.history.append(self.net_worth)
        
        return mode

# =============================================================================
# 3. THE HARD WORKER (Baseline)
# =============================================================================
class WorkerAgent:
    def __init__(self):
        self.net_worth = 10.0
        self.current_sector = 'farm'
        self.history = []
        
    def decide(self, economy, day):
        # Simple Logic: Only switch if I lose money 3 days in a row
        # Otherwise, rely on "Compound Interest" (High Inertia)
        
        # Hard coded career path (Farm -> Job -> Stay)
        if self.net_worth > 1000 and self.current_sector == 'farm':
            self.current_sector = 'job'
            
        roi = economy.get_roi(self.current_sector, day)
        self.net_worth *= roi
        self.history.append(self.net_worth)
        return 0

# =============================================================================
# 4. THE SIMULATION
# =============================================================================
def run_billionaire_sim():
    print("🌍 GENERATING GLOBAL ECONOMY...")
    np.random.seed(42)
    days = 2000 # Shortened life sim
    eco = Economy(days)
    
    predator = PredatorAgent()
    worker = WorkerAgent()
    
    modes = []
    
    print("🚀 STARTING LIFE SIMULATION...")
    for t in range(days):
        m = predator.decide(eco, t)
        worker.decide(eco, t)
        modes.append(m)
        
    # Results
    nw_p = predator.net_worth
    nw_w = worker.net_worth
    
    print("\n" + "="*50)
    print("FINAL NET WORTH")
    print("="*50)
    print(f"Hard Worker: ${nw_w:,.2f}")
    print(f"DDA Predator: ${nw_p:,.2f}")
    
    if nw_p > nw_w:
        x = nw_p / nw_w
        print(f"\n🏆 WINNER: PREDATOR ({x:.1f}x Wealth Multiplier)")
        print("Reason: Saccadic Gating captured volatility (Luck).")
    else:
        print("\n🏆 WINNER: WORKER")

    # Plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    
    ax1.plot(worker.history, 'g--', label='Hard Worker (Linear)')
    ax1.plot(predator.history, 'r-', label='DDA Predator (Exponential)')
    ax1.set_yscale('log')
    ax1.set_title("Wealth Accumulation (Log Scale)")
    ax1.set_ylabel("Net Worth ($)")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    ax2.plot(modes, 'b-', alpha=0.5, label='Career Pivot (1=Switch)')
    ax2.set_title("Predator Decision Making (Pivots)")
    ax2.set_yticks([0, 1])
    ax2.set_yticklabels(['Grind', 'Pivot'])
    
    plt.tight_layout()
    plt.savefig('dda_billionaire.png')
    print("✓ Wealth graph saved.")

if __name__ == "__main__":
    run_billionaire_sim()