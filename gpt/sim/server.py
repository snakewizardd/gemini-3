
# server.py
# pip install websockets numpy
import asyncio
import json
import math
import random
import time

import numpy as np
import websockets

# -----------------------------
# DDA SIM CONFIG
# -----------------------------
DT = 1.0
D = 8                       # latent dimension
J = 10                      # number of actions
FPS = 30                    # stream rate
SEND_EVERY = 1              # send every N sim steps

# Identity attractor
x_star = np.array([1.2, 0.2, -0.7, 0.4, 0.9, -0.3, 0.1, -0.5], dtype=float)

# Dynamics parameters
gamma = 0.55                # identity stiffness
k_base = 0.22               # baseline openness step
rho = 0.10                  # rigidity in [0,1]

# Rigidity adaptation (centered sigmoid)
alpha = 0.06                # rigidity learning rate
eps0 = 0.55                 # "threat threshold" for surprise
s_sig = 0.25                # sensitivity scale
rho_decay = 0.004           # slow recovery per step (optional but nice)

# Pressure / gain
m_base = 0.55               # baseline external pressure
m_pulse = 0.65              # pulse amplitude (to show regime changes)
pulse_period = 9.0          # seconds

# Truth / reflection weights inside reflection score
w_obj = 1.0
w_subj = 0.9
tau = 2.0                   # softmax sharpness

# Noise levels (simulate imperfect world + observation)
truth_noise = 0.10
outcome_noise = 0.18

# Projection to 2D (fixed random orthonormal projection)
rng = np.random.default_rng(7)
P = rng.normal(size=(2, D))
# Orthonormalize rows
u, _, vh = np.linalg.svd(P, full_matrices=False)
P = (u @ vh).astype(float)

# -----------------------------
# Helpers
# -----------------------------
def unit(v, eps=1e-9):
    n = np.linalg.norm(v)
    return v / (n + eps)

def cos_sim(a, b, eps=1e-9):
    return float(np.dot(a, b) / ((np.linalg.norm(a) + eps) * (np.linalg.norm(b) + eps)))

def sigmoid(z):
    return 1.0 / (1.0 + math.exp(-z))

def softmax(scores):
    scores = np.array(scores, dtype=float)
    scores = scores - np.max(scores)
    ex = np.exp(tau * scores)
    return ex / (np.sum(ex) + 1e-12)

def m_t(now_s: float) -> float:
    # smooth pressure changes so you can watch behavior shift
    pulse = 0.5 * (1.0 + math.sin(2 * math.pi * now_s / pulse_period))
    return m_base + m_pulse * pulse

# -----------------------------
# DDA Components
# -----------------------------
# action directions (fixed)
action_dirs = rng.normal(size=(J, D))
action_dirs = np.array([unit(v) for v in action_dirs], dtype=float)

def T_truth_target(x, now_s):
    """
    Truth target: a drifting target + some noise.
    In real usage: parse external world into state space.
    """
    drift = np.array([
        0.6 * math.sin(0.35 * now_s),
        0.6 * math.cos(0.28 * now_s),
        0.3 * math.sin(0.15 * now_s + 1.0),
        -0.4 * math.cos(0.22 * now_s),
        0.2 * math.sin(0.40 * now_s),
        0.3 * math.cos(0.31 * now_s),
        -0.2 * math.sin(0.19 * now_s),
        0.15 * math.cos(0.17 * now_s),
    ], dtype=float)

    noise = rng.normal(scale=truth_noise, size=D)
    return 0.8 * x_star + drift + noise

def reflection_target(x, now_s, Q_vals, S_vals):
    """
    Reflection returns an internal target state formed from a preference over actions.
    """
    scores = [w_obj * Q_vals[j] + w_subj * S_vals[j] for j in range(J)]
    pi = softmax(scores)  # distribution over actions
    direction = (pi[:, None] * action_dirs).sum(axis=0)
    direction = unit(direction)
    # Small step in preferred direction from current x
    return x + 0.9 * direction

