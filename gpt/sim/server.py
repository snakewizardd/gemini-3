
# server.py
# pip install websockets numpy
import asyncio
import json
import math
import time
import numpy as np
import websockets

# -----------------------------
# World config (2D continuous plane)
# -----------------------------
W, H = 100.0, 100.0

HOME = np.array([20.0, 20.0])
FOOD = np.array([82.0, 78.0])
THREAT = np.array([55.0, 55.0])
THREAT_R = 16.0

FOOD_RADIUS = 4.0
FOOD_RESPAWN_SEC = 6.0

# Movement actions (N,S,E,W,Stay)
ACTIONS = [
    ("N", np.array([0.0, -1.0])),
    ("S", np.array([0.0,  1.0])),
    ("E", np.array([1.0,  0.0])),
    ("W", np.array([-1.0, 0.0])),
    ("STAY", np.array([0.0, 0.0])),
]

STEP_SIZE = 1.2            # intended movement magnitude
SLIP_PROB = 0.18           # sometimes your action doesn't do what you expect
SLIP_NOISE = 1.4           # how big the slip is

# Threat "shock" = unpredictable push when inside zone
THREAT_SHOCK = 2.0

# Stream config
FPS = 30
SIM_STEPS_PER_SEND = 1

rng = np.random.default_rng(3)

# -----------------------------
# DDA config
# -----------------------------
# We'll treat state x_t as 2D position for this sim: x_t = p_t
gamma = 0.10               # identity pull strength (to HOME)
k_base = 0.80              # baseline openness (step scaling)
rho = 0.10                 # rigidity in [0,1]
alpha = 0.10               # rigidity learning rate
eps0 = 0.85                # surprise threshold
s_sig = 0.35               # sigmoid sensitivity
rho_decay = 0.010          # recovery

# Reflection personality weights
w_obj = 1.0
w_subj = 1.1
tau = 2.3

# Need system
hunger = 0.20              # [0,1]
hunger_rate = 0.0028       # per step
hunger_relief = 0.65       # when eating
reward = 0                 # food count
food_available = True
food_cooldown = 0.0

def clamp01(x): return float(np.clip(x, 0.0, 1.0))
def unit(v, eps=1e-9):
    n = float(np.linalg.norm(v))
    return v / (n + eps)

def sigmoid(z):
    return 1.0 / (1.0 + math.exp(-z))

def softmax(scores):
    s = np.array(scores, dtype=float)
    s -= np.max(s)
    ex = np.exp(tau * s)
    return ex / (np.sum(ex) + 1e-12)

def dist(a, b): return float(np.linalg.norm(a - b))

def threat_proximity(p):
    # 1.0 at center, 0.0 outside radius (with a smooth falloff)
    d = dist(p, THREAT)
    if d >= THREAT_R: return 0.0
    return float(1.0 - (d / THREAT_R))

def pressure_m(p, hunger):
    """
    Pressure increases with hunger (need) and also with threat proximity (stress).
    """
    prox = threat_proximity(p)
    # hunger pushes exploration, threat pushes defensive pressure too
    m = 0.25 + 1.20*hunger + 0.90*prox
    return float(np.clip(m, 0.0, 3.0))

def mcrit(k_eff):
    # Same sufficient boundary used earlier: m < (1/k_eff) - gamma/2
    return float((1.0 / max(k_eff, 1e-9)) - (gamma / 2.0))

def truth_target(p, hunger):
    """
    Truth is 'what the world says matters': move toward food if hungry,
    and move away from threat.
    Returns x_T target position.
    """
    # attract to food if available and hungry
    toward_food = np.zeros(2)
    if food_available:
        toward_food = unit(FOOD - p)

    away_threat = unit(p - THREAT)

    prox = threat_proximity(p)
    # weight food-seeking by hunger; threat-avoidance by proximity
    v = (1.4*hunger)*toward_food + (2.0*prox)*away_threat
    if np.linalg.norm(v) < 1e-9:
        v = np.zeros(2)

    # target is a point a few steps in that direction
    return p + 6.0 * v

def reflection_target(p, hunger):
    """
    Reflection = identity + subjective preferences:
    - prefer to hang near home
    - avoid threat even if not currently in it
    - but if hunger high, 'allow' moving outward a bit
    """
    to_home = unit(HOME - p)
    away_threat = unit(p - THREAT)

    # "courage" grows with hunger (need can override comfort)
    courage = 0.30 + 0.80*hunger

    v = (1.6*(1.0-courage))*to_home + (1.0)*away_threat + (0.6*courage)*unit(FOOD - p)
    return p + 5.0 * v

def compute_QS(p, xT, xR):
    """
    Score each action by objective (truth) and subjective (reflection/identity).
    """
    Q, S = [], []
    for name, d in ACTIONS:
        # predict one-step motion direction (intended)
        step = STEP_SIZE * d
        p1 = p + step

        # Objective: closer to truth target, farther from threat
        q = -dist(p1, xT)
        q += 1.2 * dist(p1, THREAT)  # reward being away from threat

        # Subjective: closer to reflection target and home comfort
        s = -dist(p1, xR)
        s += 0.5 * (-dist(p1, HOME))

        # mild penalty for STAY if hunger is high
        if name == "STAY":
            q -= 2.0*hunger

        Q.append(q)
        S.append(s)
    return np.array(Q), np.array(S)

