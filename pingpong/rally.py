"""The table, the ball, and ACE.

A shot is an arc. It has to clear the net and bounce once on the far half.
The shadow travels in a straight line, so the landing can be read. ACE does
that read with a delay. You do it by eye.
"""

import math
import random

from .settings import (
    ACE_MISHIT, AIM_EDGE, BALL_R, BOUNCE_FRAC, FLIGHT_FAST, FLIGHT_SLOW, GRAVITY,
    HIT_Z, LEVELS, LINE_INSET, NET_H, PACE_STEP, PADDLE_H, PADDLE_INSET, PADDLE_W,
    REACH_EXTRA, RESTITUTION, SERVE_AIM, STRIKE_Z, TARGET, WIN_BY,
)


def clamp(value, lo, hi):
    return lo if value < lo else hi if value > hi else value


def match_winner(you, ace):
    if you >= TARGET and you - ace >= WIN_BY:
        return "you"
    if ace >= TARGET and ace - you >= WIN_BY:
        return "ace"
    return None


def time_to_table(z, vz):
    disc = vz * vz + 2.0 * GRAVITY * max(0.0, z)
    return (vz + math.sqrt(disc)) / GRAVITY


class Ball:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.z = HIT_Z
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.r = BALL_R
        self.spin = 0.0
        self.bounced = False


class Paddle:
    def __init__(self, cx, cy):
        self.cx = float(cx)
        self.cy = float(cy)
        self.w = float(PADDLE_W)
        self.h = float(PADDLE_H)
        self.vx = 0.0

    @property
    def top(self):
        return self.cy - self.h / 2

    @property
    def bottom(self):
        return self.cy + self.h / 2

    def place(self, cx, dt, left, right):
        prev = self.cx
        self.cx = clamp(cx, left, right)
        self.vx = (self.cx - prev) / dt if dt > 0 else 0.0

    def slide(self, target, speed, dt, left, right):
        prev = self.cx
        delta = target - self.cx
        step = speed * dt
        if abs(delta) <= step:
            self.cx = target
        elif delta > 0:
            self.cx += step
        else:
            self.cx -= step
        self.cx = clamp(self.cx, left, right)
        self.vx = (self.cx - prev) / dt if dt > 0 else 0.0


class Agent:
    """ACE's read. The delay is the part you can play against."""

    def __init__(self, level, seed):
        spec = LEVELS[level]
        self.reaction = spec["reaction"]
        self.error_far = spec["error_far"]
        self.error_near = spec["error_near"]
        self.speed = spec["speed"]
        self.drift_scale = spec["drift"]
        self.predict = spec["predict"]
        self.aim_margin = spec["aim_margin"]
        self.aim_error = spec["aim_error"]
        self.mixup = spec["mixup"]
        self.serve_margin = spec["serve_margin"]
        self.rng = random.Random(seed)
        self.timer = 0.0
        self.target = 0.0
        self.committed = False
        self.refined = False
        self.leaving = False
        self.stretched = False

    @property
    def drift(self):
        return self.speed * self.drift_scale

    def arm(self):
        self.timer = self.reaction
        self.committed = False
        self.refined = False
        self.leaving = False


YOU_WIN = {
    "miss": ("clean.", "too wide.", "I was late."),
    "out": ("I put that wide.",),
    "net": ("caught the net.",),
    "long": ("I hit it long.",),
}
ACE_WIN = {
    "miss": ("point.", "you left that.", "right past you."),
    "out": ("wide.", "that's out."),
    "net": ("into the net.",),
    "long": ("long.",),
}
LONG = ("still with you.", "long rally.", "pace is up.")


