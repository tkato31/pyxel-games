import pyxel

# --- Layout constants (content-first sizing) ---
BRICK_COLS   = 10
BRICK_ROWS   = 5
BRICK_W      = 14
BRICK_H      = 6
BRICK_GAP    = 1
MARGIN_X     = 4
MARGIN_TOP   = 20   # space above bricks (score + title area)
MARGIN_BOT   = 4

BOARD_W = BRICK_COLS * (BRICK_W + BRICK_GAP) - BRICK_GAP   # 149
BOARD_H = (BRICK_ROWS * (BRICK_H + BRICK_GAP) - BRICK_GAP  # bricks zone
           + 50 + MARGIN_TOP + MARGIN_BOT)                   # play area below

SCR_W = MARGIN_X + BOARD_W + MARGIN_X   # 157  → round to 160
SCR_H = 160
SCR_W = 160

PLAY_X = (SCR_W - BOARD_W) // 2   # left edge of brick grid
BRICKS_Y = MARGIN_TOP

# Paddle
PAD_W    = 28
PAD_H    = 4
PAD_Y    = SCR_H - 16
PAD_SPD  = 2.0

# Ball
BALL_R   = 2
BALL_SPD = 2.0

# Brick row colors
ROW_COLORS = [8, 9, 10, 11, 3]   # red, orange, yellow, lime, green


