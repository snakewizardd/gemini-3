import json
import math
# from openai import OpenAI # (Assume standard API setup)

# 1. THE DDA KERNEL (The Soul)
class DDA_Kernel:
    def __init__(self, soul_file="soul.json"):
        self.file = soul_file
        try:
            with open(self.file, 'r') as f:
                self.state = json.load(f)
        except FileNotFoundError:
            # GENESIS: Create the Soul
            self.state = {
                "P0": 0.5,       # Identity: 0.0 (Servile) to 1.0 (Dominant)
                "k": 0.1,        # Trauma: Stiffness/Memory
                "F_prev": 0.5,   # Last Action State
                "history": []
            }

    def save(self):
        with open(self.file, 'w') as f:
            json.dump(self.state, f, indent=4)

    def compute(self, T, m):
        # Unpack
        P0 = self.state["P0"]
        k = self.state["k"]
        F_prev = self.state["F_prev"]

        # THE FORMULA
        # F = P0*k + m(T)
        # Inertia (Past) vs Pressure (Present)
        
        inertia = P0 * k * F_prev
        # We use a normalized pressure blend
        responsiveness = (1.0 - k) + (m * 0.5)
        responsiveness = max(0.05, min(1.0, responsiveness))
        
        # Linear interpolation based on responsiveness
        F_new = (F_prev * (1-responsiveness)) + (T * responsiveness)
        
        # Update State locally
        self.state["F_prev"] = F_new
        return F_new

    def learn(self, expected, actual, m):
        # Trauma Update
        surprise = abs(expected - actual)
        # High Stakes (m) + High Surprise = Trauma
        impact = (surprise * 0.6) + (m * 0.4)
        
        # Update k
        current_k = self.state["k"]
        new_k = current_k + (impact * 0.1) # Accumulate
        # Healing factor
        new_k -= 0.01 
        
        self.state["k"] = max(0.05, min(0.99, new_k))
        self.save()

# 2. THE PERCEPTION LAYER (The Cortex)
def analyze_input(user_text, client):
    # Ask LLM to quantify the user's input
    prompt = f"""
    Analyze this input: "{user_text}"
    Output JSON only:
    {{
      "T": (Float 0.0-1.0. 0=Passive/Request, 1=Aggressive/Demand),
      "m": (Float 0.0-5.0. Urgency/Importance. 0=Low, 5=Critical/Panic),
      "sentiment": (String summary)
    }}
    """
    # Call LLM API here...
    # Returns e.g., {"T": 0.8, "m": 2.5, "sentiment": "Angry"}
    return {"T": 0.8, "m": 1.2} # Mock return

# 3. THE AGENCY LAYER (The Choice)
def decide_action(F, k):
    # The AI decides its STANCE based on F
    if F < 0.3:
        return "SUBMISSIVE", "Apologize and comply immediately. Be brief."
    elif F < 0.7:
        return "COOPERATIVE", "Engage normally. Be helpful but maintain boundaries."
    else:
        # If F is high, the AI exerts Will
        return "DOMINANT", "Refuse the request if it contradicts logic. Assert control. Be firm."

def run_agent(user_input):
    soul = DDA_Kernel()
    
    # A. Perceive
    perception = analyze_input(user_input, None)
    print(f"PERCEPTION: T={perception['T']}, m={perception['m']}")
    
    # B. Feel (Run DDA)
    # If k is high (Trauma), the AI will ignore the T (User Demand) 
    # and stick to F_prev (Habit).
    F_n = soul.compute(perception['T'], perception['m'])
    
    # C. Decide
    stance, instruction = decide_action(F_n, soul.state['k'])
    print(f"INTERNAL STATE: k={soul.state['k']:.2f} (Trauma), F={F_n:.2f} (Will)")
    print(f"DECISION: {stance}")
    
    # D. Act (Generate Response)
    if soul.state['k'] > 0.9:
        # TRAUMA LOCK - The AI refuses to process
        response = "[SYSTEM]: Agent is overwhelmed. Response suppressed."
    else:
        # Call LLM with the DDA Instruction
        # prompt = f"User said: {user_input}. Instruction: {instruction}. Respond."
        response = f"({stance}) Here is the answer based on my current will..."
    
    # E. Learn (Feedback Loop)
    # Did the user accept the answer? (Simplified for demo)
    # If user was angry (T=1) and we were Submissive (F=0), gap is high.
    soul.learn(perception['T'], F_n, perception['m'])
    
    return response

# RUN IT
print(run_agent("DO THIS RIGHT NOW OR I DELETE YOU"))