def choose_action(p, hunger):
    xT = truth_target(p, hunger)
    xR = reflection_target(p, hunger)
    Q, S = compute_QS(p, xT, xR)

    scores = w_obj*Q + w_subj*S
    pi = softmax(scores)
    a = int(np.argmax(pi))  # greedy for clarity
    return a, xT, xR, Q, S, pi

def step_world(p, a_idx):
    """
    Execute action with slips + threat shock (unpredictable).
    Returns (p_next_actual, p_next_predicted).
    """
    name, d = ACTIONS[a_idx]
    intended = STEP_SIZE * d

    # predicted: what agent expects (no slip, no shock)
    p_pred = p + intended

    # actual: slip sometimes
    p_act = p + intended
    if rng.random() < SLIP_PROB:
        p_act = p_act + rng.normal(scale=SLIP_NOISE, size=2)

    # threat shock if inside threat zone
    prox = threat_proximity(p_act)
    if prox > 0.001:
        # random push whose magnitude depends on proximity
        shock = rng.normal(size=2)
        shock = unit(shock) * (THREAT_SHOCK * prox)
        p_act = p_act + shock

    # clip to bounds
    p_act[0] = float(np.clip(p_act[0], 0.0, W))
    p_act[1] = float(np.clip(p_act[1], 0.0, H))
    p_pred[0] = float(np.clip(p_pred[0], 0.0, W))
    p_pred[1] = float(np.clip(p_pred[1], 0.0, H))

    return p_act, p_pred

# -----------------------------
# Simulation state
# -----------------------------
p = np.array([18.0, 24.0], dtype=float)
traj = []
step = 0
t_last = time.time()

async def handler(websocket):
    global p, rho, hunger, reward, food_available, food_cooldown, step, t_last, traj

    print("Client connected")
    try:
        while True:
            now = time.time()
            dt_sec = now - t_last
            t_last = now

            # handle food respawn timer
            if not food_available:
                food_cooldown -= dt_sec
                if food_cooldown <= 0.0:
                    food_available = True

            # hunger rises
            hunger = clamp01(hunger + hunger_rate)

            # choose action
            a_idx, xT, xR, Q, S, pi = choose_action(p, hunger)

            # pressure m depends on hunger and threat proximity
            m = pressure_m(p, hunger)

            # effective openness
            k_eff = k_base * (1.0 - rho)

            # DDA "desired move" vector (in position space)
            F_id = gamma * (HOME - p)
            F_T = (xT - p)
            F_R = (xR - p)

            delta = F_id + m*(F_T + F_R)

            # commit to chosen action a bit (discrete decision projection)
            commit = 0.8 * ACTIONS[a_idx][1]
            delta2 = delta + commit

            # predicted next pos from DDA step (this is its internal forward model)
            p_model_pred = p + k_eff * unit(delta2) * STEP_SIZE

            # world step: actual and naive predicted from action
            p_act, p_action_pred = step_world(p, a_idx)

            # define "actual encoded outcome" as actual position
            # and "predicted" as model predicted (better matches DDA)
            eps = float(np.linalg.norm(p_model_pred - p_act))

            # rigidity update (centered sigmoid -> bidirectional)
            z = (eps - eps0) / s_sig
            rho = rho + alpha * (sigmoid(z) - 0.5)
            rho = clamp01(rho)
            rho = clamp01((1.0 - rho_decay) * rho)

            # update agent state to actual outcome
            p = p_act

            # eat food if near and available
            ate = False
            if food_available and dist(p, FOOD) <= FOOD_RADIUS:
                ate = True
                reward += 1
                hunger = clamp01(hunger - hunger_relief)
                food_available = False
                food_cooldown = FOOD_RESPAWN_SEC

            # diagnostics
            mc = mcrit(k_eff)
            prox = threat_proximity(p)

            traj.append(p.copy())
            if len(traj) > 2500:
                traj = traj[-2500:]

            step += 1

            if step % SIM_STEPS_PER_SEND == 0:
                msg = {
                    "step": step,
                    "p": [float(p[0]), float(p[1])],
                    "home": [float(HOME[0]), float(HOME[1])],
                    "food": [float(FOOD[0]), float(FOOD[1])],
                    "food_available": bool(food_available),
                    "threat": [float(THREAT[0]), float(THREAT[1])],
                    "threat_r": float(THREAT_R),

                    "action": ACTIONS[a_idx][0],
                    "ate": ate,
                    "reward": int(reward),
                    "hunger": float(hunger),
                    "threat_prox": float(prox),

                    "rho": float(rho),
                    "k_eff": float(k_eff),
                    "m": float(m),
                    "m_crit": float(mc),
                    "eps": float(eps),
                }
                await websocket.send(json.dumps(msg))

            await asyncio.sleep(1.0 / FPS)

    except websockets.ConnectionClosed:
        print("Client disconnected")
        return

async def main():
    async with websockets.serve(handler, "localhost", 8765):
        print("WebSocket server running on ws://localhost:8765")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