def compute_Q_S(x, xT):
    """
    Produce objective and subjective scores for each action.
    Q: moves toward truth target (objective).
    S: moves toward identity (subjective / alignment).
    """
    # desired directions
    to_truth = unit(xT - x)
    to_id = unit(x_star - x)

    Q = []
    S = []
    for j in range(J):
        d = action_dirs[j]
        # objective: align with truth direction, penalize moving away from identity hard
        q = cos_sim(d, to_truth) - 0.15 * max(0.0, -cos_sim(d, to_id))
        # subjective: align with identity direction + some idiosyncratic preference bump
        s = cos_sim(d, to_id) + 0.10 * math.sin(3.0 * j)
        Q.append(q)
        S.append(s)
    return np.array(Q, dtype=float), np.array(S, dtype=float)

def choose_action(delta_x):
    """
    Cosine alignment with the instantaneous desired movement delta_x.
    """
    if np.linalg.norm(delta_x) < 1e-9:
        return 0
    scores = [cos_sim(delta_x, action_dirs[j]) for j in range(J)]
    return int(np.argmax(scores))

def mcrit(k_eff):
    """
    From contraction sufficient condition:
    0 < k_eff (gamma + 2 m) < 2  =>  m < (1/k_eff) - gamma/2
    """
    return (1.0 / max(k_eff, 1e-9)) - (gamma / 2.0)

# -----------------------------
# Simulation loop state
# -----------------------------
x = np.zeros(D, dtype=float)
x[:] = rng.normal(scale=0.25, size=D)

step = 0

async def handler(websocket):
    global x, rho, step

    print("Client connected")
    last_send = 0

    try:
        while True:
            now = time.time()
            now_s = now  # absolute time is fine for a visual sim

            # pressure
            m = m_t(now_s)

            # effective openness
            k_eff = k_base * (1.0 - rho)

            # truth target and scores
            xT = T_truth_target(x, now_s)
            Q, S = compute_Q_S(x, xT)

            # reflection target
            xR = reflection_target(x, now_s, Q, S)

            # forces
            F_id = gamma * (x_star - x)
            F_T = (xT - x)
            F_R = (xR - x)

            # desired movement (pre-action)
            delta = F_id + m * (F_T + F_R)

            # choose action by cosine alignment with delta
            a = choose_action(delta)

            # incorporate chosen action as a small bias on reflection (acts like commitment)
            commit = 0.35 * action_dirs[a]
            delta2 = delta + commit

            # forward prediction (model uses same update)
            x_pred = x + k_eff * delta2

            # "world" outcome: predicted + noise + small truth pull (world pushes back)
            world_push = 0.10 * (xT - x)
            x_act = x_pred + world_push + rng.normal(scale=outcome_noise, size=D)

            # prediction error
            eps = float(np.linalg.norm(x_pred - x_act))

            # rigidity update (centered sigmoid -> bidirectional)
            z = (eps - eps0) / s_sig
            rho = rho + alpha * (sigmoid(z) - 0.5)
            rho = float(np.clip(rho, 0.0, 1.0))
            # optional decay (recovery)
            rho = float(np.clip((1.0 - rho_decay) * rho, 0.0, 1.0))

            # update actual state (use actual realized next state)
            x = x_act

            # diagnostics
            mc = float(mcrit(k_eff))

            # project to 2D
            p2 = (P @ x).tolist()

            # send
            step += 1
            if step - last_send >= SEND_EVERY:
                msg = {
                    "t": now,
                    "step": step,
                    "p": p2,                 # 2D point
                    "rho": rho,
                    "k_eff": float(k_eff),
                    "m": float(m),
                    "m_crit": mc,
                    "eps": eps,
                    "action": a,
                }
                await websocket.send(json.dumps(msg))
                last_send = step

            await asyncio.sleep(1.0 / FPS)

    except websockets.ConnectionClosed:
        print("Client disconnected")
        return

async def main():
    async with websockets.serve(handler, "localhost", 8765):
        print("WebSocket server running on ws://localhost:8765")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
