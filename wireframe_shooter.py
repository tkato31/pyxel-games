import pyxel

SCR_W, SCR_H = 160, 120
FOCAL        = 130     # perspective focal length
PLAYER_Z     = 30      # ship's Z position in world (camera is at Z=0)
STAR_DEPTH   = 180
NUM_STARS    = 180
ENEMY_SPAWN_Z = 160
PX_LIM, PY_LIM = 22, 16   # player movement range


class WireframeShooter:
    def __init__(self):
        pyxel.init(SCR_W, SCR_H, title="WIREFRAME SHOOTER", fps=60)
        self._init_sounds()
        self.hi = 0
        self.reset()
        pyxel.run(self.update, self.draw)

    # ── sounds ────────────────────────────────────────────────────────
    def _init_sounds(self):
        pyxel.sounds[0].set("c4e4",     "ss", "53", "nn", 5)   # shoot
        pyxel.sounds[1].set("g3c3",     "ss", "74", "nn", 5)   # enemy down
        pyxel.sounds[2].set("f3b2f2",   "ppp","765","nnn", 7)   # player hit
        pyxel.sounds[3].set("g2e2c2g1", "pppp","7654","nnnn",9) # game over

    # ── init ──────────────────────────────────────────────────────────
    def reset(self):
        self.score       = 0
        self.scene       = "title"
        self.px          = 0.0   # player world X
        self.py          = 0.0   # player world Y
        self.cam_x       = 0.0
        self.cam_y       = -2.0  # camera is slightly above ship
        self.bullets     = []    # [x, y, z]
        self.enemies     = []    # dict
        self.explosions  = []    # dict
        self.spawn_timer = 0
        self.hit_flash   = 0
        self.stars       = [
            [pyxel.rndf(-55, 55), pyxel.rndf(-45, 45), pyxel.rndf(1.0, STAR_DEPTH)]
            for _ in range(NUM_STARS)
        ]

    # ── 3-D projection ────────────────────────────────────────────────
    def proj(self, wx, wy, wz):
        """World coords → screen pixel. Returns (None,None) if behind cam."""
        rz = wz
        if rz < 0.5:
            return None, None
        rx = wx - self.cam_x
        ry = wy - self.cam_y
        return (int(FOCAL * rx / rz) + SCR_W // 2,
                int(FOCAL * ry / rz) + SCR_H // 2)

    def line3d(self, x1, y1, z1, x2, y2, z2, col):
        a = self.proj(x1, y1, z1)
        b = self.proj(x2, y2, z2)
        if a[0] is not None and b[0] is not None:
            pyxel.line(a[0], a[1], b[0], b[1], col)

    # ── update ────────────────────────────────────────────────────────
    def update(self):
        if self.scene == "title":
            self._update_stars(0.5)
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.scene = "game"
        elif self.scene == "game":
            self._update_game()
        elif self.scene == "gameover":
            self._update_stars(0.4)
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reset()
                self.scene = "game"

    def _update_stars(self, speed):
        for s in self.stars:
            s[2] -= speed
            if s[2] <= 0:
                s[0] = pyxel.rndf(-55, 55)
                s[1] = pyxel.rndf(-45, 45)
                s[2] = STAR_DEPTH

    def _update_game(self):
        # ─ player movement
        spd = 0.28
        if pyxel.btn(pyxel.KEY_LEFT):
            self.px = max(-PX_LIM, self.px - spd)
        if pyxel.btn(pyxel.KEY_RIGHT):
            self.px = min( PX_LIM, self.px + spd)
        if pyxel.btn(pyxel.KEY_UP):
            self.py = max(-PY_LIM, self.py - spd)
        if pyxel.btn(pyxel.KEY_DOWN):
            self.py = min( PY_LIM, self.py + spd)

        # camera lags behind player (offset: slightly above and behind)
        self.cam_x += (self.px * 0.55 - self.cam_x) * 0.07
        self.cam_y += (self.py * 0.55 - 2.0 - self.cam_y) * 0.07

        # ─ shoot
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.bullets.append([self.px, self.py, float(PLAYER_Z + 2)])
            pyxel.play(1, 0)

        # ─ bullets
        for b in list(self.bullets):
            b[2] += 5.0
            if b[2] > STAR_DEPTH + 30:
                self.bullets.remove(b)

        # ─ stars
        self._update_stars(0.7)

        # ─ enemy spawn
        self.spawn_timer += 1
        interval = max(35, 110 - self.score // 3)
        if self.spawn_timer >= interval:
            self.spawn_timer = 0
            etype = pyxel.rndi(0, 1)
            self.enemies.append({
                'x':   pyxel.rndf(-20, 20),
                'y':   pyxel.rndf(-14, 14),
                'z':   float(ENEMY_SPAWN_Z),
                'type': etype,
                'rot': float(pyxel.rndi(0, 359)),
            })

        # ─ enemy update
        e_spd = 0.9 + self.score * 0.015
        for e in list(self.enemies):
            e['z'] -= e_spd
            e['rot'] = (e['rot'] + 2.5) % 360

            if e['z'] <= PLAYER_Z - 2:
                self.enemies.remove(e)
                self.hit_flash = 12
                pyxel.play(2, 2)
                pyxel.play(3, 3)
                self.hi = max(self.hi, self.score)
                self.scene = "gameover"
                return

        # ─ bullet × enemy collision
        for e in list(self.enemies):
            for b in list(self.bullets):
                if (abs(e['x'] - b[0]) < 5 and
                        abs(e['y'] - b[1]) < 5 and
                        abs(e['z'] - b[2]) < 10):
                    if e in self.enemies:
                        self.enemies.remove(e)
                    if b in self.bullets:
                        self.bullets.remove(b)
                    self.score += 10
                    self.explosions.append({
                        'x': e['x'], 'y': e['y'], 'z': e['z'],
                        'life': 18
                    })
                    pyxel.play(1, 1)
                    break

        # ─ explosions
        for ex in list(self.explosions):
            ex['life'] -= 1
            ex['z'] -= e_spd
            if ex['life'] <= 0:
                self.explosions.remove(ex)

        if self.hit_flash > 0:
            self.hit_flash -= 1

    # ── drawing helpers ───────────────────────────────────────────────
    def _draw_stars(self):
        for s in self.stars:
            sx, sy = self.proj(s[0], s[1], s[2])
            if sx is not None and 0 <= sx < SCR_W and 0 <= sy < SCR_H:
                ratio = s[2] / STAR_DEPTH
                col = 6 if ratio < 0.3 else (5 if ratio < 0.65 else 1)
                pyxel.pset(sx, sy, col)

    def _draw_player(self):
        x, y, z = self.px, self.py, PLAYER_Z
        c = pyxel.cos
        s = pyxel.sin
        col = 6  # light_blue frame

        # Delta-wing points (world space, seen from camera behind)
        pts = [
            (x,      y - 2.5, z + 5.0),  # 0 nose
            (x - 8,  y + 2.0, z - 1.0),  # 1 left wing tip
            (x - 2,  y + 1.0, z + 0.5),  # 2 left root
            (x,      y + 3.5, z - 3.0),  # 3 tail
            (x + 2,  y + 1.0, z + 0.5),  # 4 right root
            (x + 8,  y + 2.0, z - 1.0),  # 5 right wing tip
        ]
        edges = [
            (0, 1), (0, 5),
            (1, 2), (5, 4),
            (2, 4),
            (2, 3), (4, 3),
            (0, 2), (0, 4),
        ]
        for a, b in edges:
            self.line3d(*pts[a], *pts[b], col)

        # Cockpit highlight
        sx, sy = self.proj(x, y - 1.5, z + 3)
        if sx is not None:
            pyxel.pset(sx, sy, 12)

        # Engine nozzle flicker
        sx, sy = self.proj(x, y + 2, z - 3)
        if sx is not None:
            pyxel.pset(sx, sy, 10)
            if pyxel.frame_count % 4 < 2:
                pyxel.pset(sx, sy + 1, 9)

    def _draw_enemy(self, e):
        x, y, z, r = e['x'], e['y'], e['z'], e['rot']
        if z < 1:
            return
        cr, sr = pyxel.cos(r), pyxel.sin(r)

        # Color: red when close
        col = 9 if z > 90 else (8 if z > 45 else 8)

        if e['type'] == 0:
            # Octahedron (diamond) rotating around Y
            sz = 4.5
            def rv(lx, ly, lz):   # rotate Y, translate
                return (lx*cr - lz*sr + x, ly + y, lx*sr + lz*cr + z)
            pts = [
                rv( sz,   0,  0),  # 0 right
                rv(-sz,   0,  0),  # 1 left
                rv(  0,  sz,  0),  # 2 bottom
                rv(  0, -sz,  0),  # 3 top
                rv(  0,   0,  sz), # 4 front
                rv(  0,   0, -sz), # 5 back
            ]
            edges = [
                (0,2),(0,3),(0,4),(0,5),
                (1,2),(1,3),(1,4),(1,5),
                (2,4),(2,5),(3,4),(3,5),
            ]
        else:
            # Cube rotating around Y
            hw = 3.5
            corners = [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),
                       ( 1,-1,-1),( 1,-1,1),( 1,1,-1),( 1,1,1)]
            pts = []
            for (lx, ly, lz) in corners:
                pts.append((
                    (lx*cr - lz*sr)*hw + x,
                    ly*hw + y,
                    (lx*sr + lz*cr)*hw + z,
                ))
            edges = [
                (0,1),(2,3),(4,5),(6,7),
                (0,2),(1,3),(4,6),(5,7),
                (0,4),(1,5),(2,6),(3,7),
            ]

        for a, b in edges:
            self.line3d(*pts[a], *pts[b], col)

    def _draw_bullets(self):
        for b in self.bullets:
            sx, sy = self.proj(b[0], b[1], b[2])
            if sx is not None:
                pyxel.pset(sx, sy,     10)
                pyxel.pset(sx, sy - 1, 10)

    def _draw_explosions(self):
        for ex in self.explosions:
            prog = 15 - ex['life']
            for i in range(8):
                angle = i * 45 + prog * 8
                r = prog * 0.9
                wx = ex['x'] + pyxel.cos(angle) * r
                wy = ex['y'] + pyxel.sin(angle) * r
                sx, sy = self.proj(wx, wy, ex['z'])
                if sx is not None:
                    col = 10 if ex['life'] > 10 else (9 if ex['life'] > 5 else 8)
                    pyxel.pset(sx, sy, col)

    def _draw_crosshair(self):
        # Aim reticle slightly ahead of ship
        ax, ay = self.proj(self.px, self.py, PLAYER_Z + 25)
        if ax is None:
            return
        for dx, dy in [(-5,0),(-2,0),(2,0),(5,0),(0,-5),(0,-2),(0,2),(0,5)]:
            if abs(dx) > 1 or abs(dy) > 1:
                pyxel.pset(ax + dx, ay + dy, 13)

    # ── draw scenes ───────────────────────────────────────────────────
    def draw(self):
        if self.scene == "title":
            self._draw_scene_title()
        elif self.scene == "game":
            self._draw_scene_game()
        elif self.scene == "gameover":
            self._draw_scene_gameover()

    def _draw_scene_title(self):
        pyxel.cls(0)
        self._draw_stars()

        # Animated ship on title
        t = pyxel.frame_count
        ox = pyxel.sin(t * 0.8) * 5
        oy = pyxel.cos(t * 0.6) * 3
        old_px, old_py = self.px, self.py
        self.px, self.py = ox, oy - 6
        self._draw_player()
        self.px, self.py = old_px, old_py

        title = "WIREFRAME SHOOTER"
        tx = (SCR_W - len(title) * 4) // 2
        pyxel.text(tx + 1, 51, title, 1)
        pyxel.text(tx,     50, title, 6)

        pyxel.text(42, 72,  "ARROWS : MOVE",  13)
        pyxel.text(42, 82,  "SPACE  : SHOOT", 13)

        if pyxel.frame_count % 50 < 35:
            msg = "PRESS SPACE TO START"
            pyxel.text((SCR_W - len(msg) * 4) // 2, 100, msg, 10)

        if self.hi > 0:
            hi = f"HI:{self.hi:05d}"
            pyxel.text((SCR_W - len(hi) * 4) // 2, 112, hi, 9)

    def _draw_scene_game(self):
        if self.hit_flash > 0 and self.hit_flash % 2 == 0:
            pyxel.cls(8)
            return

        pyxel.cls(0)
        self._draw_stars()
        self._draw_explosions()

        for e in sorted(self.enemies, key=lambda e: -e['z']):
            self._draw_enemy(e)

        self._draw_bullets()
        self._draw_player()
        self._draw_crosshair()

        # HUD
        pyxel.text(2, 2, f"SCORE:{self.score:05d}", 7)

    def _draw_scene_gameover(self):
        pyxel.cls(0)
        self._draw_stars()

        pyxel.dither(0.55)
        pyxel.rect(25, 42, 110, 44, 0)
        pyxel.dither(1.0)
        pyxel.rectb(25, 42, 110, 44, 8)

        t = "GAME OVER"
        pyxel.text((SCR_W - len(t) * 4) // 2 + 1, 50, t, 1)
        pyxel.text((SCR_W - len(t) * 4) // 2,     49, t, 8)

        s = f"SCORE  {self.score:05d}"
        pyxel.text((SCR_W - len(s) * 4) // 2, 63, s, 7)

        hi = f"HI     {self.hi:05d}"
        pyxel.text((SCR_W - len(hi) * 4) // 2, 73, hi, 9)

        if pyxel.frame_count % 50 < 35:
            msg = "PRESS SPACE TO RETRY"
            pyxel.text((SCR_W - len(msg) * 4) // 2, 88, msg, 13)


WireframeShooter()
