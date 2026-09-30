# Ping Pong

A small table-tennis game written in Python with [Pygame](https://www.pygame.org/).
You play the near side. An agent named ACE plays the far side, reads the bounce,
and tries to get there before you do.

The ball leaves your paddle, has to clear the net, and has to land on the far half.
Its shadow runs in a straight line across the felt. That shadow is the read.
ACE does the read with a delay. You do it by eye.

## Features

- **You against ACE.** The line under ACE's name is what it is thinking: an early read, a correction at the net, a stretch, or that your shot is going out.
- **Three agents**, picked on the title screen. **Warmup** chases the ball late. **Match** reads the bounce, then adjusts. **Agent** calls the landing early, so you have to pull it wide before a winner will land.
- **A real flight.** Shots arc. A drive has to clear the net. The white ball floats above a dark shadow, and the two meet when it bounces.
- **Aim with the paddle.** Stand to one side to shape your serve. In a rally, meet the ball with the edge of the paddle to send it wide. You can lunge past the sideline to redirect a wide ball back across the table.
- **Pace.** Each clean hit comes back faster. A gentle block keeps the rally going. A change of direction, once the pace is up, is how you score.
- **First to 11, win by 2.** Serve changes every two points, and every point once both sides reach 10.
- **Wins and best rally** are saved on this computer.
- **No asset files.** The table, the ball, and the sounds are drawn and synthesized in code. Press `M` to mute.

## Getting started

You need **Python 3.8+**.

```bash
git clone https://github.com/yugdogra0/ping-pong.git
cd ping-pong
pip install -r requirements.txt
python game.py
```

## Controls

| Action | Keys / mouse |
| --- | --- |
| Move | Mouse, or `A` `D` or the arrow keys |
| Serve | `Space` or click |
| Pick an agent | Click a card, or press `1` `2` `3` |
| Start / play again | Click **Play** or **Again** (or press `Enter` or `Space`) |
| Pause | `Esc`, then **Resume** or **Title** |
| Mute / unmute | `M` |
| Quit | `Esc` on the title screen |

## How to play

- You are the cyan paddle. ACE is the amber one, with the little eye.
- Before you serve, slide along your end. A cyan ring shows where the ball will bounce. Press `Space`.
- Watch the shadow, not only the white ball. The shadow is where the ball is on the table.
- Hit the middle of your paddle to send the ball back toward the middle. Hit it with the edge to send it wide.
- ACE can return a ball it is already standing under. Pull it to one side, then hit the other way.
- Warmup misses a wide shot. Match needs the pace to come up before a change of direction gets through. Agent covers more of the table, and still misses a fast ball hit behind it.
- If the ball does not land on the far half, the point is gone. ACE will say so.

## Tweaking the game

Feel and rules live in `pingpong/settings.py`:

```python
TARGET = 11                # points needed
WIN_BY = 2
FLIGHT_SLOW = 0.90         # seconds for a serve-speed shot to cross
FLIGHT_FAST = 0.62         # seconds once the pace is full
PACE_STEP = 0.085          # how fast each hit heats the rally up
AIM_EDGE = 0.94            # how wide a full-edge hit aims
PLAYER_SPEED = 1100        # keyboard glide; the mouse puts you on the cursor
```

How hard ACE plays is the `LEVELS` table in that same file: reaction time, move speed, and how early it trusts its read.

## Project structure

```
ping-pong/
├── game.py              # launcher: python game.py
├── pingpong/            # the game package (also runs with: python -m pingpong)
│   ├── game.py          # window, table, menus
│   ├── rally.py         # ball, paddles, and ACE
│   ├── audio.py         # synthesized hits and scores
│   ├── scores.py        # wins and best rally saved on this computer
│   └── settings.py      # window size, colours, and tuning knobs
├── requirements.txt     # pygame dependency
└── README.md
```