class Rally:
    def __init__(self, level, bounds, seed=None):
        self.level = level
        self.label = LEVELS[level]["label"]
        self.left, self.top, self.right, self.bottom = bounds
        self.cx = (self.left + self.right) / 2
        self.inner_left = self.left + LINE_INSET
        self.inner_right = self.right - LINE_INSET
        self.inner_top = self.top + LINE_INSET
        self.inner_bottom = self.bottom - LINE_INSET
        self.half = (self.inner_right - self.inner_left) / 2
        # The paddle can lunge past the sideline, so a wide ball can still be
        # redirected cross-court instead of only pushed further wide.
        self.pad_left = self.inner_left - PADDLE_W * 0.42
        self.pad_right = self.inner_right + PADDLE_W * 0.42
        self.ace_pad = Paddle(self.cx, self.top + PADDLE_INSET)
        self.player = Paddle(self.cx, self.bottom - PADDLE_INSET)
        self.ace_strike = self.ace_pad.bottom
        self.you_strike = self.player.top
        self.net_y = (self.ace_strike + self.you_strike) / 2
        self.ball = Ball()
        self.rng = random.Random(seed)
        agent_seed = None if seed is None else seed + 17
        self.agent = Agent(level, agent_seed)
        self.agent.target = self.cx
        self.you = 0
        self.ace = 0
        self.server = "you"
        self.phase = "serve"
        self.winner = None
        self.last_winner = "you"
        self.last_reason = "miss"
        self.last_hitter = "you"
        self.rally_hits = 0
        self.best_hits = 0
        self.pace = 0.0
        self.quip = "your serve."
        self.quip_t = 2.2
        self._last_quip = ""
        self.said_long = False
        self.serve_wait = 0.0
        self.serve_place = self.cx
        self.serve_arrive = self.cx
        self.point_t = 0.0
        self.events = []
        self.time = 0.0
        self.last_net_z = HIT_Z
        self._stick()

    def live_best(self):
        return max(self.best_hits, self.rally_hits)

    def say(self, text, hold=1.7):
        self._last_quip = text
        self.quip = text
        self.quip_t = hold

    def _pick(self, options):
        choices = [line for line in options if line != self._last_quip] or list(options)
        self.say(self.rng.choice(choices))

    def caption(self):
        if self.quip_t > 0 and self.quip:
            return self.quip
        if self.phase == "serve":
            return "my serve." if self.server == "ace" else "your serve."
        if self.phase != "rally":
            return self.quip
        agent = self.agent
        coming = self.ball.vy < 0
        if not coming:
            return "recovering."
        if agent.leaving and agent.committed:
            return "that's going out."
        if agent.stretched:
            return "stretching."
        if not agent.committed:
            return "watching."
        if agent.predict and not agent.refined:
            return "early read."
        if agent.predict and agent.refined:
            return "locked in."
        return "tracking."

    def _stick(self):
        pad = self.player if self.server == "you" else self.ace_pad
        ball = self.ball
        ball.x = pad.cx
        ball.vx = ball.vy = ball.vz = 0.0
        ball.bounced = False
        ball.z = 34.0 + math.sin(self.time * 2.6) * 4.0
        if self.server == "you":
            ball.y = self.you_strike - 8
        else:
            ball.y = self.ace_strike + 8

    def _begin_serve(self):
        self.phase = "serve"
        self.rally_hits = 0
        self.pace = 0.0
        self.said_long = False
        self.agent.arm()
        self.agent.timer = 0.0
        if self.server == "ace":
            self.serve_arrive = self._aim(self.player.cx, self.agent.serve_margin, self.agent.aim_error * 0.4, 0.35)
            self.serve_place = clamp(self.cx + self.rng.uniform(-50, 50), self.pad_left, self.pad_right)
            self.serve_wait = self.rng.uniform(0.55, 0.95)
            self.say("my serve.", 2.0)
        else:
            self.serve_place = self.cx
            self.serve_wait = 0.0
            self.say("your serve.", 2.0)
        self._stick()

    def _next_server(self):
        deuce = self.you >= TARGET - 1 and self.ace >= TARGET - 1
        if deuce or (self.you + self.ace) % 2 == 0:
            self.server = "ace" if self.server == "you" else "you"

    def _comment(self, winner, reason):
        table = YOU_WIN if winner == "you" else ACE_WIN
        self._pick(table.get(reason, ("point.",)))

    def _award(self, winner, reason):
        self.best_hits = max(self.best_hits, self.rally_hits)
        self.last_winner = winner
        self.last_reason = reason
        if winner == "you":
            self.you += 1
        else:
            self.ace += 1
        self._comment(winner, reason)
        self.events.append(("point", winner, reason, self.ball.x, self.ball.y))
        self._next_server()
        self.phase = "point"
        self.point_t = 1.0
        found = match_winner(self.you, self.ace)
        if found:
            self.winner = found
            self.say("good match." if found == "you" else "I kept the read.", 5.0)
            self.events.append(("match", found))

    def _fair(self, x, y, hitter):
        if not (self.inner_left <= x <= self.inner_right and self.inner_top <= y <= self.inner_bottom):
            return False
        if hitter == "you":
            return y < self.net_y - 6
        return y > self.net_y + 6

    def _aim(self, player_x, margin, error, mixup):
        side = 1.0 if player_x < self.cx else -1.0
        if self.agent.rng.random() < mixup:
            side *= -1
        reach = max(40.0, self.half - margin)
        aim = self.cx + side * reach
        aim += self.agent.rng.uniform(-error, error)
        return clamp(aim, self.inner_left + 28, self.inner_right - 28)

    def _player_serve_arrive(self):
        place = clamp((self.player.cx - self.cx) / self.half, -1.0, 1.0)
        return self.cx + place * SERVE_AIM * self.half

    def _player_return_arrive(self, contact_x):
        offset = clamp((contact_x - self.player.cx) / (self.player.w / 2), -1.0, 1.0)
        return self.cx + offset * self.half * AIM_EDGE

    def serve_ghost(self):
        """Where your serve will bounce, so the aim is visible before you hit it."""
        if self.phase != "serve" or self.server != "you":
            return None
        arrive_x = self._player_serve_arrive()
        start_x = self.player.cx
        start_y = self.you_strike
        bx = start_x + (arrive_x - start_x) * BOUNCE_FRAC
        by = start_y + (self.ace_strike - start_y) * BOUNCE_FRAC
        return bx, by, self._fair(bx, by, "you")

    def _fly_toward(self, arrive_x, who, serving):
        ball = self.ball
        ball.z = HIT_Z
        if who == "you":
            ball.y = self.you_strike - 3
            arrive_y = self.ace_strike
        else:
            ball.y = self.ace_strike + 3
            arrive_y = self.you_strike
        flight = FLIGHT_SLOW + (FLIGHT_FAST - FLIGHT_SLOW) * self.pace
        tb = max(0.05, flight * BOUNCE_FRAC)
        ball.vx = (arrive_x - ball.x) / flight
        ball.vy = (arrive_y - ball.y) / flight
        ball.vz = 0.5 * GRAVITY * tb - ball.z / tb
        ball.bounced = False
        self.last_hitter = who
        self.phase = "rally"
        if serving:
            self.quip_t = 0.0
        kind = "serve" if serving else "hit"
        if not serving:
            self.rally_hits += 1
            self.pace = min(1.0, self.pace + PACE_STEP)
            if self.rally_hits == 8 and not self.said_long:
                self.said_long = True
                self._pick(LONG)
        if who == "you":
            self.agent.arm()
        self.events.append((kind, who, ball.x, ball.y))

    def _return(self, who, contact_x):
        self.ball.x = contact_x
        if who == "you":
            arrive = self._player_return_arrive(contact_x)
        else:
            arrive = self._aim(self.player.cx, self.agent.aim_margin, self.agent.aim_error, self.agent.mixup)
            offset = clamp((contact_x - self.ace_pad.cx) / (self.ace_pad.w / 2), -1.0, 1.0)
            arrive += offset * self.half * ACE_MISHIT
        self._fly_toward(arrive, who, serving=False)

    def _launch_serve(self, who):
        if who == "you":
            self.ball.x = self.player.cx
            arrive = self._player_serve_arrive()
        else:
            self.ball.x = self.ace_pad.cx
            arrive = self.serve_arrive
        self._fly_toward(arrive, who, serving=True)

    def _sample(self, prev_y, line, prev_x, prev_z):
        ball = self.ball
        span = ball.y - prev_y
        t = 0.0 if abs(span) < 1e-8 else (line - prev_y) / span
        t = clamp(t, 0.0, 1.0)
        x = prev_x + (ball.x - prev_x) * t
        z = prev_z + (ball.z - prev_z) * t
        return x, z

    def _try_strike(self, who, prev_x, prev_y, prev_z):
        ball = self.ball
        line = self.you_strike if who == "you" else self.ace_strike
        if who == "you":
            crossed = prev_y < line <= ball.y
        else:
            crossed = prev_y > line >= ball.y
        if not crossed:
            return False
        if not ball.bounced:
            # It reached the far end without landing. The hitter missed the table.
            self._award(who, "long")
            return True
        x, z = self._sample(prev_y, line, prev_x, prev_z)
        pad = self.player if who == "you" else self.ace_pad
        if z > STRIKE_Z:
            self._award(self._other(who), "miss")
            return True
        if abs(x - pad.cx) <= pad.w / 2 + REACH_EXTRA:
            self._return(who, x)
            return True
        self._award(self._other(who), "miss")
        return True

    def _other(self, who):
        return "ace" if who == "you" else "you"

    def _going_out(self):
        ball = self.ball
        if ball.bounced or ball.vz == 0 and ball.z <= 0:
            return False
        t = time_to_table(ball.z, ball.vz)
        if t <= 0:
            return False
        x = ball.x + ball.vx * t
        y = ball.y + ball.vy * t
        return not self._fair(x, y, self.last_hitter)

    def _arrival_x(self, strike):
        ball = self.ball
        if abs(ball.vy) < 1:
            return ball.x
        t = (strike - ball.y) / ball.vy
        if t < 0:
            return ball.x
        return ball.x + ball.vx * t

    def _drive_ace(self, dt):
        agent = self.agent
        pad = self.ace_pad
        if self.phase == "serve" and self.server == "ace":
            pad.slide(self.serve_place, agent.speed, dt, self.pad_left, self.pad_right)
            agent.target = self.serve_place
            agent.stretched = False
            return
        coming = self.phase == "rally" and self.ball.vy < 0
        agent.timer -= dt
        if not coming:
            agent.target = self.cx
            agent.committed = False
            agent.leaving = False
            pad.slide(self.cx, agent.drift, dt, self.pad_left, self.pad_right)
            agent.stretched = False
            return
        if not agent.predict:
            if agent.timer <= 0:
                agent.timer = agent.reaction
                agent.committed = True
                far = self.ball.y > self.net_y
                err = agent.error_far if far else agent.error_near
                agent.target = self.ball.x + agent.rng.uniform(-err, err)
            speed = agent.speed if agent.committed else agent.drift
            if not agent.committed:
                agent.target = self.cx
        else:
            if not agent.committed:
                agent.target = self.cx
                speed = agent.drift
                if agent.timer <= 0:
                    agent.committed = True
                    agent.timer = agent.reaction
                    if self._going_out():
                        agent.leaving = True
                        agent.target = self.cx
                    else:
                        agent.leaving = False
                        err = agent.error_far * (0.8 + 0.5 * self.pace)
                        agent.target = self._arrival_x(self.ace_strike) + agent.rng.uniform(-err, err)
            else:
                speed = agent.drift if agent.leaving else agent.speed
                if agent.leaving:
                    agent.target = self.cx
                elif (not agent.refined) and self.ball.y <= self.net_y and agent.timer <= 0:
                    agent.refined = True
                    err = agent.error_near
                    agent.target = self._arrival_x(self.ace_strike) + agent.rng.uniform(-err, err)
        pad.slide(agent.target, speed, dt, self.pad_left, self.pad_right)
        agent.stretched = abs(pad.cx - agent.target) > pad.w * 0.72

    def _bounce(self):
        ball = self.ball
        ball.z = 0.0
        if not ball.bounced and self._fair(ball.x, ball.y, self.last_hitter):
            ball.vz = abs(ball.vz) * RESTITUTION
            ball.bounced = True
            self.events.append(("bounce", ball.x, ball.y))
            return
        if not ball.bounced:
            self._award(self._other(self.last_hitter), "out")
        else:
            self._award(self.last_hitter, "miss")

    def _substep(self, dt):
        ball = self.ball
        prev_x, prev_y, prev_z = ball.x, ball.y, ball.z
        ball.x += ball.vx * dt
        ball.y += ball.vy * dt
        ball.z += ball.vz * dt - 0.5 * GRAVITY * dt * dt
        ball.vz -= GRAVITY * dt
        ball.spin += dt * (abs(ball.vx) + abs(ball.vy)) * 0.01
        if not ball.bounced and (prev_y - self.net_y) * (ball.y - self.net_y) <= 0 and prev_y != ball.y:
            _, z_net = self._sample(prev_y, self.net_y, prev_x, prev_z)
            self.last_net_z = z_net
            if z_net < NET_H:
                self._award(self._other(self.last_hitter), "net")
                return
        if ball.vy > 0:
            if self._try_strike("you", prev_x, prev_y, prev_z):
                return
        elif ball.vy < 0:
            if self._try_strike("ace", prev_x, prev_y, prev_z):
                return
        if self.phase == "rally" and ball.z <= 0 and ball.vz <= 0:
            self._bounce()

    def _fly(self, dt):
        left = dt
        guard = 0
        while left > 1e-5 and self.phase == "rally" and guard < 48:
            step = min(left, 1.0 / 180.0)
            self._substep(step)
            left -= step
            guard += 1

    def step(self, dt, player_cx, serve):
        self.events = []
        if dt <= 0:
            dt = 1 / 60
        dt = min(float(dt), 0.05)
        self.time += dt
        if self.quip_t > 0:
            self.quip_t -= dt
        self.player.place(player_cx, dt, self.pad_left, self.pad_right)
        self._drive_ace(dt)
        if self.phase == "serve":
            self._stick()
            if self.server == "you" and serve:
                self._launch_serve("you")
            elif self.server == "ace":
                self.serve_wait -= dt
                if self.serve_wait <= 0:
                    self._launch_serve("ace")
        elif self.phase == "rally":
            self._fly(dt)
        elif self.phase == "point":
            self.point_t -= dt
            if self.point_t <= 0:
                if self.winner:
                    self.phase = "match"
                else:
                    self._begin_serve()
        return self.events