class Breakout:
    def __init__(self):
        pyxel.init(SCR_W, SCR_H, title="BREAKOUT", fps=60)
        self._init_sounds()
        self.reset_game()
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------------
    def _init_sounds(self):
        # Paddle hit
        pyxel.sounds[0].set("c3e3", "s", "74", "nn", 6)
        # Brick hit
        pyxel.sounds[1].set("g3c4", "s", "64", "nn", 5)
        # Wall hit
        pyxel.sounds[2].set("c3", "s", "5", "n", 5)
        # Miss (life lost)
        pyxel.sounds[3].set("g2e2c2", "p", "654", "nnn", 8)
        # Clear
        pyxel.sounds[4].set("c3e3g3c4e4g4c4", "s", "4444444", "nnnnnnn", 6)
        # BGM (3ch)
        pyxel.sounds[10].mml("T120 @1 V60 L8 O3 [CEGCEGCE >C<BAGFED]2")
        pyxel.sounds[11].mml("T120 @0 V40 L4 O2 [CC GG AA FF]2")
        pyxel.sounds[12].mml("T120 @1 V30 L16 O3 [CEGCEGCEGCEGCEGC]2")
        pyxel.musics[0].set([10], [11], [12])

    # ------------------------------------------------------------------
    def reset_game(self):
        self.score  = 0
        self.lives  = 3
        self.scene  = "title"   # title / game / gameover / clear
        self.hi     = 0
        self._reset_round()

    def _reset_round(self):
        self.pad_x   = (SCR_W - PAD_W) // 2
        cx = SCR_W // 2
        cy = PAD_Y - 20
        self.ball_x  = float(cx)
        self.ball_y  = float(cy)
        self.ball_vx = BALL_SPD
        self.ball_vy = -BALL_SPD
        self.ball_on_pad = True  # wait for launch
        self.shake   = 0
        self.bricks  = self._make_bricks()

    def _make_bricks(self):
        bricks = []
        for row in range(BRICK_ROWS):
            for col in range(BRICK_COLS):
                x = PLAY_X + col * (BRICK_W + BRICK_GAP)
                y = BRICKS_Y + row * (BRICK_H + BRICK_GAP)
                bricks.append([x, y, True, ROW_COLORS[row]])
        return bricks

    # ------------------------------------------------------------------
    def update(self):
        if self.scene == "title":
            self._update_title()
        elif self.scene == "game":
            self._update_game()
        elif self.scene == "gameover":
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset_game()
        elif self.scene == "clear":
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self.reset_game()

    def _update_title(self):
        if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
            pyxel.playm(0, loop=True)
            self.scene = "game"

    def _update_game(self):
        # Paddle move
        if pyxel.btn(pyxel.KEY_LEFT)  or pyxel.btn(pyxel.KEY_A):
            self.pad_x = max(0, self.pad_x - PAD_SPD)
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            self.pad_x = min(SCR_W - PAD_W, self.pad_x + PAD_SPD)

        # Launch ball
        if self.ball_on_pad:
            self.ball_x = self.pad_x + PAD_W // 2
            self.ball_y = PAD_Y - BALL_R - 1
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_UP):
                self.ball_on_pad = False
            return

        # Ball movement
        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy

        # Wall bounce (left/right)
        if self.ball_x - BALL_R <= 0:
            self.ball_x = BALL_R
            self.ball_vx = abs(self.ball_vx)
            pyxel.play(3, 2)
        if self.ball_x + BALL_R >= SCR_W:
            self.ball_x = SCR_W - BALL_R
            self.ball_vx = -abs(self.ball_vx)
            pyxel.play(3, 2)

        # Ceiling bounce
        if self.ball_y - BALL_R <= 0:
            self.ball_y = BALL_R
            self.ball_vy = abs(self.ball_vy)
            pyxel.play(3, 2)

        # Paddle collision
        if (self.ball_vy > 0
                and PAD_Y <= self.ball_y + BALL_R <= PAD_Y + PAD_H
                and self.pad_x - BALL_R <= self.ball_x <= self.pad_x + PAD_W + BALL_R):
            # Angle based on hit position
            rel = (self.ball_x - (self.pad_x + PAD_W / 2)) / (PAD_W / 2)  # -1..1
            speed = (self.ball_vx**2 + self.ball_vy**2) ** 0.5
            self.ball_vx = rel * speed
            if abs(self.ball_vx) < 0.3:
                self.ball_vx = 0.3 * (1 if rel >= 0 else -1)
            self.ball_vy = -abs(self.ball_vy)
            pyxel.play(3, 0)

        # Brick collision
        for b in self.bricks:
            if not b[2]:
                continue
            bx, by = b[0], b[1]
            if (bx - BALL_R <= self.ball_x <= bx + BRICK_W + BALL_R and
                    by - BALL_R <= self.ball_y <= by + BRICK_H + BALL_R):
                b[2] = False
                self.score += 10
                self.shake = 3
                pyxel.play(3, 1)
                # Reflect
                cx = bx + BRICK_W / 2
                cy = by + BRICK_H / 2
                dx = self.ball_x - cx
                dy = self.ball_y - cy
                if abs(dx) / BRICK_W > abs(dy) / BRICK_H:
                    self.ball_vx = -self.ball_vx
                else:
                    self.ball_vy = -self.ball_vy
                break  # one brick per frame

        # Ball out of bottom
        if self.ball_y - BALL_R > SCR_H:
            pyxel.stop()
            pyxel.play(3, 3)
            self.lives -= 1
            self.hi = max(self.hi, self.score)
            if self.lives <= 0:
                self.scene = "gameover"
            else:
                self._reset_round()
                pyxel.playm(0, loop=True)
            return

        # Clear check
        if all(not b[2] for b in self.bricks):
            pyxel.stop()
            pyxel.play(3, 4)
            self.hi = max(self.hi, self.score)
            self.scene = "clear"

        # Shake decay
        if self.shake > 0:
            self.shake -= 1

    # ------------------------------------------------------------------
    def draw(self):
        pyxel.cls(0)

        # Screen shake
        ox = oy = 0
        if self.shake > 0:
            ox = pyxel.rndi(-2, 2)
            oy = pyxel.rndi(-1, 1)
        pyxel.camera(ox, oy)

        if self.scene == "title":
            self._draw_title()
        elif self.scene == "game":
            self._draw_game()
        elif self.scene == "gameover":
            self._draw_game()
            self._draw_overlay("GAME OVER", f"SCORE:{self.score}", 8)
        elif self.scene == "clear":
            self._draw_game()
            self._draw_overlay("STAGE CLEAR!", f"SCORE:{self.score}", 10)

        pyxel.camera()

    # ------------------------------------------------------------------
    def _draw_title(self):
        # Stars
        for i in range(40):
            sx = (i * 37 + pyxel.frame_count // 3) % SCR_W
            sy = (i * 23) % SCR_H
            pyxel.pset(sx, sy, [1, 5, 6][i % 3])

        # Bouncing bricks decoration
        for i in range(5):
            x = 10 + i * 30
            y = int(40 + pyxel.sin(pyxel.frame_count * 4 + i * 72) * 4)
            pyxel.rect(x, y, BRICK_W, BRICK_H, ROW_COLORS[i % 5])

        # Title
        t = "BREAKOUT"
        pyxel.text((SCR_W - len(t) * 4) // 2 + 1, 61, t, 1)
        pyxel.text((SCR_W - len(t) * 4) // 2, 60, t, 7)

        # Controls
        pyxel.text(28, 90, "ARROWS / A-D : MOVE", 13)
        pyxel.text(36, 100, "SPACE / UP : LAUNCH", 13)

        # Blink
        if pyxel.frame_count % 50 < 35:
            t2 = "PRESS SPACE TO START"
            pyxel.text((SCR_W - len(t2) * 4) // 2, 120, t2, 10)

        if self.hi > 0:
            pyxel.text(52, 140, f"HI:{self.hi}", 9)

    def _draw_game(self):
        # Stars background
        for i in range(30):
            sx = (i * 43) % SCR_W
            sy = (i * 29 + pyxel.frame_count // 6) % SCR_H
            pyxel.pset(sx, sy, [1, 5][i % 2])

        # Bricks
        for b in self.bricks:
            if b[2]:
                x, y, _, col = b
                # Shadow
                pyxel.rect(x + 1, y + 1, BRICK_W, BRICK_H, 1)
                # Brick body
                pyxel.rect(x, y, BRICK_W, BRICK_H, col)
                # Highlight
                pyxel.line(x, y, x + BRICK_W - 1, y, 7)
                pyxel.line(x, y, x, y + BRICK_H - 1, 7)

        # Paddle
        px = int(self.pad_x)
        pyxel.rect(px + 1, PAD_Y + 1, PAD_W, PAD_H, 5)
        pyxel.rect(px, PAD_Y, PAD_W, PAD_H, 6)
        pyxel.line(px, PAD_Y, px + PAD_W - 1, PAD_Y, 12)

        # Ball
        bx, by = int(self.ball_x), int(self.ball_y)
        pyxel.circ(bx, by, BALL_R, 7)
        pyxel.pset(bx - 1, by - 1, 12)   # highlight

        # HUD
        pyxel.text(2, 2, f"SCORE:{self.score}", 7)
        hearts = "".join(["<3 " if i < self.lives else "   " for i in range(3)])
        pyxel.text(SCR_W - len(hearts) * 4 - 2, 2, hearts, 8)

        # Ball-on-pad hint
        if self.ball_on_pad:
            if pyxel.frame_count % 40 < 28:
                pyxel.text(38, SCR_H // 2 + 10, "PRESS SPACE/UP", 10)

    def _draw_overlay(self, title, sub, col):
        # Dim
        pyxel.dither(0.5)
        pyxel.rect(20, 55, SCR_W - 40, 55, 0)
        pyxel.dither(1.0)
        pyxel.rectb(20, 55, SCR_W - 40, 55, col)

        tx = (SCR_W - len(title) * 4) // 2
        pyxel.text(tx + 1, 67, title, 1)
        pyxel.text(tx, 66, title, col)

        sx = (SCR_W - len(sub) * 4) // 2
        pyxel.text(sx, 80, sub, 7)

        hi_txt = f"HI:{self.hi}"
        pyxel.text((SCR_W - len(hi_txt) * 4) // 2, 90, hi_txt, 9)

        if pyxel.frame_count % 50 < 35:
            t = "PRESS SPACE TO RETRY"
            pyxel.text((SCR_W - len(t) * 4) // 2, 102, t, 13)


Breakout()
