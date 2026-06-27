import pyxel
import math


class Gear:
    def __init__(self, x, y, teeth, radius, speed=0.0, angle=0.0, fixed=True):
        self.x = x
        self.y = y
        self.teeth = teeth
        self.radius = radius
        self.angle = angle
        self.speed = speed
        self.fixed = fixed
        self.tooth_len = max(3, self.radius // 3)
        self.base_speed = speed

    def update(self, speed_mult=1.0):
        self.angle += self.speed * speed_mult

    def outer_radius(self):
        return self.radius + self.tooth_len

    def draw(self, col):
        tl = self.tooth_len
        base_half = math.pi / self.teeth * 0.7
        tip_half = math.pi / self.teeth * 0.4

        for i in range(self.teeth):
            a = math.radians(self.angle) + 2 * math.pi * i / self.teeth
            bl = a - base_half
            br = a + base_half
            tla = a - tip_half
            tra = a + tip_half
            r_in = self.radius
            r_out = self.radius + tl
            x1 = self.x + math.cos(bl) * r_in
            y1 = self.y + math.sin(bl) * r_in
            x2 = self.x + math.cos(br) * r_in
            y2 = self.y + math.sin(br) * r_in
            x3 = self.x + math.cos(tra) * r_out
            y3 = self.y + math.sin(tra) * r_out
            x4 = self.x + math.cos(tla) * r_out
            y4 = self.y + math.sin(tla) * r_out
            pyxel.tri(x1, y1, x2, y2, x3, y3, col)
            pyxel.tri(x1, y1, x3, y3, x4, y4, col)

        pyxel.circ(self.x, self.y, self.radius, col)

        spoke_col = 0
        n_spokes = 4
        for i in range(n_spokes):
            sa = math.radians(self.angle) + 2 * math.pi * i / n_spokes
            sx = self.x + math.cos(sa) * (self.radius + tl)
            sy = self.y + math.sin(sa) * (self.radius + tl)
            pyxel.line(self.x, self.y, sx, sy, spoke_col)

        hole_r = max(2, self.radius // 3)
        pyxel.circ(self.x, self.y, hole_r, 0)
        pyxel.circb(self.x, self.y, hole_r, col)
        pyxel.pset(self.x, self.y, col)


class Slot:
    def __init__(self, x, y, answer_teeth):
        self.x = x
        self.y = y
        self.answer_teeth = answer_teeth
        self.gear = None

    def draw(self, active=False):
        if self.gear:
            return
        r = 18
        if active:
            blink = (pyxel.frame_count // 15) % 2
            col = 5 if blink else 6
        else:
            col = 1
        pyxel.circb(self.x, self.y, r, col)
        pyxel.circb(self.x, self.y, r + 1, col)
        pyxel.circb(self.x, self.y, r + 2, col)
        pyxel.text(self.x - 2, self.y - 3, "?", col)


class HandGear:
    def __init__(self, x, y, teeth, radius, hand_index=0):
        self.x = x
        self.y = y
        self.teeth = teeth
        self.radius = radius
        self.tooth_len = max(3, self.radius // 3)
        self.selected = False
        self.hand_index = hand_index

    def draw(self):
        col = 10 if self.selected else 7
        gear = Gear(self.x, self.y, self.teeth, self.radius)
        gear.draw(col)
        label = str(self.teeth)
        pyxel.text(self.x - len(label) * 2, self.y + self.radius + self.tooth_len + 4, label, 7)

    def hit(self, mx, my):
        dx = mx - self.x
        dy = my - self.y
        return dx * dx + dy * dy <= (self.radius + self.tooth_len) ** 2


def calc_mesh_speed(driver, driven_teeth):
    return -driver.speed * (driver.teeth / driven_teeth)


def calc_mesh_angle(driver, driven_teeth):
    step = 360.0 / driven_teeth
    return driver.angle * (-driver.teeth / driven_teeth) + step / 2


def is_adjacent(x1, y1, r1, x2, y2, r2):
    dx = x2 - x1
    dy = y2 - y1
    dist = math.sqrt(dx * dx + dy * dy)
    expected = mesh_dist(r1, r2)
    return dist < expected + 10


def find_neighbor(slot, gears):
    best = None
    best_dist = float("inf")
    for g in gears:
        dx = slot.x - g.x
        dy = slot.y - g.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < g.outer_radius() + 100 and dist < best_dist:
            best = g
            best_dist = dist
    return best


def find_all_neighbors(slot, gears, slot_radius=None):
    neighbors = []
    for g in gears:
        if slot_radius is not None:
            if is_adjacent(slot.x, slot.y, slot_radius, g.x, g.y, g.radius):
                neighbors.append(g)
        else:
            dx = slot.x - g.x
            dy = slot.y - g.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < g.outer_radius() + 100:
                neighbors.append(g)
    return neighbors


def mesh_dist(r1, r2):
    tl1 = max(3, r1 // 3)
    tl2 = max(3, r2 // 3)
    return r1 + r2 + max(tl1, tl2) + 2


# module=4: radius = teeth * 2
# XL: 20t r=40  L: 16t r=32  M: 12t r=24  S: 8t r=16  XS: 6t r=12
# dummy: 10t r=20, 14t r=28
def gr(teeth):
    return teeth * 2


STAGES = [
    {
        "name": "STAGE 1",
        "actions": 2,
        "gears": [
            {"x": 160, "y": 140, "teeth": 16, "radius": gr(16), "speed": 0.5},
        ],
        "slots": [
            {"x": 160 + mesh_dist(gr(16), gr(12)), "y": 140, "answer": 12},
        ],
        "hand": [
            {"teeth": 12, "radius": gr(12)},
            {"teeth": 10, "radius": gr(10)},
        ],
    },
    {
        "name": "STAGE 2",
        "actions": 4,
        "gears": [
            {"x": 80, "y": 140, "teeth": 20, "radius": gr(20), "speed": 0.4},
        ],
        "slots": [
            {"x": 80 + mesh_dist(gr(20), gr(12)), "y": 140, "answer": 12},
            {"x": 80 + mesh_dist(gr(20), gr(12)) + mesh_dist(gr(12), gr(8)), "y": 140, "answer": 8},
        ],
        "hand": [
            {"teeth": 12, "radius": gr(12)},
            {"teeth": 8, "radius": gr(8)},
            {"teeth": 10, "radius": gr(10)},
        ],
    },
    {
        "name": "STAGE 3",
        "actions": 4,
        "gears": [
            {"x": 256, "y": 80, "teeth": 16, "radius": gr(16), "speed": 0.5},
        ],
        "slots": [
            {"x": 256, "y": 80 + mesh_dist(gr(16), gr(8)), "answer": 8},
            {"x": 256 - mesh_dist(gr(16), gr(20)), "y": 80, "answer": 20},
        ],
        "hand": [
            {"teeth": 8, "radius": gr(8)},
            {"teeth": 20, "radius": gr(20)},
            {"teeth": 14, "radius": gr(14)},
        ],
    },
    {
        "name": "STAGE 4",
        "actions": 5,
        "gears": [
            {"x": 50, "y": 140, "teeth": 6, "radius": gr(6), "speed": 1.2},
        ],
        "slots": [
            {"x": 50 + mesh_dist(gr(6), gr(12)), "y": 140, "answer": 12},
            {"x": 50 + mesh_dist(gr(6), gr(12)) + mesh_dist(gr(12), gr(8)), "y": 140, "answer": 8},
            {"x": 50 + mesh_dist(gr(6), gr(12)) + mesh_dist(gr(12), gr(8)) + mesh_dist(gr(8), gr(20)), "y": 140, "answer": 20},
        ],
        "hand": [
            {"teeth": 12, "radius": gr(12)},
            {"teeth": 8, "radius": gr(8)},
            {"teeth": 20, "radius": gr(20)},
            {"teeth": 14, "radius": gr(14)},
        ],
    },
    {
        "name": "STAGE 5",
        "actions": 6,
        "gears": [
            {"x": 256, "y": 70, "teeth": 16, "radius": gr(16), "speed": 0.5},
        ],
        "slots": [
            {"x": 256 - mesh_dist(gr(16), gr(6)), "y": 70, "answer": 6},
            {"x": 256 + mesh_dist(gr(16), gr(20)), "y": 70, "answer": 20},
            {"x": 256, "y": 70 + mesh_dist(gr(16), gr(12)), "answer": 12},
        ],
        "hand": [
            {"teeth": 6, "radius": gr(6)},
            {"teeth": 20, "radius": gr(20)},
            {"teeth": 12, "radius": gr(12)},
            {"teeth": 10, "radius": gr(10)},
        ],
    },
]


def setup_sounds():
    # SE (ch3)
    pyxel.sounds[0].set("c3e3g3c4", "p", "7654", "n", 6)
    pyxel.sounds[1].set("f1c1", "n", "76", "n", 8)
    pyxel.sounds[2].set("c3e3g3c4e4g4", "p", "776655", "n", 5)

    # BGM ch0: bass - heavy industrial pulse (4 bars, Cm)
    pyxel.sounds[10].set(
        "c1rc1r c1rc1r c1rc1r c1rc1r",
        "p",
        "4040 4040 4040 4040",
        "f",
        20,
    )
    pyxel.sounds[13].set(
        "c1rc1r d#1rd#1r f1rf1r d#1rc1r",
        "p",
        "4040 3030 3030 4040",
        "f",
        20,
    )
    # BGM ch1: mid - mechanical grind (4 bars)
    pyxel.sounds[11].set(
        "c2d#2f2d#2 c2d#2f2g2 g#2g2f2d#2 f2d#2c2c2",
        "s",
        "2233 2233 3322 3322",
        "n",
        20,
    )
    # BGM ch2: high - sparse metallic hits (4 bars)
    pyxel.sounds[12].set(
        "rrrg3 rrc3r rrrd#3 rrf3r rrrg3 rrc4r rrrd#3 c3rrr",
        "n",
        "00020020 00020020 00020020 20000000",
        "f",
        20,
    )

    pyxel.musics[0].set([10, 13], [11], [12])


def start_bgm():
    pyxel.playm(0, loop=True)


FONT8 = {
    "S": [
        "  ####  ",
        " #    # ",
        " #      ",
        "  ####  ",
        "      # ",
        " #    # ",
        "  ####  ",
        "        ",
    ],
    "T": [
        " ###### ",
        "   ##   ",
        "   ##   ",
        "   ##   ",
        "   ##   ",
        "   ##   ",
        "   ##   ",
        "        ",
    ],
    "A": [
        "  ####  ",
        " #    # ",
        " #    # ",
        " ###### ",
        " #    # ",
        " #    # ",
        " #    # ",
        "        ",
    ],
    "G": [
        "  ####  ",
        " #    # ",
        " #      ",
        " #  ### ",
        " #    # ",
        " #    # ",
        "  ####  ",
        "        ",
    ],
    "E": [
        " ###### ",
        " #      ",
        " #      ",
        " ####   ",
        " #      ",
        " #      ",
        " ###### ",
        "        ",
    ],
    " ": [
        "        ",
        "        ",
        "        ",
        "        ",
        "        ",
        "        ",
        "        ",
        "        ",
    ],
    "1": [
        "   ##   ",
        "  ###   ",
        "   ##   ",
        "   ##   ",
        "   ##   ",
        "   ##   ",
        " ###### ",
        "        ",
    ],
    "2": [
        "  ####  ",
        " #    # ",
        "      # ",
        "   ###  ",
        "  #     ",
        " #      ",
        " ###### ",
        "        ",
    ],
    "3": [
        "  ####  ",
        " #    # ",
        "      # ",
        "   ###  ",
        "      # ",
        " #    # ",
        "  ####  ",
        "        ",
    ],
    "4": [
        " #    # ",
        " #    # ",
        " #    # ",
        " ###### ",
        "      # ",
        "      # ",
        "      # ",
        "        ",
    ],
    "5": [
        " ###### ",
        " #      ",
        " #      ",
        " #####  ",
        "      # ",
        " #    # ",
        "  ####  ",
        "        ",
    ],
}


def draw_text8(x, y, text, col, scale=2):
    cx = x
    for ch in text:
        glyph = FONT8.get(ch)
        if glyph:
            for row in range(8):
                for c in range(8):
                    if glyph[row][c] == "#":
                        px = cx + c * scale
                        py = y + row * scale
                        pyxel.rect(px, py, scale, scale, col)
        cx += 9 * scale


GEAR_COLORS = [13, 6, 11, 14, 12, 9, 3]


class App:
    def __init__(self):
        pyxel.init(512, 384, title="COGS")
        pyxel.colors[0] = 0x1C2833
        pyxel.mouse(True)
        setup_sounds()

        self.stage_idx = 0
        self.gears = []
        self.slots = []
        self.hand = []
        self.selected_hand = None
        self.message = ""
        self.message_timer = 0
        self.cleared = False
        self.clear_timer = 0
        self.all_clear = False
        self.intro_timer = 0
        self.playing = False

        self.load_stage(0)
        start_bgm()

        pyxel.run(self.update, self.draw)

    def load_stage(self, idx):
        self.stage_idx = idx
        self.gears.clear()
        self.slots.clear()
        self.hand.clear()
        self.selected_hand = None
        self.message = ""
        self.message_timer = 0
        self.intro_timer = 120
        self.playing = False
        self.cleared = False
        self.clear_timer = 0
        self.game_over = False

        stage = STAGES[idx]
        self.actions_left = stage["actions"]

        for gd in stage["gears"]:
            self.gears.append(Gear(**gd, fixed=True))

        for sd in stage["slots"]:
            self.slots.append(Slot(sd["x"], sd["y"], sd["answer"]))

        self.hand_start_x = 70
        self.hand_spacing = 100
        for i, hd in enumerate(stage["hand"]):
            x = self.hand_start_x + i * self.hand_spacing
            self.hand.append(HandGear(x, 335, hd["teeth"], hd["radius"], hand_index=i))

    def show_message(self, text, frames=90):
        self.message = text
        self.message_timer = frames

    def check_game_over(self):
        if self.cleared:
            return
        if all(s.gear for s in self.slots):
            return
        if self.actions_left <= 0:
            self.game_over = True

    def try_place(self, slot, hand_gear):
        if self.actions_left <= 0:
            self.show_message("NO ACTIONS LEFT!", 60)
            pyxel.play(3, 1)
            return

        primary = find_neighbor(slot, self.gears)
        if not primary:
            self.show_message("NO NEIGHBOR", 60)
            return

        if hand_gear.teeth != slot.answer_teeth:
            self.actions_left -= 1
            self.show_message("MISS!", 60)
            pyxel.play(3, 1)
            self.check_game_over()
            return

        speed = calc_mesh_speed(primary, hand_gear.teeth)
        angle = calc_mesh_angle(primary, hand_gear.teeth)

        tight_neighbors = find_all_neighbors(slot, self.gears, slot_radius=hand_gear.radius)
        for n in tight_neighbors:
            if n is primary:
                continue
            expected_speed = calc_mesh_speed(n, hand_gear.teeth)
            if abs(speed - expected_speed) > 0.01:
                self.actions_left -= 1
                self.show_message("BAD ORDER!", 60)
                pyxel.play(3, 1)
                self.check_game_over()
                return

        new_gear = Gear(x=slot.x, y=slot.y, teeth=hand_gear.teeth,
                        radius=hand_gear.radius, speed=speed,
                        angle=angle, fixed=True)
        new_gear.gear_hand_index = hand_gear.hand_index
        self.gears.append(new_gear)
        slot.gear = new_gear

        self.hand.remove(hand_gear)
        self.selected_hand = None
        self.actions_left -= 1
        pyxel.play(3, 0)

        if all(s.gear for s in self.slots):
            self.cleared = True
            self.game_over = False
            self.clear_timer = 0
            self.message = ""
            self.message_timer = 0
            pyxel.play(3, 2)
        elif self.actions_left <= 0:
            self.game_over = True

    def update(self):
        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()

        if self.intro_timer > 0:
            self.intro_timer -= 1
            if self.intro_timer == 0:
                self.playing = True
            return

        if self.cleared:
            self.clear_timer += 1
            speed_mult = 1.0 + self.clear_timer * 0.02
            for g in self.gears:
                g.update(speed_mult)

            if self.clear_timer > 120 and pyxel.btnp(pyxel.KEY_RETURN):
                if self.stage_idx + 1 < len(STAGES):
                    self.load_stage(self.stage_idx + 1)
                else:
                    self.all_clear = True
            return

        if self.game_over:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.load_stage(self.stage_idx)
            return

        for g in self.gears:
            g.update()

        if self.message_timer > 0:
            self.message_timer -= 1

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx, my = pyxel.mouse_x, pyxel.mouse_y

            for h in self.hand:
                if h.hit(mx, my):
                    if self.selected_hand == h:
                        h.selected = False
                        self.selected_hand = None
                    else:
                        if self.selected_hand:
                            self.selected_hand.selected = False
                        h.selected = True
                        self.selected_hand = h
                    return

            if self.selected_hand:
                for s in self.slots:
                    if s.gear:
                        continue
                    dx = mx - s.x
                    dy = my - s.y
                    if dx * dx + dy * dy <= 30 * 30:
                        self.try_place(s, self.selected_hand)
                        return

        if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT) and not self.cleared:
            mx, my = pyxel.mouse_x, pyxel.mouse_y
            for s in self.slots:
                if not s.gear:
                    continue
                dx = mx - s.x
                dy = my - s.y
                if dx * dx + dy * dy <= (s.gear.outer_radius()) ** 2:
                    self.remove_gear_chain(s)
                    return

    def remove_gear_chain(self, start_slot):
        to_remove = [start_slot]
        changed = True
        while changed:
            changed = False
            for s in self.slots:
                if not s.gear or s in to_remove:
                    continue
                neighbors = find_all_neighbors(s, self.gears)
                has_fixed = False
                for n in neighbors:
                    if n not in [rs.gear for rs in to_remove]:
                        has_fixed = True
                        break
                if not has_fixed:
                    to_remove.append(s)
                    changed = True

        for s in to_remove:
            hg = HandGear(0, 335, s.gear.teeth, s.gear.radius, hand_index=s.gear.gear_hand_index)
            hg.x = self.hand_start_x + hg.hand_index * self.hand_spacing
            self.hand.append(hg)
            self.gears.remove(s.gear)
            s.gear = None

        self.hand.sort(key=lambda h: h.hand_index)
        self.selected_hand = None
        self.game_over = False

    def draw_play_screen(self, stage):
        pyxel.text(4, 4, "COGS", 7)
        pyxel.text(4, 14, stage["name"], 5)
        act_col = 8 if self.actions_left <= 1 else 7
        pyxel.text(420, 4, f"ACTIONS: {self.actions_left}", act_col)

        if not self.cleared:
            msg = "SELECT A GEAR, THEN CLICK A SLOT"
            pyxel.text((512 - len(msg) * 4) // 2, 24, msg, 5)

        for s in self.slots:
            active = find_neighbor(s, self.gears) is not None
            s.draw(active)

        for i, g in enumerate(self.gears):
            if self.cleared and (pyxel.frame_count // 4) % 2 == 0:
                col = 10
            else:
                col = GEAR_COLORS[i % len(GEAR_COLORS)]
            g.draw(col)

        pyxel.rect(0, 295, 512, 384, 1)
        pyxel.text(4, 298, "HandGear:", 7)
        for h in self.hand:
            h.draw()

        if self.message_timer > 0:
            tw = len(self.message) * 4
            tx = (512 - tw) // 2
            col = 8 if "MISS" in self.message else 10
            pyxel.text(tx, 260, self.message, col)

    def draw(self):
        pyxel.cls(0)

        stage = STAGES[self.stage_idx]

        if self.all_clear:
            pyxel.text(4, 4, "COGS", 7)
            msg1 = "ALL STAGES CLEAR!"
            msg2 = "THANK YOU FOR PLAYING!"
            pyxel.text((512 - len(msg1) * 4) // 2, 170, msg1, 10)
            pyxel.text((512 - len(msg2) * 4) // 2, 186, msg2, 7)
            return

        if self.intro_timer > 0:
            name = stage["name"]
            col = 10 if (self.intro_timer // 4) % 2 == 0 else 7
            scale = 3
            char_w = 9 * scale
            tw = len(name) * char_w
            tx = (512 - tw) // 2
            ty = 155
            draw_text8(tx, ty, name, col, scale)

            msg = "GET READY..."
            pyxel.text((512 - len(msg) * 4) // 2, ty + 8 * scale + 10, msg, 5)
            return

        self.draw_play_screen(stage)

        if self.cleared:
            msg1 = "STAGE CLEAR!"
            pyxel.text((512 - len(msg1) * 4) // 2, 180, msg1, 10)
            if self.clear_timer > 120:
                if self.stage_idx + 1 < len(STAGES):
                    msg2 = "PRESS ENTER FOR NEXT"
                else:
                    msg2 = "PRESS ENTER TO FINISH"
                pyxel.text((512 - len(msg2) * 4) // 2, 196, msg2, 7)
        elif self.game_over:
            bw, bh = 180, 45
            bx = (512 - bw) // 2
            by = 150
            pyxel.rect(bx, by, bw, bh, 0)
            pyxel.rectb(bx, by, bw, bh, 8)
            msg1 = "GAME OVER"
            msg2 = "PRESS ENTER TO RETRY"
            pyxel.text((512 - len(msg1) * 4) // 2, by + 10, msg1, 8)
            pyxel.text((512 - len(msg2) * 4) // 2, by + 26, msg2, 7)


App()