def _arrival(rally):
    ball = rally.ball
    if abs(ball.vy) < 1:
        return ball.x
    t = (rally.you_strike - ball.y) / ball.vy
    if t < 0:
        return rally.cx
    return ball.x + ball.vx * t


def self_check():
    assert match_winner(10, 10) is None
    assert match_winner(11, 9) == "you"
    assert match_winner(11, 10) is None
    assert match_winner(12, 10) == "you"
    assert match_winner(9, 11) == "ace"
    assert match_winner(13, 11) == "you"

    from .settings import TABLE_H, TABLE_W, TABLE_X, TABLE_Y
    bounds = (TABLE_X, TABLE_Y, TABLE_X + TABLE_W, TABLE_Y + TABLE_H)
    rally = Rally("match", bounds, seed=4)
    net_z = None
    bounced = None
    for _ in range(240):
        prev = rally.ball.y
        rally.step(1 / 60, rally.cx, serve=True)
        if rally.phase == "rally" and net_z is None and prev > rally.net_y >= rally.ball.y:
            net_z = rally.last_net_z
        for event in rally.events:
            if event[0] == "bounce" and bounced is None:
                bounced = event
        if bounced and net_z:
            break
    assert net_z is not None and net_z > NET_H, net_z
    assert bounced is not None, "serve never bounced"
    _, bx, by = bounced
    assert rally._fair(bx, by, "you"), (bx, by, rally.net_y)

    def play(level, seconds, policy, seed):
        game = Rally(level, bounds, seed=seed)
        for _ in range(int(seconds * 60)):
            game.step(1 / 60, policy(game), serve=True)
        return game

    def perfect(game):
        if game.phase == "rally" and game.ball.vy > 0:
            return _arrival(game)
        return game.cx

    steady = play("match", 8, perfect, 2)
    assert steady.live_best() >= 4, (steady.you, steady.ace, steady.live_best())

    def attack(game):
        sign = 1 if (game.you + game.ace) % 2 == 0 else -1
        if game.phase == "serve" and game.server == "you":
            return game.cx + sign * game.half * 0.15
        if game.phase == "rally" and game.ball.vy > 0:
            return _arrival(game) - sign * (PADDLE_W * 0.46)
        return game.cx

    corner = play("warmup", 18, attack, 5)
    assert corner.you >= 1, (corner.you, corner.ace, corner.live_best())
    play("agent", 6, perfect, 9)
    print(
        "rally check ok",
        "steady", steady.you, steady.ace, steady.live_best(),
        "warmup", corner.you, corner.ace, corner.live_best(),
    )


if __name__ == "__main__":
    self_check()
