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
        self.power = 0.0
        self.gear_type = GEAR_NORMAL

    def update(self, speed_mult=1.0):
        self.angle += self.speed * speed_mult

    def draw(self, col):
        tl = self.tooth_len
        base_half = math.pi / self.teeth * 0.7
        tip_half = math.pi / self.teeth * 0.4
        for i in range(self.teeth):
            a = math.radians(self.angle) + 2 * math.pi * i / self.teeth
            bl, br = a - base_half, a + base_half
            tla, tra = a - tip_half, a + tip_half
            r_in, r_out = self.radius, self.radius + tl
            pyxel.tri(self.x+math.cos(bl)*r_in, self.y+math.sin(bl)*r_in,
                      self.x+math.cos(br)*r_in, self.y+math.sin(br)*r_in,
                      self.x+math.cos(tra)*r_out, self.y+math.sin(tra)*r_out, col)
            pyxel.tri(self.x+math.cos(bl)*r_in, self.y+math.sin(bl)*r_in,
                      self.x+math.cos(tra)*r_out, self.y+math.sin(tra)*r_out,
                      self.x+math.cos(tla)*r_out, self.y+math.sin(tla)*r_out, col)
        pyxel.circ(self.x, self.y, self.radius, col)
        for i in range(4):
            sa = math.radians(self.angle) + math.pi/2*i
            pyxel.line(self.x, self.y, self.x+math.cos(sa)*(self.radius+tl),
                       self.y+math.sin(sa)*(self.radius+tl), 0)
        hole_r = max(2, self.radius // 3)
        pyxel.circ(self.x, self.y, hole_r, 0)
        pyxel.circb(self.x, self.y, hole_r, col)
        pyxel.pset(self.x, self.y, col)


# --- ギアタイプ ---

GEAR_NORMAL = "normal"
GEAR_SAME = "same"
GEAR_AMP = "amp"
GEAR_REDUCE = "reduce"
GEAR_LARGE = "large"
GEAR_FIXED = "fixed"

CELL_SIZE = 32
GRID_COLS = 10
GRID_ROWS = 10
GRID_X = (512 - CELL_SIZE * GRID_COLS) // 2
GRID_Y = 24
GEAR_RADIUS = 12
GEAR_TEETH = 8
HAND_Y = 340
STATUS_Y = 0

CELL_EMPTY = 0
CELL_WALL = 1
CELL_MOTOR = 2
CELL_MACHINE = 3
CELL_GEAR = 4

TYPE_COLORS = {
    GEAR_NORMAL: 13, GEAR_SAME: 12, GEAR_AMP: 9,
    GEAR_REDUCE: 3, GEAR_LARGE: 6, GEAR_FIXED: 5,
}
TYPE_LABELS = {
    GEAR_NORMAL: "", GEAR_SAME: "=", GEAR_AMP: "+",
    GEAR_REDUCE: "-", GEAR_LARGE: "L", GEAR_FIXED: "F",
}


# --- グリッドシステム ---

class Grid:
    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        self.cells = [[CELL_EMPTY]*cols for _ in range(rows)]
        self.gears = {}
        self.motors = {}
        self.machines = {}

    def cell_center(self, col, row):
        return (GRID_X + col*CELL_SIZE + CELL_SIZE//2,
                GRID_Y + row*CELL_SIZE + CELL_SIZE//2)

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
                c, r = col+dc, row+dr
                if c >= self.cols or r >= self.rows or self.cells[r][c] != CELL_EMPTY:
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
        cx = GRID_X + col*CELL_SIZE + CELL_SIZE
        cy = GRID_Y + row*CELL_SIZE + CELL_SIZE
        gear = Gear(cx, cy, teeth+4, GEAR_RADIUS+10)
        gear.flash_timer = 15
        gear.gear_type = GEAR_LARGE
        gear.origin = (col, row)
        for dc in range(2):
            for dr in range(2):
                self.cells[row+dr][col+dc] = CELL_GEAR
        self.gears[(col, row)] = gear
        self.propagate_power()
        return True

    def remove_gear(self, col, row):
        actual_pos = None
        for pos, g in self.gears.items():
            if pos == (col, row):
                actual_pos = pos
                break
            if g.gear_type == GEAR_LARGE:
                oc, or_ = g.origin
                if oc <= col <= oc+1 and or_ <= row <= or_+1:
                    actual_pos = pos
                    break
        if actual_pos is None:
            return None
        gear = self.gears[actual_pos]
        if gear.gear_type == GEAR_FIXED:
            return None
        del self.gears[actual_pos]
        if gear.gear_type == GEAR_LARGE:
            oc, or_ = gear.origin
            for dc in range(2):
                for dr in range(2):
                    self.cells[or_+dr][oc+dc] = CELL_EMPTY
        else:
            self.cells[actual_pos[1]][actual_pos[0]] = CELL_EMPTY
        self.propagate_power()
        return gear

    def add_motor(self, col, row, speed=1.0, power=1.0):
        cx, cy = self.cell_center(col, row)
        gear = Gear(cx, cy, GEAR_TEETH, GEAR_RADIUS, speed=speed)
        gear.power = power
        self.cells[row][col] = CELL_MOTOR
        self.motors[(col, row)] = gear

    def add_machine(self, col, row, direction=1, req_power=1.0, dual=False):
        self.cells[row][col] = CELL_MACHINE
        self.machines[(col, row)] = {
            "active": False, "dir": direction,
            "req_power": req_power, "dual": dual,
            "recv_power": 0.0,
        }

    def add_fixed_gear(self, col, row, gear_type=GEAR_FIXED, teeth=GEAR_TEETH):
        cx, cy = self.cell_center(col, row)
        gear = Gear(cx, cy, teeth, GEAR_RADIUS)
        gear.gear_type = gear_type
        self.cells[row][col] = CELL_GEAR
        self.gears[(col, row)] = gear

    def add_wall(self, col, row):
        self.cells[row][col] = CELL_WALL

    def cell_neighbors(self, col, row):
        for dc, dr in [(-1,0),(1,0),(0,-1),(0,1)]:
            nc, nr = col+dc, row+dr
            if 0 <= nc < self.cols and 0 <= nr < self.rows:
                yield nc, nr

    def gear_adjacent_cells(self, pos):
        gear = self.gears.get(pos) or self.motors.get(pos)
        if gear and gear.gear_type == GEAR_LARGE:
            oc, or_ = gear.origin
            adj = set()
            for dc in range(2):
                for dr in range(2):
                    for nc, nr in self.cell_neighbors(oc+dc, or_+dr):
                        if not (oc <= nc <= oc+1 and or_ <= nr <= or_+1):
                            adj.add((nc, nr))
            return adj
        return set(self.cell_neighbors(*pos))

    def find_gear_at(self, col, row):
        if (col, row) in self.gears:
            return (col, row), self.gears[(col, row)]
        for pos, g in self.gears.items():
            if g.gear_type == GEAR_LARGE:
                oc, or_ = g.origin
                if oc <= col <= oc+1 and or_ <= row <= or_+1:
                    return pos, g
        if (col, row) in self.motors:
            return (col, row), self.motors[(col, row)]
        return None, None

    def propagate_power(self):
        for g in self.gears.values():
            g.speed = 0.0
            g.power = 0.0

        visited = set()
        queue = []

        for pos, motor in self.motors.items():
            visited.add(pos)
            queue.append(pos)

        while queue:
            src_pos = queue.pop(0)
            src = self.motors.get(src_pos) or self.gears.get(src_pos)
            if src is None:
                continue

            downstream = []
            for nc, nr in self.gear_adjacent_cells(src_pos):
                npos, ng = self.find_gear_at(nc, nr)
                if npos and npos in self.gears and npos not in visited:
                    downstream.append((npos, ng))

            if not downstream:
                continue

            split_power = src.power / len(downstream)

            for npos, ng in downstream:
                gtype = ng.gear_type
                if gtype == GEAR_SAME:
                    ng.speed = src.speed
                    ng.power += split_power
                elif gtype == GEAR_AMP:
                    ng.speed = -src.speed
                    ng.power += split_power + 1.0
                elif gtype == GEAR_REDUCE:
                    ng.speed = -src.speed
                    ng.power += max(0, split_power - 0.5)
                else:
                    ng.speed = -src.speed
                    ng.power += split_power

                if npos not in visited:
                    visited.add(npos)
                    queue.append(npos)

        for pos, mdata in self.machines.items():
            mdata["active"] = False
            mdata["recv_power"] = 0.0
            required_dir = mdata["dir"]
            req_power = mdata["req_power"]
            is_dual = mdata.get("dual", False)

            total_power = 0.0
            spinning_count = 0
            correct_dir = True
            for nc, nr in self.cell_neighbors(*pos):
                npos, ng = self.find_gear_at(nc, nr)
                if ng is None or ng.speed == 0:
                    continue
                spinning_count += 1
                total_power += ng.power
                gear_dir = 1 if ng.speed > 0 else -1
                if gear_dir != required_dir:
                    correct_dir = False

            mdata["recv_power"] = total_power
            if is_dual:
                mdata["active"] = spinning_count >= 2 and total_power >= req_power
            else:
                mdata["active"] = correct_dir and spinning_count >= 1 and total_power >= req_power

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
                x = GRID_X + col*CELL_SIZE
                y = GRID_Y + row*CELL_SIZE
                cell = self.cells[row][col]
                if cell == CELL_WALL:
                    pyxel.rect(x+1, y+1, CELL_SIZE-2, CELL_SIZE-2, 1)
                else:
                    pyxel.rectb(x, y, CELL_SIZE, CELL_SIZE, 1)

        for pos, motor in self.motors.items():
            motor.draw(10)
            cx, cy = self.cell_center(*pos)
            pw = f'{motor.power:.0f}'
            pyxel.text(cx-len(pw)*2, cy+GEAR_RADIUS+4, pw, 10)

        for pos, gear in self.gears.items():
            gtype = gear.gear_type
            if gear.flash_timer > 0 and (pyxel.frame_count//2)%2 == 0:
                col = 10
            else:
                col = TYPE_COLORS.get(gtype, 13)
            gear.draw(col)
            if gear.power > 0:
                pw = f'P{gear.power:.1g}'
                cx, cy = gear.x, gear.y
                pyxel.text(cx-len(pw)*2, cy+gear.radius+4, pw, 5)

        for pos, mdata in self.machines.items():
            cx, cy = self.cell_center(*pos)
            active = mdata["active"]
            req_dir = mdata["dir"]
            req_pw = mdata["req_power"]
            recv_pw = mdata["recv_power"]
            is_dual = mdata.get("dual", False)
            col = 11 if active else 8
            pyxel.rect(cx-13, cy-13, 26, 26, 0)
            pyxel.rectb(cx-13, cy-13, 26, 26, col)
            pyxel.rectb(cx-12, cy-12, 24, 24, col)
            if is_dual:
                pyxel.rectb(cx-11, cy-11, 22, 22, col)
            a = math.radians(pyxel.frame_count * 3 * req_dir)
            r = 7
            ax = cx + math.cos(a)*r
            ay = cy + math.sin(a)*r
            pyxel.line(cx, cy, ax, ay, col)
            tip_a1 = a + math.pi*0.75
            tip_a2 = a - math.pi*0.75
            pyxel.line(ax, ay, ax+math.cos(tip_a1)*4, ay+math.sin(tip_a1)*4, col)
            pyxel.line(ax, ay, ax+math.cos(tip_a2)*4, ay+math.sin(tip_a2)*4, col)
            pw_text = f'P{req_pw:.0f}'
            pcol = 11 if recv_pw >= req_pw else 8
            pyxel.text(cx-len(pw_text)*2, cy+14, pw_text, pcol)


# --- サウンド ---

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

# New rules: branch splits power, amp adds +1, reduce subtracts -0.5
STAGES = [
    {
        # S1: Tutorial. Motor p2 -> 3 normal -> Machine needs p2, dir=-1
        # 3 normal (odd) from d1 -> d-1. Power stays 2. OK.
        "name": "STAGE 1",
        "actions": 5,
        "motors": [{"col": 2, "row": 4, "speed": 1.0, "power": 2.0}],
        "machines": [{"col": 6, "row": 4, "dir": -1, "req_power": 2.0}],
        "fixed_gears": [],
        "walls": [],
        "hand": [{"type": GEAR_NORMAL, "teeth": 8, "count": 5}],
    },
    {
        # S2: Power split intro.
        # Motor(2,4) p2 d1. (3,4)N d-1 p2. (4,4)N d1 p2.
        # Split: (4,3)N d-1 p1. (4,5)N d-1 p1.
        # Machine A(5,3) needs d-1, p1. Adjacent (4,3) d-1 OK.
        # Machine B(5,5) needs d-1, p1. Adjacent (4,5) d-1 OK.
        "name": "STAGE 2",
        "actions": 6,
        "motors": [{"col": 2, "row": 4, "speed": 1.0, "power": 2.0}],
        "machines": [
            {"col": 5, "row": 3, "dir": -1, "req_power": 1.0},
            {"col": 5, "row": 5, "dir": -1, "req_power": 1.0},
        ],
        "fixed_gears": [],
        "walls": [],
        "hand": [{"type": GEAR_NORMAL, "teeth": 8, "count": 6}],
    },
    {
        # S3: Amp needed. Motor p1, Machine needs p2.
        # 1 normal + 1 amp: p1 -> N(p1) -> Amp(p1+1=p2). dir: d1->d-1->d1.
        # Machine(4,4) dir=1, p2. 2 gears (even) from d1 = d1. OK.
        "name": "STAGE 3",
        "actions": 5,
        "motors": [{"col": 1, "row": 4, "speed": 1.0, "power": 1.0}],
        "machines": [{"col": 4, "row": 4, "dir": 1, "req_power": 2.0}],
        "fixed_gears": [],
        "walls": [],
        "hand": [
            {"type": GEAR_NORMAL, "teeth": 8, "count": 3},
            {"type": GEAR_AMP, "teeth": 8, "count": 1},
        ],
    },
    {
        # S4: Split + amp. Motor p2 -> branch.
        # Machine A needs p2 (more than split gives).
        # Machine B needs p1 (split is enough).
        # Must amp the A branch after split to recover power.
        # Motor(1,4) p2. (2,4)N p2. (3,4)N p2 -> splits to (3,3)+(3,5).
        # Each gets p1. A branch: (3,3)Amp -> p1+1=p2. Machine A(4,3) gets p2, dir check.
        # B branch: (3,5)N p1. Machine B(4,5) gets p1.
        # Dir: d1->(2,4)d-1->(3,4)d1->split.
        # A: (3,3)Amp d-1 -> Machine A(4,3) needs d-1, p2 OK.
        # B: (3,5)N d-1 -> Machine B(4,5) needs d-1, p1 OK.
        "name": "STAGE 4",
        "actions": 6,
        "motors": [{"col": 1, "row": 4, "speed": 1.0, "power": 2.0}],
        "machines": [
            {"col": 4, "row": 3, "dir": -1, "req_power": 2.0},
            {"col": 4, "row": 5, "dir": -1, "req_power": 1.0},
        ],
        "fixed_gears": [],
        "walls": [],
        "hand": [
            {"type": GEAR_NORMAL, "teeth": 8, "count": 4},
            {"type": GEAR_AMP, "teeth": 8, "count": 1},
        ],
    },
    {
        # S5: Direction puzzle + split.
        # Motor(1,4) p2, d1. Branch at (3,4).
        # Machine A(6,2) needs d1, p1. Machine B(6,6) needs d-1, p1.
        # After (2,4)N d-1, (3,4)N d1. Split -> each p1.
        # A path: (3,3)(3,2)(4,2)(5,2) = 4N. d1*(−1)^4=d1. Machine A d1,p1 OK.
        # B path: (3,5)(3,6)(4,6)(5,6) = 4N. d1*(−1)^4=d1. Machine B needs d-1. FAIL!
        # Fix: B needs 3N+1Same. (3,5)N d-1,(3,6)N d1,(4,6)Same d1,(5,6)N d-1. Machine B d-1 OK.
        # Hand: 7N + 1Same = 8 gears. 2 shared + 4 branch A + 4 branch B = 10 slots.
        # Hmm, too many slots. Let me shorten.
        # Shorter: branch at (3,4), up (3,3)(4,3)(5,3) = 3N d1*(-1)^3=d-1.
        # down (3,5)(4,5)(5,5) = 3N d1*(-1)^3=d-1.
        # Machine A(6,3) needs d1. 3 odd = wrong. Need Same in A path.
        # A: (3,3)Same d1, (4,3)N d-1, (5,3)N d1. Machine A(6,3) d1 p1 OK.
        # B: (3,5)N d-1, (4,5)N d1, (5,5)N d-1. Machine B(6,5) d-1 p1 OK.
        # Hand: 2 shared N + 1S+2N (A) + 3N (B) = 7N + 1S = 8.
        "name": "STAGE 5",
        "actions": 10,
        "motors": [{"col": 1, "row": 4, "speed": 1.0, "power": 2.0}],
        "machines": [
            {"col": 6, "row": 3, "dir": 1, "req_power": 1.0},
            {"col": 6, "row": 5, "dir": -1, "req_power": 1.0},
        ],
        "fixed_gears": [],
        "walls": [],
        "hand": [
            {"type": GEAR_NORMAL, "teeth": 8, "count": 7},
            {"type": GEAR_SAME, "teeth": 8, "count": 1},
        ],
    },
    {
        # S6: Full puzzle. Motor p2 -> 3 machines, different requirements.
        # Motor(1,4) p2,d1. (2,4)N d-1 p2. (3,4)N d1 p2.
        # Split 3 ways from (3,4): up, right, down. Each gets p2/3 = 0.67.
        # Too low! Need amp.
        # Better: split 2 ways first, then split again.
        # (3,4) splits to (3,3) and (3,5). Each gets p1.
        # (3,3) goes to Machine A. (3,5) splits to B and C.
        # A path: (3,3)Amp d-1 p1+1=p2. (4,3)N d1 p2. Machine A(5,3) d1 p2 OK.
        # (3,5)N d-1 p1. Splits at (4,5) to (4,6) and (5,5). Each p0.5.
        # B: (4,6)N d1 p0.5. Needs p1. FAIL. Need amp: (4,6)Amp d1 p0.5+1=1.5>=1 OK.
        # C: (5,5)N d1 p0.5. Needs p1. FAIL.
        # Hmm. Let me redesign.
        # Motor p4 so split gives more power.
        # Motor(1,4) p4,d1. (2,4)N p4. (3,4)N p4 -> split 2 ways.
        # Up: p2. Down: p2.
        # Machine A(5,3) needs d1, p2. Path (3,3)N d-1 p2, (4,3)N d1 p2. OK.
        # (3,5)N d-1 p2 -> splits to (4,5) and (3,6). Each p1.
        # Machine B(5,5) needs d-1, p1. Path (4,5)N d1 p1, (5,5)... wait.
        # Simpler: (3,5) goes right (4,5)N p2, splits to B and C.
        # No wait, (3,5) doesn't split if only 1 downstream.
        # Let me just do: Motor p4 -> 2shared -> split to A and B.
        # A needs p2, B needs p2. Each gets p2 from split.
        # A needs dir=1, B needs dir=-1 -> different parities.
        # A: even path, B: odd path. Use Same gear.
        "name": "STAGE 6",
        "actions": 12,
        "motors": [{"col": 1, "row": 4, "speed": 1.0, "power": 4.0}],
        "machines": [
            {"col": 7, "row": 2, "dir": 1, "req_power": 2.0},
            {"col": 7, "row": 6, "dir": -1, "req_power": 2.0},
        ],
        "fixed_gears": [],
        "walls": [],
        "hand": [
            {"type": GEAR_NORMAL, "teeth": 8, "count": 9},
            {"type": GEAR_SAME, "teeth": 8, "count": 1},
        ],
    },
]


# --- フォント ---

FONT8 = {
    "S": ["  ####  "," #    # "," #      ","  ####  ","      # "," #    # ","  ####  ","        "],
    "T": [" ###### ","   ##   ","   ##   ","   ##   ","   ##   ","   ##   ","   ##   ","        "],
    "A": ["  ####  "," #    # "," #    # "," ###### "," #    # "," #    # "," #    # ","        "],
    "G": ["  ####  "," #    # "," #      "," #  ### "," #    # "," #    # ","  ####  ","        "],
    "E": [" ###### "," #      "," #      "," ####   "," #      "," #      "," ###### ","        "],
    " ": ["        "]*8,
    "0": ["  ####  "," #    # "," #   ## "," #  # # "," # #  # "," ##   # ","  ####  ","        "],
    "1": ["   ##   ","  ###   ","   ##   ","   ##   ","   ##   ","   ##   "," ###### ","        "],
    "2": ["  ####  "," #    # ","      # ","   ###  ","  #     "," #      "," ###### ","        "],
    "3": ["  ####  "," #    # ","      # ","   ###  ","      # "," #    # ","  ####  ","        "],
    "4": [" #    # "," #    # "," #    # "," ###### ","      # ","      # ","      # ","        "],
    "5": [" ###### "," #      "," #      "," #####  ","      # "," #    # ","  ####  ","        "],
    "6": ["  ####  "," #      "," #      "," #####  "," #    # "," #    # ","  ####  ","        "],
}

def draw_text8(x, y, text, col, scale=3):
    cx = x
    for ch in text:
        glyph = FONT8.get(ch)
        if glyph:
            for row in range(8):
                for c in range(8):
                    if glyph[row][c] == "#":
                        pyxel.rect(cx+c*scale, y+row*scale, scale, scale, col)
        cx += 9*scale


# --- フェード ---

FADE_STEPS = [2,3,4,6,8,12,16,24,32,48,64]
FADE_OUT_FRAMES = [5,5,4,4,3,3,2,2,1,1,1]
FADE_IN_FRAMES = [1,1,1,2,2,3,3,4,4,5,5]


# --- アプリ ---

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
            self.grid.add_motor(m["col"], m["row"], m["speed"], m.get("power", 1.0))
        for m in stage["machines"]:
            self.grid.add_machine(m["col"], m["row"], m.get("dir", 1),
                                 m.get("req_power", 1.0), m.get("dual", False))
        for w in stage.get("walls", []):
            self.grid.add_wall(w["col"], w["row"])
        for fg in stage.get("fixed_gears", []):
            self.grid.add_fixed_gear(fg["col"], fg["row"],
                                     fg.get("type", GEAR_FIXED), fg.get("teeth", GEAR_TEETH))
        self.grid.propagate_power()

        self.hand = []
        for hd in stage["hand"]:
            self.hand.append({
                "type": hd.get("type", GEAR_NORMAL),
                "teeth": hd["teeth"], "count": hd["count"],
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
        if h["count"] <= 0:
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

    def try_remove(self, col, row):
        pos, gear = self.grid.find_gear_at(col, row)
        if gear is None or pos not in self.grid.gears:
            return
        if gear.gear_type == GEAR_FIXED:
            return
        removed = self.grid.remove_gear(col, row)
        if removed:
            gtype = removed.gear_type
            for h in self.hand:
                if h.get("type") == gtype and h["teeth"] == removed.teeth:
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
            accum, step_idx = 0, 0
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
            self.fade_step_idx = min(step_idx, len(FADE_STEPS)-1)
            return

        if self.intro_timer > 0:
            self.intro_timer -= 1
            return

        if self.cleared:
            self.clear_timer += 1
            self.grid.update()
            if self.clear_timer > 120 and pyxel.btnp(pyxel.KEY_RETURN):
                if self.stage_idx + 1 < len(STAGES):
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
            if my >= HAND_Y - 4:
                hx = 70
                for i, h in enumerate(self.hand):
                    if h["count"] > 0 and hx-14 <= mx <= hx+14:
                        self.selected_hand = i if self.selected_hand != i else -1
                        return
                    hx += 60
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
            si = self.fade_step_idx
            bs = FADE_STEPS[si] if self.fade_state == 1 else FADE_STEPS[len(FADE_STEPS)-1-si]
            for y in range(0, 384, bs):
                for x in range(0, 512, bs):
                    col = pyxel.pget(min(x+bs//2, 511), min(y+bs//2, 383))
                    pyxel.rect(x, y, bs, bs, col)

    def draw_title_gear(self, cx, cy, teeth, radius, col, speed=0.5):
        gear = Gear(cx, cy, teeth, radius)
        gear.angle = pyxel.frame_count * speed
        gear.draw(col)

    def draw_scene(self):
        if self.on_title:
            self.draw_title_gear(50, 340, 20, 80, 1, -0.3)
            self.draw_title_gear(440, 90, 12, 24, 1, 0.5)
            self.draw_title_gear(430, 300, 16, 32, 1, -0.4)
            self.draw_title_gear(60, 70, 6, 12, 1, 0.8)

            scale = 4
            cw = 13 * scale
            total_w = cw * 4
            tx = (512 - total_w) // 2
            ty = 130
            TITLE_FONT = {
                "C": ["  ########  "," ##      ## ","##          ","##          ","##          ","##        ##"," ##      ## ","  ########  "],
                "G": ["  ########  "," ##      ## ","##          ","##    ######","##       ## ","##        ##"," ##      ## ","  ########  "],
                "S": ["  ########  "," ##      ## ","##          ","  ######    ","        ### ","##        ##"," ##      ## ","  ########  "],
            }
            for ci, ch in enumerate("C GS"):
                if ch == " ":
                    gear = Gear(tx + cw + 6*scale, ty + 4*scale, 10, 18)
                    gear.angle = pyxel.frame_count * 0.8
                    gear.draw(6)
                elif ch in TITLE_FONT:
                    glyph = TITLE_FONT[ch]
                    for row in range(len(glyph)):
                        for c in range(len(glyph[row])):
                            if glyph[row][c] == "#":
                                pyxel.rect(tx + ci*cw + c*scale, ty + row*scale, scale, scale, 13)

            pyxel.text((512-21*4)//2, ty + 14*scale, "Fill the missing cog.", 5)
            if (pyxel.frame_count//20)%2:
                pyxel.text((512-20*4)//2, 300, "PRESS ENTER TO START", 7)
            return

        stage = STAGES[self.stage_idx]

        if self.all_clear:
            pyxel.text((512-17*4)//2, 170, "ALL STAGES CLEAR!", 10)
            pyxel.text((512-22*4)//2, 186, "THANK YOU FOR PLAYING!", 7)
            return

        if self.intro_timer > 0:
            name = stage["name"]
            col = 10 if (self.intro_timer//4)%2 == 0 else 7
            draw_text8((512-len(name)*27)//2, 155, name, col, 3)
            pyxel.text((512-12*4)//2, 195, "GET READY...", 5)
            return

        pyxel.rect(0, 0, 512, GRID_Y - 1, 1)
        pyxel.text(4, 6, "COGS", 7)
        pyxel.text(40, 6, stage["name"], 5)
        act_col = 8 if self.actions_left <= 1 else 7
        remaining = sum(h["count"] for h in self.hand)
        pyxel.text(300, 6, f"GEARS:{remaining}", 7)
        pyxel.text(380, 6, f"ACTIONS:{self.actions_left}", act_col)
        if not self.cleared:
            pyxel.text(200, 6, "L:PLACE R:REMOVE", 5)

        self.grid.draw()

        if self.selected_hand >= 0 and not self.cleared:
            mx, my = pyxel.mouse_x, pyxel.mouse_y
            col, row = self.grid.pixel_to_cell(mx, my)
            h = self.hand[self.selected_hand]
            gtype = h.get("type", GEAR_NORMAL)
            if col is not None:
                can = self.grid.can_place_large(col, row) if gtype == GEAR_LARGE else self.grid.can_place(col, row)
                if can and (pyxel.frame_count//10)%3 != 0:
                    cx, cy = self.grid.cell_center(col, row)
                    r = GEAR_RADIUS+10 if gtype == GEAR_LARGE else GEAR_RADIUS
                    ghost = Gear(cx, cy, h["teeth"], r)
                    ghost.draw(1)

        pyxel.rect(0, HAND_Y - 4, 512, 384 - HAND_Y + 4, 1)
        pyxel.text(4, HAND_Y, "HandGear:", 7)
        hx = 70
        for i, h in enumerate(self.hand):
            if h["count"] > 0:
                gtype = h.get("type", GEAR_NORMAL)
                col = 10 if i == self.selected_hand else TYPE_COLORS.get(gtype, 7)
                r = 9 if gtype == GEAR_LARGE else 8
                gear = Gear(hx, HAND_Y + 16, h["teeth"], r)
                gear.draw(col)
                label = TYPE_LABELS.get(gtype, "")
                pyxel.text(hx - 10, HAND_Y + 29, f'{label}{h["teeth"]}Tx{h["count"]}', 7)
            hx += 60

        if self.message_timer > 0:
            pyxel.text((512-len(self.message)*4)//2, HAND_Y - 12, self.message, 8)

        if self.cleared:
            pyxel.text((512-12*4)//2, 160, "STAGE CLEAR!", 10)
            if self.clear_timer > 120:
                msg = "PRESS ENTER FOR NEXT" if self.stage_idx+1 < len(STAGES) else "PRESS ENTER TO FINISH"
                pyxel.text((512-len(msg)*4)//2, 176, msg, 7)
        elif self.game_over:
            bw, bh = 180, 45
            bx, by = (512-bw)//2, 150
            pyxel.rect(bx, by, bw, bh, 0)
            pyxel.rectb(bx, by, bw, bh, 8)
            pyxel.text((512-9*4)//2, by+10, "GAME OVER", 8)
            pyxel.text((512-20*4)//2, by+26, "PRESS ENTER TO RETRY", 7)


App()
