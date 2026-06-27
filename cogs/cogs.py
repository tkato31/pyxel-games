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

    def draw(self):
        if self.gear:
            return
        r = 12
        blink = (pyxel.frame_count // 15) % 2
        col = 5 if blink else 1
        pyxel.circb(self.x, self.y, r, col)
        pyxel.circb(self.x, self.y, r + 1, col)
        pyxel.text(self.x - 2, self.y - 3, "?", col)


class HandGear:
    def __init__(self, x, y, teeth, radius):
        self.x = x
        self.y = y
        self.teeth = teeth
        self.radius = radius
        self.tooth_len = max(3, self.radius // 3)
        self.selected = False

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


def find_neighbor(slot, gears):
    best = None
    best_dist = float("inf")
    for g in gears:
        dx = slot.x - g.x
        dy = slot.y - g.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < g.outer_radius() + 60 and dist < best_dist:
            best = g
            best_dist = dist
    return best


def mesh_dist(r1, r2):
    tl1 = max(3, r1 // 3)
    tl2 = max(3, r2 // 3)
    return r1 + r2 + max(tl1, tl2) + 2


# S1: [8r20] - [12r16]
# S2: [8r20] - [12r16] - [8r14]
# S3: [10r16] with [8r14] below and [12r16] left
# S4: [8r16] - [10r14] - [8r12] - [12r16]
# S5: [10r16] with [8r12] left, [12r16] right, [6r10] below
STAGES = [
    {
        "name": "STAGE 1",
        "gears": [
            {"x": 100, "y": 100, "teeth": 8, "radius": 20, "speed": 0.8},
        ],
        "slots": [
            {"x": 100 + mesh_dist(20, 16), "y": 100, "answer": 12},
        ],
        "hand": [
            {"teeth": 12, "radius": 16},
            {"teeth": 10, "radius": 15},
        ],
    },
    {
        "name": "STAGE 2",
        "gears": [
            {"x": 60, "y": 100, "teeth": 8, "radius": 20, "speed": 0.8},
        ],
        "slots": [
            {"x": 60 + mesh_dist(20, 16), "y": 100, "answer": 12},
            {"x": 60 + mesh_dist(20, 16) + mesh_dist(16, 14), "y": 100, "answer": 8},
        ],
        "hand": [
            {"teeth": 12, "radius": 16},
            {"teeth": 8, "radius": 14},
            {"teeth": 10, "radius": 15},
        ],
    },
    {
        "name": "STAGE 3",
        "gears": [
            {"x": 160, "y": 55, "teeth": 10, "radius": 16, "speed": 0.7},
        ],
        "slots": [
            {"x": 160, "y": 55 + mesh_dist(16, 14), "answer": 8},
            {"x": 160 - mesh_dist(16, 16), "y": 55, "answer": 12},
        ],
        "hand": [
            {"teeth": 8, "radius": 14},
            {"teeth": 12, "radius": 16},
            {"teeth": 6, "radius": 12},
        ],
    },
    {
        "name": "STAGE 4",
        "gears": [
            {"x": 35, "y": 90, "teeth": 8, "radius": 16, "speed": 0.8},
        ],
        "slots": [
            {"x": 35 + mesh_dist(16, 14), "y": 90, "answer": 10},
            {"x": 35 + mesh_dist(16, 14) + mesh_dist(14, 12), "y": 90, "answer": 8},
            {"x": 35 + mesh_dist(16, 14) + mesh_dist(14, 12) + mesh_dist(12, 16), "y": 90, "answer": 12},
        ],
        "hand": [
            {"teeth": 10, "radius": 14},
            {"teeth": 8, "radius": 12},
            {"teeth": 12, "radius": 16},
            {"teeth": 6, "radius": 10},
        ],
    },
    {
        "name": "STAGE 5",
        "gears": [
            {"x": 160, "y": 45, "teeth": 10, "radius": 16, "speed": 0.6},
        ],
        "slots": [
            {"x": 160 - mesh_dist(16, 12), "y": 45, "answer": 8},
            {"x": 160 + mesh_dist(16, 16), "y": 45, "answer": 12},
            {"x": 160, "y": 45 + mesh_dist(16, 10), "answer": 6},
        ],
        "hand": [
            {"teeth": 8, "radius": 12},
            {"teeth": 12, "radius": 16},
            {"teeth": 6, "radius": 10},
            {"teeth": 10, "radius": 14},
        ],
    },
]


def setup_sounds():
    # ch3: SE
    # 0: click (success)
    pyxel.sounds[0].set("c3e3g3c4", "p", "7654", "n", 6)
    pyxel.sounds[1].set("f1c1", "n", "76", "n", 8)
    pyxel.sounds[2].set("c3e3g3c4e4g4", "p", "776655", "n", 5)


GEAR_COLORS = [13, 6, 11, 14, 12, 9, 3]


class App:
    def __init__(self):
        pyxel.init(320, 240, title="COGS")
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

        self.load_stage(0)

        pyxel.run(self.update, self.draw)

    def load_stage(self, idx):
        self.stage_idx = idx
        self.gears.clear()
        self.slots.clear()
        self.hand.clear()
        self.selected_hand = None
        self.message = ""
        self.message_timer = 0
        self.cleared = False
        self.clear_timer = 0

        stage = STAGES[idx]

        for gd in stage["gears"]:
            self.gears.append(Gear(**gd, fixed=True))

        for sd in stage["slots"]:
            self.slots.append(Slot(sd["x"], sd["y"], sd["answer"]))

        hand_start_x = 40
        spacing = 70
        for i, hd in enumerate(stage["hand"]):
            self.hand.append(HandGear(hand_start_x + i * spacing, 210, hd["teeth"], hd["radius"]))

    def show_message(self, text, frames=90):
        self.message = text
        self.message_timer = frames

    def try_place(self, slot, hand_gear):
        neighbor = find_neighbor(slot, self.gears)
        if not neighbor:
            self.show_message("NO NEIGHBOR", 60)
            return

        if hand_gear.teeth != slot.answer_teeth:
            self.show_message("MISS!", 60)
            pyxel.play(3, 1)
            return

        speed = calc_mesh_speed(neighbor, hand_gear.teeth)
        angle = calc_mesh_angle(neighbor, hand_gear.teeth)

        new_gear = Gear(x=slot.x, y=slot.y, teeth=hand_gear.teeth,
                        radius=hand_gear.radius, speed=speed,
                        angle=angle, fixed=True)
        self.gears.append(new_gear)
        slot.gear = new_gear

        self.hand.remove(hand_gear)
        self.selected_hand = None
        pyxel.play(3, 0)

        if all(s.gear for s in self.slots):
            self.cleared = True
            self.clear_timer = 0
            self.message = ""
            self.message_timer = 0
            pyxel.play(3, 2)

    def update(self):
        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()

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

    def draw(self):
        pyxel.cls(0)

        stage = STAGES[self.stage_idx]
        pyxel.text(4, 4, "COGS", 7)
        pyxel.text(4, 14, stage["name"], 5)

        if self.all_clear:
            pyxel.text(100, 100, "ALL STAGES CLEAR!", 10)
            pyxel.text(90, 116, "THANK YOU FOR PLAYING!", 7)
            return

        if not self.cleared:
            pyxel.text(4, 24, "SELECT A GEAR, THEN CLICK A SLOT", 5)

        for s in self.slots:
            s.draw()

        for i, g in enumerate(self.gears):
            if self.cleared and (pyxel.frame_count // 4) % 2 == 0:
                col = 10
            else:
                col = GEAR_COLORS[i % len(GEAR_COLORS)]
            g.draw(col)

        pyxel.rect(0, 185, 320, 240, 1)
        pyxel.text(4, 188, "HAND:", 7)
        for h in self.hand:
            h.draw()

        if self.message_timer > 0:
            tw = len(self.message) * 4
            tx = (320 - tw) // 2
            col = 8 if "MISS" in self.message else 10
            pyxel.text(tx, 150, self.message, col)

        if self.cleared:
            pyxel.text(120, 150, "STAGE CLEAR!", 10)
            if self.clear_timer > 120:
                if self.stage_idx + 1 < len(STAGES):
                    pyxel.text(100, 166, "PRESS ENTER FOR NEXT", 7)
                else:
                    pyxel.text(100, 166, "PRESS ENTER TO FINISH", 7)


App()
