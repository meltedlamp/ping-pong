"""Match loop, table, and menus."""

import math
import random

import pygame

from .audio import Audio
from .rally import Rally
from .scores import load, save
from .settings import (
    ACE, APRON, APRON_EDGE, BALL, BG, FAULT, FELT, FELT_DARK, FPS, GOLD, HEIGHT,
    LEVEL_ORDER, LEVELS, LINE, LINE_INSET, MUTED, PLAYER_SPEED, TABLE_H, TABLE_W,
    TABLE_X, TABLE_Y, TEXT, TITLE, WHITE, WIDTH, YOU,
)


def _bounds():
    return (TABLE_X, TABLE_Y, TABLE_X + TABLE_W, TABLE_Y + TABLE_H)


class Spark:
    def __init__(self, x, y, color):
        angle = random.random() * math.tau
        speed = random.uniform(30, 160)
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.color = color
        self.life = random.uniform(0.15, 0.32)
        self.age = 0.0

    def step(self, dt):
        self.age += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        return self.age < self.life


class Game:
    def __init__(self):
        try:
            pygame.mixer.pre_init(44100, -16, 1, 512)
        except pygame.error:
            pass
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("segoeui", 28)
        self.small = pygame.font.SysFont("segoeui", 18)
        self.tiny = pygame.font.SysFont("segoeui", 15)
        self.big = pygame.font.SysFont("segoeui", 68, bold=True)
        self.score_font = pygame.font.SysFont("segoeui", 54, bold=True)
        self.button_font = pygame.font.SysFont("segoeui", 24, bold=True)
        self.audio = Audio()
        self.stats = load()
        self.audio.muted = self.stats["muted"]
        self.level = self.stats["level"]
        self.table = pygame.Rect(TABLE_X, TABLE_Y, TABLE_W, TABLE_H)
        self.glow = pygame.Surface((TABLE_W, TABLE_H), pygame.SRCALPHA)
        pygame.draw.ellipse(self.glow, (255, 255, 255, 18), (80, 24, TABLE_W - 160, TABLE_H - 70))
        self.shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.shade.fill((5, 8, 12, 176))
        rng = random.Random(3)
        self.scuffs = [
            (
                rng.randint(36, TABLE_W - 36),
                rng.randint(36, TABLE_H - 36),
                rng.randint(18, 46),
                rng.randint(8, 18),
            )
            for _ in range(22)
        ]
        self.play_rect = pygame.Rect(0, 0, 240, 62)
        self.play_rect.center = (WIDTH // 2, 470)
        gap = 16
        card_w, card_h = 220, 108
        row = card_w * 3 + gap * 2
        left = (WIDTH - row) // 2
        self.cards = {
            level: pygame.Rect(left + i * (card_w + gap), 248, card_w, card_h)
            for i, level in enumerate(LEVEL_ORDER)
        }
        self.again_rect = pygame.Rect(0, 0, 200, 54)
        self.again_rect.center = (WIDTH // 2, 575)
        self.menu_rect = pygame.Rect(0, 0, 200, 54)
        self.menu_rect.center = (WIDTH // 2, 644)
        self.resume_rect = pygame.Rect(0, 0, 210, 54)
        self.resume_rect.center = (WIDTH // 2, 500)
        self.pause_menu_rect = pygame.Rect(0, 0, 210, 54)
        self.pause_menu_rect.center = (WIDTH // 2, 568)
        self.mouse = (WIDTH // 2, HEIGHT // 2)
        self.using_mouse = True
        self.clicked = False
        self.serve_down = False
        self.ui_used = False
        self.running = True
        self.state = "start"
        self.rally = None
        self.trail = []
        self.sparks = []
        self.shake = 0.0
        self.ox = 0.0
        self.oy = 0.0
        self.seen_point = False
        pygame.mouse.set_visible(True)

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000
            self.frame(dt)
        pygame.mouse.set_visible(True)
        pygame.quit()

    def frame(self, dt):
        self._events()
        self._update(dt)
        self._draw()
        pygame.display.flip()

    def _events(self):
        self.clicked = False
        self.serve_down = False
        self.ui_used = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEMOTION:
                self.mouse = event.pos
                self.using_mouse = True
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.mouse = event.pos
                self.clicked = True
                self.using_mouse = True
            elif event.type == pygame.KEYDOWN:
                self._key(event.key)
        if self.clicked:
            self.ui_used = self._click()
        if self.clicked and self.state == "play" and not self.ui_used:
            self.serve_down = True

    def _key(self, key):
        if key == pygame.K_m:
            self.audio.muted = not self.audio.muted
            self.stats["muted"] = self.audio.muted
            self._store()
            return
        if key == pygame.K_ESCAPE:
            if self.state == "start":
                self.running = False
            elif self.state == "play":
                self.state = "pause"
                pygame.mouse.set_visible(True)
            elif self.state == "pause":
                self._resume()
            elif self.state == "over":
                self._to_title()
            return
        if key in (pygame.K_1, pygame.K_2, pygame.K_3) and self.state == "start":
            self.level = LEVEL_ORDER[key - pygame.K_1]
            self.stats["level"] = self.level
            self._store()
            return
        if key in (pygame.K_SPACE, pygame.K_RETURN):
            if self.state in ("start", "over"):
                self.start_match()
            elif self.state == "pause":
                self._resume()
            elif self.state == "play":
                self.serve_down = True

    def _click(self):
        if self.state == "start":
            for level, rect in self.cards.items():
                if rect.collidepoint(self.mouse):
                    self.level = level
                    self.stats["level"] = level
                    self._store()
                    return True
            if self.play_rect.collidepoint(self.mouse):
                self.start_match()
                return True
        elif self.state == "pause":
            if self.resume_rect.collidepoint(self.mouse):
                self._resume()
                return True
            if self.pause_menu_rect.collidepoint(self.mouse):
                self._to_title()
                return True
        elif self.state == "over":
            if self.again_rect.collidepoint(self.mouse):
                self.start_match()
                return True
            if self.menu_rect.collidepoint(self.mouse):
                self._to_title()
                return True
        return False

    def _resume(self):
        self.state = "play"
        pygame.mouse.set_visible(False)

    def _to_title(self):
        self.state = "start"
        pygame.mouse.set_visible(True)

    def start_match(self):
        self.rally = Rally(self.level, _bounds())
        self.trail = []
        self.sparks = []
        self.shake = 0.0
        self.seen_point = False
        self.state = "play"
        self.stats["level"] = self.level
        self._store()
        pygame.mouse.set_visible(False)

    def _player_x(self, dt):
        keys = pygame.key.get_pressed()
        cx = self.rally.player.cx
        direction = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            direction -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            direction += 1
        if direction:
            self.using_mouse = False
            return cx + direction * PLAYER_SPEED * dt
        if self.using_mouse:
            return self.mouse[0]
        return cx

    def _update(self, dt):
        if dt <= 0:
            dt = 1 / FPS
        dt = min(dt, 0.05)
        self.shake = max(0.0, self.shake - dt * 1.5)
        if self.state != "play" or self.rally is None:
            return
        events = self.rally.step(dt, self._player_x(dt), self.serve_down)
        self._react(events)
        ball = self.rally.ball
        if self.rally.phase == "rally":
            self.trail.append((ball.x, ball.y - ball.z))
            del self.trail[:-16]
        else:
            self.trail.clear()
        self.sparks = [spark for spark in self.sparks if spark.step(dt)]
        if self.rally.live_best() > self.stats["rally"]:
            self.stats["rally"] = self.rally.live_best()
            self._store()
        if self.rally.phase == "match":
            self.state = "over"
            pygame.mouse.set_visible(True)

    def _react(self, events):
        for event in events:
            kind = event[0]
            if kind == "serve":
                self.audio.play("serve")
                self._burst(event[2], event[3], WHITE, 8)
            elif kind == "hit":
                who = event[1]
                self.audio.play("hit_you" if who == "you" else "hit_ace")
                self._burst(event[2], event[3], YOU if who == "you" else ACE, 12)
                self.shake = min(0.3, self.shake + 0.08)
            elif kind == "bounce":
                self.audio.play("bounce")
                self._burst(event[1], event[2], WHITE, 7)
            elif kind == "point":
                winner, reason, x, y = event[1], event[2], event[3], event[4]
                self.seen_point = True
                if reason == "net":
                    self.audio.play("net")
                elif reason == "out":
                    self.audio.play("out")
                else:
                    self.audio.play("score_you" if winner == "you" else "score_ace")
                self._burst(x, y, YOU if winner == "you" else ACE, 16)
                self.shake = min(0.34, self.shake + 0.18)
            elif kind == "match" and event[1] == "you":
                self.stats["wins"] += 1
                self._store()

    def _burst(self, x, y, color, count):
        for _ in range(count):
            self.sparks.append(Spark(x, y, color))

    def _store(self):
        save(self.stats)

    def _draw(self):
        self.screen.fill(BG)
        mag = self.shake * 16
        if mag > 0.4:
            self.ox = random.uniform(-mag, mag)
            self.oy = random.uniform(-mag, mag)
        else:
            self.ox = self.oy = 0.0
        if self.state == "start":
            self._draw_start()
            return
        self._draw_world()
        self._draw_hud()
        if self.state == "pause":
            self._draw_pause()
        elif self.state == "over":
            self._draw_over()
        elif self.rally is not None and self.rally.phase == "point":
            self._draw_banner()

    def _draw_world(self):
        ox, oy = self.ox, self.oy
        apron = self.table.inflate(28, 28)
        apron.move_ip(ox, oy)
        pygame.draw.rect(self.screen, APRON_EDGE, apron, border_radius=18)
        lip = self.table.inflate(12, 12)
        lip.move_ip(ox, oy)
        pygame.draw.rect(self.screen, APRON, lip, border_radius=12)
        felt = self.table.move(ox, oy)
        pygame.draw.rect(self.screen, FELT_DARK, felt, border_radius=8)
        inner = self.table.inflate(-10, -10).move(ox, oy)
        pygame.draw.rect(self.screen, FELT, inner, border_radius=6)
        self.screen.blit(self.glow, felt.topleft)
        for sx, sy, rw, rh in self.scuffs:
            rect = pygame.Rect(0, 0, rw, rh)
            rect.center = (self.table.left + sx + ox, self.table.top + sy + oy)
            pygame.draw.ellipse(self.screen, (22, 124, 92), rect)
        lines = pygame.Rect(
            self.table.left + LINE_INSET + ox,
            self.table.top + LINE_INSET + oy,
            self.table.w - LINE_INSET * 2,
            self.table.h - LINE_INSET * 2,
        )
        pygame.draw.rect(self.screen, LINE, lines, 3, border_radius=2)
        rally = self.rally
        self._draw_ghost()
        if rally.phase in ("serve", "rally"):
            self._draw_shadow()
        self._draw_net()
        self._draw_paddle(rally.player, YOU, eye=False)
        self._draw_paddle(rally.ace_pad, ACE, eye=True)
        if rally.phase in ("serve", "rally"):
            self._draw_trail()
            self._draw_ball()
        for spark in self.sparks:
            pygame.draw.circle(self.screen, spark.color, (int(spark.x + self.ox), int(spark.y + self.oy)), 2)

    def _draw_net(self):
        y = int(self.rally.net_y + self.oy)
        left = int(self.table.left + self.ox)
        right = int(self.table.right + self.ox)
        pygame.draw.rect(self.screen, WHITE, (left - 8, y - 16, 8, 32), border_radius=2)
        pygame.draw.rect(self.screen, WHITE, (right, y - 16, 8, 32), border_radius=2)
        for x in range(left, right, 7):
            pygame.draw.line(self.screen, (226, 232, 226), (x, y - 12), (x, y + 12))
        pygame.draw.line(self.screen, WHITE, (left, y - 12), (right, y - 12), 3)

    def _draw_paddle(self, pad, color, eye):
        rect = pygame.Rect(0, 0, pad.w, pad.h)
        rect.center = (int(pad.cx + self.ox), int(pad.cy + self.oy))
        pygame.draw.rect(self.screen, color, rect, border_radius=7)
        edge = tuple(min(255, c + 40) for c in color)
        pygame.draw.rect(self.screen, edge, rect, 2, border_radius=7)
        if not eye:
            return
        slot = pygame.Rect(0, 0, 26, 6)
        slot.center = rect.center
        pygame.draw.rect(self.screen, (48, 28, 16), slot, border_radius=3)
        ball = self.rally.ball
        look = max(-1.0, min(1.0, (ball.x - pad.cx) / 90))
        pupil = pygame.Rect(0, 0, 7, 4)
        pupil.center = (slot.centerx + int(look * 7), slot.centery)
        pygame.draw.rect(self.screen, (255, 244, 220), pupil, border_radius=2)

    def _draw_shadow(self):
        ball = self.rally.ball
        rect = pygame.Rect(0, 0, 22, 10)
        rect.center = (int(ball.x + self.ox), int(ball.y + self.oy))
        pygame.draw.ellipse(self.screen, (4, 36, 28), rect)

    def _draw_trail(self):
        total = len(self.trail)
        for i, (x, y) in enumerate(self.trail):
            radius = 2 if i < total - 4 else 3
            color = (180, 210, 196) if i > total - 5 else (70, 130, 112)
            pygame.draw.circle(self.screen, color, (int(x + self.ox), int(y + self.oy)), radius)

    def _draw_ball(self):
        ball = self.rally.ball
        x = int(ball.x + self.ox)
        y = int(ball.y - ball.z + self.oy)
        if ball.z < 7:
            rect = pygame.Rect(0, 0, ball.r * 2 + 4, ball.r * 2 - 2)
            rect.center = (x, y)
            pygame.draw.ellipse(self.screen, BALL, rect)
        else:
            pygame.draw.circle(self.screen, BALL, (x, y), ball.r)
        dx = math.cos(ball.spin) * 5
        dy = math.sin(ball.spin) * 3
        pygame.draw.line(self.screen, (190, 196, 188), (x - dx, y - dy), (x + dx, y + dy), 2)

    def _draw_ghost(self):
        ghost = self.rally.serve_ghost()
        if ghost is None:
            return
        bx, by, fair = ghost
        color = YOU if fair else FAULT
        center = (int(bx + self.ox), int(by + self.oy))
        pygame.draw.circle(self.screen, color, center, 15, 2)
        ball = self.rally.ball
        for i in range(1, 5):
            t = i / 5
            x = ball.x + (bx - ball.x) * t
            y = ball.y + (by - ball.y) * t
            pygame.draw.circle(self.screen, color, (int(x + self.ox), int(y + self.oy)), 2)

    def _draw_hud(self):
        rally = self.rally
        ace_color = GOLD if rally.ace > rally.you else TEXT
        you_color = GOLD if rally.you > rally.ace else TEXT
        self._blit(self.font, "ACE", ACE, (36, 34))
        level = self.small.render(rally.label, True, MUTED)
        self.screen.blit(level, (100, 42))
        caption = self.small.render(rally.caption(), True, GOLD)
        self.screen.blit(caption, (36, 74))
        ace_score = self.score_font.render(str(rally.ace), True, ace_color)
        self.screen.blit(ace_score, ace_score.get_rect(right=WIDTH - 36, top=24))
        if rally.phase == "serve" and rally.server == "ace":
            pygame.draw.circle(self.screen, ACE, (24, 48), 5)

        self._blit(self.font, "YOU", YOU, (36, HEIGHT - 118))
        you_score = self.score_font.render(str(rally.you), True, you_color)
        self.screen.blit(you_score, you_score.get_rect(right=WIDTH - 36, top=HEIGHT - 132))
        if rally.phase == "serve" and rally.server == "you":
            pygame.draw.circle(self.screen, YOU, (24, HEIGHT - 104), 5)

        pace = pygame.Rect(WIDTH // 2 - 90, HEIGHT - 78, 180, 8)
        pygame.draw.rect(self.screen, (24, 36, 40), pace, border_radius=4)
        fill = pace.copy()
        fill.w = max(0, int(pace.w * rally.pace))
        if fill.w:
            pygame.draw.rect(self.screen, GOLD, fill, border_radius=4)
        pace_label = self.tiny.render("PACE", True, MUTED)
        self.screen.blit(pace_label, pace_label.get_rect(midbottom=(pace.centerx, pace.top - 4)))
        rally_label = self.tiny.render(f"rally {rally.rally_hits}", True, MUTED)
        self.screen.blit(rally_label, (36, HEIGHT - 78))

        if not self.seen_point:
            hint = "Mouse or A D to move.  Space serves.  Meet the ball — the edge of the paddle aims it wide."
        else:
            hint = "Space serves    M mute    Esc pause"
        hint_img = self.tiny.render(hint, True, MUTED)
        self.screen.blit(hint_img, hint_img.get_rect(midbottom=(WIDTH // 2, HEIGHT - 18)))
        if self.audio.muted:
            tag = self.tiny.render("muted", True, MUTED)
            self.screen.blit(tag, (WIDTH - 36 - tag.get_width(), HEIGHT - 78))

    def _draw_banner(self):
        rally = self.rally
        label = "YOU" if rally.last_winner == "you" else "ACE"
        color = YOU if rally.last_winner == "you" else ACE
        plate = pygame.Surface((280, 96), pygame.SRCALPHA)
        plate.fill((6, 12, 16, 150))
        rect = plate.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20))
        self.screen.blit(plate, rect)
        text = self.big.render(label, True, color)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def _draw_start(self):
        title = self.big.render("PING PONG", True, TEXT)
        self.screen.blit(title, title.get_rect(midtop=(WIDTH // 2, 64)))
        sub = self.font.render("You on the near side. ACE plays the far side.", True, MUTED)
        self.screen.blit(sub, sub.get_rect(midtop=(WIDTH // 2, 148)))
        rule = self.small.render("First to 11, win by 2. Land it on the far half.", True, TEXT)
        self.screen.blit(rule, rule.get_rect(midtop=(WIDTH // 2, 192)))
        for level, rect in self.cards.items():
            self._card(rect, level, level == self.level)
        blurb = LEVELS[self.level]["blurb"]
        self._centered(self.small, blurb, TEXT, 372, WIDTH - 120)
        self._button(self.play_rect, "PLAY", primary=True)
        wins = self.small.render(f"Wins  {self.stats['wins']}", True, GOLD)
        best = self.small.render(f"Best rally  {self.stats['rally']}", True, MUTED)
        self.screen.blit(wins, wins.get_rect(midtop=(WIDTH // 2 - 90, 560)))
        self.screen.blit(best, best.get_rect(midtop=(WIDTH // 2 + 80, 560)))
        lines = (
            "Move with the mouse, or A and D.",
            "Stand to one side before you serve. Hit the ball with the edge to angle it.",
            "M mutes.  Esc pauses.  1  2  3 pick the agent.",
        )
        y = 630
        for line in lines:
            img = self.small.render(line, True, MUTED)
            self.screen.blit(img, img.get_rect(midtop=(WIDTH // 2, y)))
            y += 28
        self._draw_diagram()

    def _draw_diagram(self):
        rect = pygame.Rect(0, 0, 280, 140)
        rect.midbottom = (WIDTH // 2, HEIGHT - 36)
        pygame.draw.rect(self.screen, APRON_EDGE, rect.inflate(10, 10), border_radius=10)
        pygame.draw.rect(self.screen, FELT, rect, border_radius=6)
        pygame.draw.rect(self.screen, LINE, rect.inflate(-12, -12), 2)
        net = rect.centery
        pygame.draw.line(self.screen, WHITE, (rect.left + 8, net), (rect.right - 8, net), 3)
        ace = pygame.Rect(0, 0, 54, 8)
        ace.center = (rect.centerx, rect.top + 22)
        you = pygame.Rect(0, 0, 54, 8)
        you.center = (rect.centerx, rect.bottom - 22)
        pygame.draw.rect(self.screen, ACE, ace, border_radius=3)
        pygame.draw.rect(self.screen, YOU, you, border_radius=3)
        far = self.tiny.render("ACE", True, ACE)
        near = self.tiny.render("YOU", True, YOU)
        self.screen.blit(far, far.get_rect(midbottom=(rect.centerx, ace.top - 2)))
        self.screen.blit(near, near.get_rect(midtop=(rect.centerx, you.bottom + 2)))

    def _draw_pause(self):
        self.screen.blit(self.shade, (0, 0))
        title = self.big.render("PAUSED", True, TEXT)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 400)))
        self._button(self.resume_rect, "RESUME", primary=True)
        self._button(self.pause_menu_rect, "TITLE")

    def _draw_over(self):
        self.screen.blit(self.shade, (0, 0))
        rally = self.rally
        you_won = rally.winner == "you"
        label = "YOU WIN" if you_won else "ACE WINS"
        title = self.big.render(label, True, YOU if you_won else ACE)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 360)))
        score = self.font.render(f"{rally.you}   –   {rally.ace}", True, TEXT)
        self.screen.blit(score, score.get_rect(center=(WIDTH // 2, 440)))
        note = rally.quip or ""
        quip = self.small.render(note, True, GOLD)
        self.screen.blit(quip, quip.get_rect(center=(WIDTH // 2, 482)))
        best = self.small.render(f"Best rally  {self.stats['rally']}", True, MUTED)
        self.screen.blit(best, best.get_rect(center=(WIDTH // 2, 518)))
        self._button(self.again_rect, "AGAIN", primary=True)
        self._button(self.menu_rect, "TITLE")

    def _card(self, rect, level, selected):
        spec = LEVELS[level]
        hover = rect.collidepoint(self.mouse)
        accent = {"warmup": YOU, "match": GOLD, "agent": ACE}[level]
        pygame.draw.rect(self.screen, (12, 22, 28), rect, border_radius=14)
        border = accent if selected or hover else (40, 58, 64)
        pygame.draw.rect(self.screen, border, rect, 2, border_radius=14)
        name = self.button_font.render(spec["label"], True, accent if selected else TEXT)
        self.screen.blit(name, name.get_rect(center=(rect.centerx, rect.centery - 10)))
        if selected:
            mark = self.tiny.render("selected", True, MUTED)
            self.screen.blit(mark, mark.get_rect(center=(rect.centerx, rect.centery + 22)))

    def _button(self, rect, label, primary=False):
        hover = rect.collidepoint(self.mouse)
        fill = (16, 58, 68) if primary else (14, 26, 32)
        if hover:
            fill = tuple(min(255, channel + 16) for channel in fill)
        pygame.draw.rect(self.screen, fill, rect, border_radius=12)
        border = YOU if primary or hover else (46, 68, 74)
        pygame.draw.rect(self.screen, border, rect, 2, border_radius=12)
        text = self.button_font.render(label, True, TEXT)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def _blit(self, font, text, color, pos):
        img = font.render(text, True, color)
        self.screen.blit(img, pos)

    def _centered(self, font, text, color, top, width):
        words = text.split()
        lines = []
        current = ""
        for word in words:
            trial = word if not current else f"{current} {word}"
            if font.size(trial)[0] <= width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        y = top
        for line in lines:
            img = font.render(line, True, color)
            self.screen.blit(img, img.get_rect(midtop=(WIDTH // 2, y)))
            y += font.get_linesize()


def main():
    Game().run()
