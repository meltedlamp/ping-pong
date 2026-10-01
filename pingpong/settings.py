"""Window, colours, and the knobs that change how a rally feels."""

WIDTH, HEIGHT = 860, 940
FPS = 60
TITLE = "Ping Pong"

TABLE_X, TABLE_Y = 70, 128
TABLE_W, TABLE_H = 720, 670
LINE_INSET = 22
PADDLE_INSET = 40
PADDLE_W = 116
PADDLE_H = 16
BALL_R = 9

# A shot leaves the paddle, clears the net, and bounces on the far half.
GRAVITY = 900.0
RESTITUTION = 0.56
BOUNCE_FRAC = 0.93
HIT_Z = 12.0
NET_H = 26.0
STRIKE_Z = 80.0
FLIGHT_SLOW = 0.90
FLIGHT_FAST = 0.62
PACE_STEP = 0.085
# 1.0 aims a full-edge hit at the sideline. Just under that keeps the corner in.
AIM_EDGE = 0.94
SERVE_AIM = 0.70
ACE_MISHIT = 0.2
REACH_EXTRA = 12.0

TARGET = 11
WIN_BY = 2

# Keyboard glide. The mouse puts the paddle on the cursor.
PLAYER_SPEED = 1100.0

BG = (8, 14, 18)
FELT = (16, 108, 80)
FELT_DARK = (10, 74, 56)
APRON = (124, 80, 48)
APRON_EDGE = (74, 46, 30)
LINE = (236, 240, 230)
YOU = (86, 214, 255)
ACE = (255, 176, 72)
BALL = (246, 247, 242)
TEXT = (236, 240, 242)
MUTED = (154, 170, 164)
GOLD = (255, 214, 120)
FAULT = (255, 124, 108)
INK = (6, 10, 12)
WHITE = (248, 250, 246)

LEVEL_ORDER = ("warmup", "match", "agent")

LEVELS = {
    "warmup": {
        "label": "WARMUP",
        "blurb": "Chases the ball late. A wide angle gets through.",
        "reaction": 0.28,
        "error_far": 34.0,
        "error_near": 16.0,
        "speed": 340.0,
        "drift": 0.30,
        "predict": False,
        "aim_margin": 150.0,
        "aim_error": 34.0,
        "mixup": 0.45,
        "serve_margin": 190.0,
    },
    "match": {
        "label": "MATCH",
        "blurb": "Reads the bounce, then corrects as it crosses the net.",
        "reaction": 0.15,
        "error_far": 26.0,
        "error_near": 7.0,
        "speed": 500.0,
        "drift": 0.16,
        "predict": True,
        "aim_margin": 52.0,
        "aim_error": 16.0,
        "mixup": 0.18,
        "serve_margin": 130.0,
    },
    "agent": {
        "label": "AGENT",
        "blurb": "Calls the landing early. Pull it wide, then hit behind it.",
        "reaction": 0.07,
        "error_far": 11.0,
        "error_near": 3.0,
        "speed": 680.0,
        "drift": 0.12,
        "predict": True,
        "aim_margin": 22.0,
        "aim_error": 8.0,
        "mixup": 0.10,
        "serve_margin": 78.0,
    },
}
