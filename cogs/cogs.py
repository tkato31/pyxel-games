import pyxel
import math
import random


# --- Gear描画（プロトタイプから継承） ---

class Gear:
    def __init__(self, x, y, teeth, radius, speed=0.0, angle=0.0):
        self.x = x
        self.y = y
        self.teeth = teeth
        self.radius = radius
        self.angle = angle
        self.speed = speed
        self.tooth_len = max(3, self.radius // 3)
        self.flash_timer = 0

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


# --- グリッドシステム ---

CELL_SIZE = 28
GRID_COLS = 16
GRID_ROWS = 10
GRID_X = (512 - CELL_SIZE * GRID_COLS) // 2
GRID_Y = 28
GEAR_RADIUS = 10
GEAR_TEETH = 8

CELL_EMPTY = 0
CELL_WALL = 1
CELL_MOTOR = 2
CELL_MACHINE = 3
CELL_GEAR = 4

GEAR_NORMAL = "normal"
GEAR_SAME = "same"
GEAR_LARGE = "large"
GEAR_FIXED = "fixed"


class Grid:
    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        self.cells = [[CELL_EMPTY] * cols for _ in range(rows)]
        self.gears = {}
        self.motors = {}
        self.machines = {}
        self.powered = set()

    def cell_center(self, col, row):
        return (GRID_X + col * CELL_SIZE + CELL_SIZE // 2,
                GRID_Y + row * CELL_SIZE + CELL_SIZE // 2)

    def pixel_to_cell(self, px, py):
        col = (px - GRID_X) // CELL_SIZE
        row = (py - GRID_Y) // CELL_SIZE
        if 0 <= col < self.cols and 0 <= row < self.rows:
            return col, row
        return None, None

    def can_place(self, col, row):
        return self.cells[row][col] == CELL_EMPTY

    def can_place_large(self, col, row):
        for dc in range(2):
            for dr in range(2):
                c, r = col + dc, row + dr
                if c >= self.cols or r >= self.rows:
                    return False
                if self.cells[r][c] != CELL_EMPTY:
                    return False
        return True

    def place_gear(self, col, row, gear_type=GEAR_NORMAL, teeth=GEAR_TEETH):
        if gear_type == GEAR_LARGE:
            return self.place_large_gear(col, row, teeth)
        if not self.can_place(col, row):
            return False
        cx, cy = self.cell_center(col, row)
        gear = Gear(cx, cy, teeth, GEAR_RADIUS)
        gear.flash_timer = 15
        gear.gear_type = gear_type
        self.cells[row][col] = CELL_GEAR
        self.gears[(col, row)] = gear
        self.propagate_power()
        return True

    def place_large_gear(self, col, row, teeth=GEAR_TEETH):
        if not self.can_place_large(col, row):
            return False
        cx = GRID_X + col * CELL_SIZE + CELL_SIZE
        cy = GRID_Y + row * CELL_SIZE + CELL_SIZE
        gear = Gear(cx, cy, teeth + 4, GEAR_RADIUS + 8)
        gear.flash_timer = 15
        gear.gear_type = GEAR_LARGE
        gear.origin = (col, row)
        for dc in range(2):
            for dr in range(2):
                self.cells[row + dr][col + dc] = CELL_GEAR
        self.gears[(col, row)] = gear
        self.propagate_power()
        return True

    def remove_gear(self, col, row):
        actual_pos = None
        for pos, g in self.gears.items():
            if pos == (col, row):
                actual_pos = pos
                break
            if hasattr(g, 'gear_type') and g.gear_type == GEAR_LARGE:
                oc, or_ = g.origin
                if oc <= col <= oc + 1 and or_ <= row <= or_ + 1:
                    actual_pos = pos
                    break
        if actual_pos is None:
            return None
        gear = self.gears[actual_pos]
        del self.gears[actual_pos]
        if hasattr(gear, 'gear_type') and gear.gear_type == GEAR_LARGE:
            oc, or_ = gear.origin
            for dc in range(2):
                for dr in range(2):
                    self.cells[or_ + dr][oc + dc] = CELL_EMPTY
        else:
            self.cells[actual_pos[1]][actual_pos[0]] = CELL_EMPTY
        self.propagate_power()
        return gear

    def add_motor(self, col, row, speed=1.0):
        cx, cy = self.cell_center(col, row)
        gear = Gear(cx, cy, GEAR_TEETH, GEAR_RADIUS, speed=speed)
        self.cells[row][col] = CELL_MOTOR
        self.motors[(col, row)] = gear

    def add_machine(self, col, row, direction=1):
        self.cells[row][col] = CELL_MACHINE
        self.machines[(col, row)] = {"active": False, "dir": direction}

    def add_fixed_gear(self, col, row, teeth=GEAR_TEETH):
        cx, cy = self.cell_center(col, row)
        gear = Gear(cx, cy, teeth, GEAR_RADIUS)
        gear.gear_type = GEAR_FIXED
        self.cells[row][col] = CELL_GEAR
        self.gears[(col, row)] = gear

    def add_wall(self, col, row):
        self.cells[row][col] = CELL_WALL

    def cell_neighbors(self, col, row):
        for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nc, nr = col + dc, row + dr
            if 0 <= nc < self.cols and 0 <= nr < self.rows:
                yield nc, nr

    def gear_adjacent_cells(self, pos):
        gear = self.gears.get(pos) or self.motors.get(pos)
        if gear and hasattr(gear, 'gear_type') and gear.gear_type == GEAR_LARGE:
            oc, or_ = gear.origin
            adj = set()
            for dc in range(2):
                for dr in range(2):
                    for nc, nr in self.cell_neighbors(oc + dc, or_ + dr):
                        if not (oc <= nc <= oc + 1 and or_ <= nr <= or_ + 1):
                            adj.add((nc, nr))
            return adj
        else:
            return set(self.cell_neighbors(*pos))

    def find_gear_at(self, col, row):
        if (col, row) in self.gears:
            return (col, row), self.gears[(col, row)]
        for pos, g in self.gears.items():
            if hasattr(g, 'gear_type') and g.gear_type == GEAR_LARGE:
                oc, or_ = g.origin
                if oc <= col <= oc + 1 and or_ <= row <= or_ + 1:
                    return pos, g
        if (col, row) in self.motors:
            return (col, row), self.motors[(col, row)]
        return None, None

    def propagate_power(self):
        for pos in self.gears:
            self.gears[pos].speed = 0.0

        visited = set()
        queue = []

        for pos, motor in self.motors.items():
            visited.add(pos)
            queue.append((pos, motor.speed, motor.teeth))

        while queue:
            src_pos, speed, teeth = queue.pop(0)
            for nc, nr in self.gear_adjacent_cells(src_pos):
                npos, ng = self.find_gear_at(nc, nr)
                if npos is None or npos in visited:
                    continue
                if npos not in self.gears:
                    continue
                gtype = getattr(ng, 'gear_type', GEAR_NORMAL)
                if gtype == GEAR_SAME:
                    ng.speed = speed * (teeth / ng.teeth)
                else:
                    ng.speed = -speed * (teeth / ng.teeth)
                visited.add(npos)
                queue.append((npos, ng.speed, ng.teeth))

        for pos, mdata in self.machines.items():
            mdata["active"] = False
            required_dir = mdata["dir"]
            for nc, nr in self.cell_neighbors(*pos):
                npos, ng = self.find_gear_at(nc, nr)
                if ng is None:
                    continue
                spd = ng.speed
                if spd != 0:
                    gear_dir = 1 if spd > 0 else -1
                    if gear_dir == required_dir:
                        mdata["active"] = True
                    break

    def all_machines_on(self):
        if not self.machines:
            return False
        return all(m["active"] for m in self.machines.values())

    def update(self):
        for motor in self.motors.values():
            motor.update()
        for gear in self.gears.values():
            gear.update()
            if gear.flash_timer > 0:
                gear.flash_timer -= 1

    def draw(self):
        for row in range(self.rows):
            for col in range(self.cols):
                x = GRID_X + col * CELL_SIZE
                y = GRID_Y + row * CELL_SIZE
                cell = self.cells[row][col]

                if cell == CELL_WALL:
                    pyxel.rect(x + 1, y + 1, CELL_SIZE - 2, CELL_SIZE - 2, 1)
                elif cell == CELL_EMPTY:
                    pyxel.rectb(x, y, CELL_SIZE, CELL_SIZE, 1)

        for pos, motor in self.motors.items():
            motor.draw(10)
            cx, cy = self.cell_center(*pos)
            pyxel.text(cx - 1, cy + GEAR_RADIUS + 4, "M", 10)

        for i, (pos, gear) in enumerate(self.gears.items()):
            gtype = getattr(gear, 'gear_type', GEAR_NORMAL)
            if gear.flash_timer > 0 and (pyxel.frame_count // 2) % 2 == 0:
                col = 10
            elif gtype == GEAR_SAME:
                col = 12
            elif gtype == GEAR_FIXED:
                col = 5
            elif gtype == GEAR_LARGE:
                col = 6
            else:
                col = 13
            gear.draw(col)

        for pos, mdata in self.machines.items():
            cx, cy = self.cell_center(*pos)
            active = mdata["active"]
            req_dir = mdata["dir"]
            col = 11 if active else 8
            pyxel.rect(cx - 12, cy - 12, 24, 24, 0)
            pyxel.rectb(cx - 12, cy - 12, 24, 24, col)
            pyxel.rectb(cx - 11, cy - 11, 22, 22, col)
            a = math.radians(pyxel.frame_count * 3 * req_dir)
            r = 7
            ax = cx + math.cos(a) * r
            ay = cy + math.sin(a) * r
            pyxel.line(cx, cy, ax, ay, col)
            tip_a1 = a + math.pi * 0.75
            tip_a2 = a - math.pi * 0.75
            pyxel.line(ax, ay, ax + math.cos(tip_a1) * 4, ay + math.sin(tip_a1) * 4, col)
            pyxel.line(ax, ay, ax + math.cos(tip_a2) * 4, ay + math.sin(tip_a2) * 4, col)


# --- サウンド（プロトタイプから継承） ---

def setup_sounds():
    pyxel.sounds[0].set("c3e3g3c4", "p", "7654", "n", 6)
    pyxel.sounds[1].set("f1c1", "n", "76", "n", 8)
    pyxel.sounds[2].set("c3e3g3c4e4g4", "p", "776655", "n", 5)

    pyxel.sounds[10].set("c1rc1r c1rc1r c1rc1r c1rc1r", "p", "4040 4040 4040 4040", "f", 20)
    pyxel.sounds[13].set("c1rc1r d#1rd#1r f1rf1r d#1rc1r", "p", "4040 3030 3030 4040", "f", 20)
    pyxel.sounds[11].set("c2d#2f2d#2 c2d#2f2g2 g#2g2f2d#2 f2d#2c2c2", "s", "2233 2233 3322 3322", "n", 20)
    pyxel.sounds[12].set("rrrg3 rrc3r rrrd#3 rrf3r rrrg3 rrc4r rrrd#3 c3rrr", "n", "00020020 00020020 00020020 20000000", "f", 20)
    pyxel.musics[0].set([10, 13], [11], [12])

    pyxel.sounds[20].set("c1rrrr c1rrrr d#1rrrr c1rrrr", "p", "30000 30000 20000 30000", "f", 30)
    pyxel.sounds[21].set("rrrg2r rrrd#2r rrrf2r rrrc2r", "t", "00020 00020 00020 00020", "f", 30)
    pyxel.sounds[22].set("rrrrrrrr c3rrrrrrr rrrrrrrr g2rrrrrrr rrrrrrrr d#3rrrrrrr rrrrrrrr c3rrrrrrr", "p", "00000000 20000000 00000000 20000000 00000000 20000000 00000000 10000000", "f", 30)
    pyxel.musics[1].set([20], [21], [22])


# --- ステージデータ ---

def maze_walls(open_cells, cols=GRID_COLS, rows=GRID_ROWS):
    walls = []
    for r in range(rows):
        for c in range(cols):
            if (c, r) not in open_cells:
                walls.append({"col": c, "row": r})
    return walls


STAGES = [
    {
        # Motor(↻) → 歯車3個(奇数) → Machine(↺)
        "name": "STAGE 1",
        "actions": 5,
        "motors": [{"col": 2, "row": 4, "speed": 1.0}],
        "machines": [{"col": 6, "row": 4, "dir": -1}],
        "walls": maze_walls({
            (2, 3), (3, 3), (4, 3), (5, 3), (6, 3),
            (2, 4), (3, 4), (4, 4), (5, 4), (6, 4),
            (2, 5), (3, 5), (4, 5), (5, 5), (6, 5),
        }),
        "hand": [{"type": GEAR_NORMAL, "teeth": 8, "count": 5}],
    },
    {
        # fixed(4,4): (3,4)fixed(5,4)(6,4)=4 even dir=1 Machine dir=1 OK
        "name": "STAGE 2",
        "actions": 6,
        "motors": [{"col": 2, "row": 4, "speed": 1.0}],
        "machines": [{"col": 7, "row": 4, "dir": 1}],
        "walls": maze_walls({
            (2, 3), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3),
            (2, 4), (3, 4), (4, 4), (5, 4), (6, 4), (7, 4),
            (2, 5), (3, 5), (4, 5), (5, 5), (6, 5), (7, 5),
        }),
        "hand": [{"type": GEAR_NORMAL, "teeth": 8, "count": 5}],
        "fixed_gears": [{"col": 4, "row": 4, "teeth": 8}],
    },
    {
        # Machine A(6,3) dir=-1: (2,4)(3,4)(3,3)(4,3)(5,3)=5 odd dir=-1 OK
        # Machine B(5,5) dir=1: (2,4)(3,4)(3,5)(4,5)=4 even dir=1
        #   but 4 normal=even=dir1. OR 3 normal+1 same=still dir1.
        #   Player must use same-dir gear to solve B with fewer gears
        "name": "STAGE 3",
        "actions": 10,
        "motors": [{"col": 1, "row": 4, "speed": 1.0}],
        "machines": [
            {"col": 6, "row": 3, "dir": -1},
            {"col": 5, "row": 5, "dir": 1},
        ],
        "fixed_gears": [],
        "walls": maze_walls({
            (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3),
            (1, 4), (2, 4), (3, 4),
            (1, 5), (2, 5), (3, 5), (4, 5), (5, 5),
        }),
        "hand": [
            {"type": GEAR_NORMAL, "teeth": 8, "count": 7},
            {"type": GEAR_SAME, "teeth": 8, "count": 2},
        ],
    },
    {
        # S4: large gear intro
        # normal 6 = even = dir1. Machine needs dir=-1.
        # large gear skips 1 cell -> 5 effective = odd = dir=-1 OK
        # (2,4)(3,4) + large(4,3) + (6,4)(7,4) = 5 chain = odd
        "name": "STAGE 4",
        "actions": 6,
        "motors": [{"col": 1, "row": 4, "speed": 1.0}],
        "machines": [{"col": 8, "row": 4, "dir": -1}],
        "fixed_gears": [],
        "walls": maze_walls({
            (1, 4), (2, 4), (3, 4), (4, 3), (5, 3), (4, 4), (5, 4), (6, 4), (7, 4), (8, 4),
            (1, 3), (2, 3), (3, 3), (6, 3), (7, 3), (8, 3),
            (1, 5), (2, 5), (3, 5), (6, 5), (7, 5), (8, 5),
        }),
        "hand": [
            {"type": GEAR_NORMAL, "teeth": 8, "count": 4},
            {"type": GEAR_LARGE, "teeth": 8, "count": 1},
        ],
    },
    {
        # S5: fixed + same + normal combo
        # Motor(1,4) -> fixed(3,4) -> branch
        # Upper: (2,4)(4,4)(4,3)(5,3)(6,3) = 5+fixed = 6 chain even dir=1
        #   Machine A(7,3) dir=1 OK
        # Lower: (2,4)(4,4)(4,5)(5,5) = 4+fixed = 5 chain odd dir=-1
        #   Machine B(6,5) dir=1 -> need same-dir at (5,5) to keep dir=1
        #   with same: (2,4) dir-1, fixed(3,4) dir1, (4,4) dir-1, (4,5) dir1, same(5,5) dir1
        #   Machine B(6,5) gets dir=1 OK
        "name": "STAGE 5",
        "actions": 10,
        "motors": [{"col": 1, "row": 4, "speed": 1.0}],
        "machines": [
            {"col": 7, "row": 3, "dir": 1},
            {"col": 6, "row": 5, "dir": 1},
        ],
        "fixed_gears": [{"col": 3, "row": 4, "teeth": 8}],
        "walls": maze_walls({
            (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3),
            (1, 4), (2, 4), (3, 4), (4, 4),
            (1, 5), (2, 5), (3, 5), (4, 5), (5, 5), (6, 5),
        }),
        "hand": [
            {"type": GEAR_NORMAL, "teeth": 8, "count": 6},
            {"type": GEAR_SAME, "teeth": 8, "count": 2},
        ],
    },
    {
        # S6: all types - large + fixed + same
        # Motor(1,4) -> (2,4) -> large(3,3) -> (5,3)(6,3) = Machine A(7,3) dir=-1
        #   chain: (2,4)dir-1, large(3,3)dir1, (5,3)dir-1, (6,3)dir1
        #   Machine A gets dir=1. needs -1 -> use same at (6,3): keeps dir=-1
        #   chain: (2,4)d-1, large(3,3)d1, (5,3)d-1, same(6,3)d-1 -> Machine A d-1 OK
        # Lower: large(3,3) also adj to (3,5)(4,5) area
        #   (2,4) -> large(3,3) -> fixed(3,5) -> (4,5)(5,5)
        #   chain: (2,4)d-1, large(3,3)d1, fixed(3,5)d-1, (4,5)d1, (5,5)d-1
        #   Machine B(6,5) gets d-1, needs d1 -> use same at (5,5)
        #   with same(5,5): d1 -> Machine B d1 OK
        "name": "STAGE 6",
        "actions": 10,
        "motors": [{"col": 1, "row": 4, "speed": 1.0}],
        "machines": [
            {"col": 7, "row": 3, "dir": -1},
            {"col": 6, "row": 5, "dir": 1},
        ],
        "fixed_gears": [{"col": 3, "row": 5, "teeth": 8}],
        "walls": maze_walls({
            (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3),
            (1, 4), (2, 4), (3, 4), (4, 4),
            (1, 5), (2, 5), (3, 5), (4, 5), (5, 5), (6, 5),
        }),
        "hand": [
            {"type": GEAR_NORMAL, "teeth": 8, "count": 4},
            {"type": GEAR_SAME, "teeth": 8, "count": 2},
            {"type": GEAR_LARGE, "teeth": 8, "count": 1},
        ],
    },
]


# --- 8x8フォント（プロトタイプから継承） ---

FONT8 = {
    "S": ["  ####  ", " #    # ", " #      ", "  ####  ", "      # ", " #    # ", "  ####  ", "        "],
    "T": [" ###### ", "   ##   ", "   ##   ", "   ##   ", "   ##   ", "   ##   ", "   ##   ", "        "],
    "A": ["  ####  ", " #    # ", " #    # ", " ###### ", " #    # ", " #    # ", " #    # ", "        "],
    "G": ["  ####  ", " #    # ", " #      ", " #  ### ", " #    # ", " #    # ", "  ####  ", "        "],
    "E": [" ###### ", " #      ", " #      ", " ####   ", " #      ", " #      ", " ###### ", "        "],
    " ": ["        "] * 8,
    "1": ["   ##   ", "  ###   ", "   ##   ", "   ##   ", "   ##   ", "   ##   ", " ###### ", "        "],
    "2": ["  ####  ", " #    # ", "      # ", "   ###  ", "  #     ", " #      ", " ###### ", "        "],
    "3": ["  ####  ", " #    # ", "      # ", "   ###  ", "      # ", " #    # ", "  ####  ", "        "],
    "4": [" #    # ", " #    # ", " #    # ", " ###### ", "      # ", "      # ", "      # ", "        "],
    "5": [" ###### ", " #      ", " #      ", " #####  ", "      # ", " #    # ", "  ####  ", "        "],
    "6": ["  ####  ", " #      ", " #      ", " #####  ", " #    # ", " #    # ", "  ####  ", "        "],
}


def draw_text8(x, y, text, col, scale=3):
    cx = x
    for ch in text:
        glyph = FONT8.get(ch)
        if glyph:
            for row in range(8):
                for c in range(8):
                    if glyph[row][c] == "#":
                        pyxel.rect(cx + c * scale, y + row * scale, scale, scale, col)
        cx += 9 * scale


# --- モザイクフェード（プロトタイプから継承） ---

FADE_STEPS = [2, 3, 4, 6, 8, 12, 16, 24, 32, 48, 64]
FADE_OUT_FRAMES = [5, 5, 4, 4, 3, 3, 2, 2, 1, 1, 1]
FADE_IN_FRAMES = [1, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5]


# --- ボーナスシステム ---

BONUS_POOLS = [
    # Stage 1 clear
    [
        {"type": GEAR_NORMAL, "teeth": 8, "count": 2},
        {"type": GEAR_NORMAL, "teeth": 8, "count": 1},
        {"type": GEAR_SAME, "teeth": 8, "count": 1},
    ],
    # Stage 2 clear
    [
        {"type": GEAR_NORMAL, "teeth": 8, "count": 2},
        {"type": GEAR_SAME, "teeth": 8, "count": 1},
        {"type": GEAR_NORMAL, "teeth": 8, "count": 3},
    ],
    # Stage 3 clear
    [
        {"type": GEAR_SAME, "teeth": 8, "count": 1},
        {"type": GEAR_LARGE, "teeth": 8, "count": 1},
        {"type": GEAR_NORMAL, "teeth": 8, "count": 2},
    ],
    # Stage 4 clear
    [
        {"type": GEAR_LARGE, "teeth": 8, "count": 1},
        {"type": GEAR_SAME, "teeth": 8, "count": 2},
        {"type": GEAR_NORMAL, "teeth": 8, "count": 3},
    ],
    # Stage 5 clear
    [
        {"type": GEAR_LARGE, "teeth": 8, "count": 1},
        {"type": GEAR_SAME, "teeth": 8, "count": 2},
        {"type": GEAR_LARGE, "teeth": 8, "count": 1},
    ],
]


# --- メインアプリ ---

class App:
    def __init__(self):
        pyxel.init(512, 384, title="COGS")
        pyxel.colors[0] = 0x1C2833
        pyxel.mouse(True)
        setup_sounds()

        self.stage_idx = 0
        self.grid = None
        self.hand = []
        self.selected_hand = -1
        self.actions_left = 0
        self.cleared = False
        self.clear_timer = 0
        self.game_over = False
        self.all_clear = False
        self.intro_timer = 0
        self.message = ""
        self.message_timer = 0
        self.on_title = True
        self.current_bgm = -1
        self.fade_state = 0
        self.fade_timer = 0
        self.fade_step_idx = 0
        self.fade_next_stage = -1
        self.bonus_inventory = []
        self.bonus_selecting = False
        self.bonus_choices = []
        self.bonus_selected = -1

        self.play_bgm(1)
        pyxel.run(self.update, self.draw)

    def play_bgm(self, idx):
        if self.current_bgm != idx:
            self.current_bgm = idx
            pyxel.playm(idx, loop=True)

    def load_stage(self, idx):
        self.stage_idx = idx
        self.selected_hand = -1
        self.cleared = False
        self.clear_timer = 0
        self.game_over = False
        self.intro_timer = 120
        self.message = ""
        self.message_timer = 0

        stage = STAGES[idx]
        self.actions_left = stage["actions"]

        self.grid = Grid(GRID_COLS, GRID_ROWS)
        for m in stage["motors"]:
            self.grid.add_motor(m["col"], m["row"], m["speed"])
        for m in stage["machines"]:
            self.grid.add_machine(m["col"], m["row"], m.get("dir", 1))
        for w in stage["walls"]:
            self.grid.add_wall(w["col"], w["row"])
        for fg in stage.get("fixed_gears", []):
            self.grid.add_fixed_gear(fg["col"], fg["row"], fg.get("teeth", GEAR_TEETH))
        self.grid.propagate_power()

        self.hand = []
        for hd in stage["hand"]:
            self.hand.append({
                "type": hd.get("type", GEAR_NORMAL),
                "teeth": hd["teeth"],
                "count": hd["count"],
            })
        for bonus in self.bonus_inventory:
            found = False
            for h in self.hand:
                if h["type"] == bonus["type"] and h["teeth"] == bonus["teeth"]:
                    h["count"] += bonus["count"]
                    found = True
                    break
            if not found:
                self.hand.append({
                    "type": bonus["type"],
                    "teeth": bonus["teeth"],
                    "count": bonus["count"],
                })

    def show_message(self, text, frames=60):
        self.message = text
        self.message_timer = frames

    def try_place(self, col, row):
        if self.actions_left <= 0:
            self.show_message("NO ACTIONS LEFT!")
            pyxel.play(3, 1)
            return

        if self.selected_hand < 0 or self.selected_hand >= len(self.hand):
            return

        h = self.hand[self.selected_hand]
        if h["count"] <= 0:
            return

        gtype = h.get("type", GEAR_NORMAL)
        if gtype == GEAR_LARGE:
            if not self.grid.can_place_large(col, row):
                self.show_message("CANT PLACE HERE!")
                pyxel.play(3, 1)
                return
        else:
            if not self.grid.can_place(col, row):
                self.show_message("CANT PLACE HERE!")
                pyxel.play(3, 1)
                return

        self.grid.place_gear(col, row, gear_type=gtype, teeth=h["teeth"])
        h["count"] -= 1
        self.actions_left -= 1
        pyxel.play(3, 0)

        if h["count"] <= 0 and self.selected_hand >= 0:
            self.selected_hand = -1

        if self.grid.all_machines_on():
            self.cleared = True
            self.game_over = False
            self.clear_timer = 0
            self.message = ""
            self.message_timer = 0
            pyxel.play(3, 2)
        elif self.actions_left <= 0:
            self.game_over = True

    def start_bonus_select(self):
        self.bonus_selecting = True
        self.bonus_selected = -1
        self.bonus_choices = BONUS_POOLS[self.stage_idx]
        self.cleared = False

    def update_bonus(self):
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx, my = pyxel.mouse_x, pyxel.mouse_y
            for i in range(len(self.bonus_choices)):
                bx = 80 + i * 140
                if bx - 30 <= mx <= bx + 30 and 160 <= my <= 220:
                    self.bonus_selected = i
                    return

        if self.bonus_selected >= 0 and pyxel.btnp(pyxel.KEY_RETURN):
            choice = self.bonus_choices[self.bonus_selected]
            found = False
            for b in self.bonus_inventory:
                if b["type"] == choice["type"] and b["teeth"] == choice["teeth"]:
                    b["count"] += choice["count"]
                    found = True
                    break
            if not found:
                self.bonus_inventory.append(dict(choice))
            self.bonus_selecting = False
            self.bonus_selected = -1
            if self.stage_idx + 1 < len(STAGES):
                self.fade_state = 1
                self.fade_timer = 0
                self.fade_next_stage = self.stage_idx + 1
            else:
                self.all_clear = True
                self.play_bgm(1)

    def draw_bonus(self):
        pyxel.text((512 - 13 * 4) // 2, 80, "BONUS SELECT!", 10)
        pyxel.text((512 - 24 * 4) // 2, 96, "CHOOSE A GEAR TO KEEP", 5)

        type_colors = {GEAR_NORMAL: 13, GEAR_SAME: 12, GEAR_LARGE: 6}
        type_labels = {GEAR_NORMAL: "", GEAR_SAME: "=", GEAR_LARGE: "L"}

        for i, choice in enumerate(self.bonus_choices):
            bx = 80 + i * 140
            by = 170
            gtype = choice.get("type", GEAR_NORMAL)
            selected = (i == self.bonus_selected)
            col = 10 if selected else type_colors.get(gtype, 7)

            if selected:
                pyxel.rectb(bx - 35, by - 40, 70, 90, 10)

            r = GEAR_RADIUS + 8 if gtype == GEAR_LARGE else GEAR_RADIUS
            gear = Gear(bx, by, choice["teeth"], r)
            gear.draw(col)

            label = type_labels.get(gtype, "")
            pyxel.text(bx - 8, by + r + 8, f'{label}{choice["teeth"]}T x{choice["count"]}', 7)

        if self.bonus_selected >= 0:
            pyxel.text((512 - 18 * 4) // 2, 280, "PRESS ENTER TO GET", 7)

        pyxel.text(4, 4, "COGS", 7)
        inv_text = "INVENTORY: "
        for b in self.bonus_inventory:
            tl = type_labels.get(b["type"], "")
            inv_text += f'{tl}{b["teeth"]}Tx{b["count"]} '
        pyxel.text(4, 370, inv_text if self.bonus_inventory else "INVENTORY: (empty)", 5)

    def try_remove(self, col, row):
        pos, gear = self.grid.find_gear_at(col, row)
        if gear is None or pos not in self.grid.gears:
            return
        gtype = getattr(gear, 'gear_type', GEAR_NORMAL)
        if gtype == GEAR_FIXED:
            return
        removed = self.grid.remove_gear(col, row)
        if removed:
            for h in self.hand:
                if h.get("type", GEAR_NORMAL) == gtype and h["teeth"] == removed.teeth:
                    h["count"] += 1
                    break

    def update(self):
        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()

        if self.on_title:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.on_title = False
                self.load_stage(0)
                self.play_bgm(0)
            return

        if self.fade_state > 0:
            self.fade_timer += 1
            durations = FADE_OUT_FRAMES if self.fade_state == 1 else FADE_IN_FRAMES
            accum = 0
            step_idx = 0
            for i, d in enumerate(durations):
                accum += d
                if self.fade_timer <= accum:
                    step_idx = i
                    break
            else:
                step_idx = len(durations)
            if self.fade_state == 1 and step_idx >= len(FADE_STEPS):
                self.fade_state = 2
                self.fade_timer = 0
                self.load_stage(self.fade_next_stage)
                self.play_bgm(0)
                self.fade_next_stage = -1
            elif self.fade_state == 2 and step_idx >= len(FADE_STEPS):
                self.fade_state = 0
                self.fade_timer = 0
            self.fade_step_idx = min(step_idx, len(FADE_STEPS) - 1)
            return

        if self.intro_timer > 0:
            self.intro_timer -= 1
            return

        if self.bonus_selecting:
            self.update_bonus()
            return

        if self.cleared:
            self.clear_timer += 1
            self.grid.update()
            if self.clear_timer > 120 and pyxel.btnp(pyxel.KEY_RETURN):
                if self.stage_idx < len(BONUS_POOLS):
                    self.start_bonus_select()
                elif self.stage_idx + 1 < len(STAGES):
                    self.fade_state = 1
                    self.fade_timer = 0
                    self.fade_next_stage = self.stage_idx + 1
                else:
                    self.all_clear = True
                    self.play_bgm(1)
            return

        if self.game_over:
            if pyxel.btnp(pyxel.KEY_RETURN):
                self.load_stage(self.stage_idx)
                self.play_bgm(0)
            return

        self.grid.update()

        if self.message_timer > 0:
            self.message_timer -= 1

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            mx, my = pyxel.mouse_x, pyxel.mouse_y

            hand_y = 310
            if my >= hand_y:
                hx = 60
                for i, h in enumerate(self.hand):
                    if h["count"] > 0 and hx - 14 <= mx <= hx + 14:
                        self.selected_hand = i if self.selected_hand != i else -1
                        return
                    hx += 80
                return

            col, row = self.grid.pixel_to_cell(mx, my)
            if col is not None and self.selected_hand >= 0:
                self.try_place(col, row)

        if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
            mx, my = pyxel.mouse_x, pyxel.mouse_y
            col, row = self.grid.pixel_to_cell(mx, my)
            if col is not None:
                self.try_remove(col, row)

    def draw(self):
        pyxel.cls(0)
        self.draw_scene()
        if self.fade_state > 0:
            step_idx = self.fade_step_idx
            if self.fade_state == 1:
                bs = FADE_STEPS[step_idx]
            else:
                bs = FADE_STEPS[len(FADE_STEPS) - 1 - step_idx]
            for y in range(0, 384, bs):
                for x in range(0, 512, bs):
                    col = pyxel.pget(min(x + bs // 2, 511), min(y + bs // 2, 383))
                    pyxel.rect(x, y, bs, bs, col)

    def draw_scene(self):
        if self.on_title:
            msg1 = "COGS"
            pyxel.text((512 - len(msg1) * 4) // 2, 150, msg1, 7)
            sub = "Fill the missing cog."
            pyxel.text((512 - len(sub) * 4) // 2, 170, sub, 5)
            blink = (pyxel.frame_count // 20) % 2
            if blink:
                msg = "PRESS ENTER TO START"
                pyxel.text((512 - len(msg) * 4) // 2, 250, msg, 7)
            return

        if self.bonus_selecting:
            self.draw_bonus()
            return

        stage = STAGES[self.stage_idx]

        if self.all_clear:
            msg1 = "ALL STAGES CLEAR!"
            msg2 = "THANK YOU FOR PLAYING!"
            pyxel.text((512 - len(msg1) * 4) // 2, 170, msg1, 10)
            pyxel.text((512 - len(msg2) * 4) // 2, 186, msg2, 7)
            return

        if self.intro_timer > 0:
            name = stage["name"]
            col = 10 if (self.intro_timer // 4) % 2 == 0 else 7
            scale = 3
            cw = 9 * scale
            tw = len(name) * cw
            tx = (512 - tw) // 2
            draw_text8(tx, 155, name, col, scale)
            msg = "GET READY..."
            pyxel.text((512 - len(msg) * 4) // 2, 195, msg, 5)
            return

        pyxel.text(4, 4, "COGS", 7)
        pyxel.text(4, 14, stage["name"], 5)
        act_col = 8 if self.actions_left <= 1 else 7
        pyxel.text(400, 4, f"ACTIONS: {self.actions_left}", act_col)

        remaining = sum(h["count"] for h in self.hand)
        pyxel.text(400, 14, f"GEARS: {remaining}", 7)

        if not self.cleared:
            msg = "LEFT CLICK: PLACE / RIGHT CLICK: REMOVE"
            pyxel.text((512 - len(msg) * 4) // 2, 18, msg, 5)

        self.grid.draw()

        if self.selected_hand >= 0 and not self.cleared:
            mx, my = pyxel.mouse_x, pyxel.mouse_y
            col, row = self.grid.pixel_to_cell(mx, my)
            if col is not None and self.grid.can_place(col, row):
                cx, cy = self.grid.cell_center(col, row)
                if (pyxel.frame_count // 10) % 3 != 0:
                    ghost = Gear(cx, cy, self.hand[self.selected_hand]["teeth"], GEAR_RADIUS)
                    ghost.draw(1)

        pyxel.rect(0, 300, 512, 384, 1)
        pyxel.text(4, 303, "HandGear:", 7)
        hx = 60
        type_colors = {GEAR_NORMAL: 13, GEAR_SAME: 12, GEAR_LARGE: 6}
        type_labels = {GEAR_NORMAL: "", GEAR_SAME: "=", GEAR_LARGE: "L"}
        for i, h in enumerate(self.hand):
            if h["count"] > 0:
                gtype = h.get("type", GEAR_NORMAL)
                if i == self.selected_hand:
                    col = 10
                else:
                    col = type_colors.get(gtype, 7)
                r = GEAR_RADIUS + 8 if gtype == GEAR_LARGE else GEAR_RADIUS
                gear = Gear(hx, 340, h["teeth"], r)
                gear.draw(col)
                label = type_labels.get(gtype, "")
                pyxel.text(hx - 6, 358, f'{label}{h["teeth"]}T', 7)
                pyxel.text(hx - 4, 368, f'x{h["count"]}', 7)
            hx += 80

        if self.message_timer > 0:
            tw = len(self.message) * 4
            tx = (512 - tw) // 2
            pyxel.text(tx, 288, self.message, 8)

        if self.cleared:
            msg1 = "STAGE CLEAR!"
            pyxel.text((512 - len(msg1) * 4) // 2, 150, msg1, 10)
            if self.clear_timer > 120:
                if self.stage_idx + 1 < len(STAGES):
                    msg2 = "PRESS ENTER FOR NEXT"
                else:
                    msg2 = "PRESS ENTER TO FINISH"
                pyxel.text((512 - len(msg2) * 4) // 2, 166, msg2, 7)
        elif self.game_over:
            bw, bh = 180, 45
            bx = (512 - bw) // 2
            by = 150
            pyxel.rect(bx, by, bw, bh, 0)
            pyxel.rectb(bx, by, bw, bh, 8)
            pyxel.text((512 - 9 * 4) // 2, by + 10, "GAME OVER", 8)
            pyxel.text((512 - 20 * 4) // 2, by + 26, "PRESS ENTER TO RETRY", 7)


App()
