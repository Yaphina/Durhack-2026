import math
import random
import dearpygui.dearpygui as dpg

GRID = 4
NUM = GRID * GRID
VIEW_W, VIEW_H = 1300, 800

# ---------------- layout ----------------
BOX = (20, 50, 820, 770)            # ScatterBox: x0, y0, x1, y1 (pieces start inside this)
BOARD_ORIGIN = (860, 120)           # top-left of the finished picture on the target grid
BOARD_MAX = (420, 600)              # max size of the finished picture on screen
ARENA = (0, 0, VIEW_W - 16, VIEW_H - 16)
ROAM_WHOLE_ARENA = True             # offline agents may leave the box (needed to reach docked pieces)

# ---------------- behaviour ----------------
SPEED = 2.0            # chase speed, px/frame
HOME_SPEED = 4.0       # speed when flying to the slot the hub gave us
REPEL_FRAMES = 60
REPEL_SPEED = 3.0
CHASE_LIMIT = 900
PASS_CHANCE = 0.6
TOUCH_MARGIN = 6
LINK_REROLL_FRAMES = 30

# Top-left of each piece PNG in the finished picture (original PNG pixels), from calibrate.py
FINAL = {
    0:  (0,    0),    1:  (119,  -2),   2:  (394,  -3),   3:  (591,  -5),
    4:  (2,    197),  5:  (120,  258),  6:  (394,  195),  7:  (527,  225),
    8:  (0,    451),  9:  (200,  468),  10: (396,  448),  11: (530,  462),
    12: (-2,   769),  13: (120,  712),  14: (314,  769),  15: (593,  705),
}

# ---------------- textures and scale ----------------
dpg.create_context()
dpg.create_viewport(title="Decentralized Puzzle", width=VIEW_W, height=VIEW_H)

TEX_W, TEX_H = {}, {}
with dpg.texture_registry():
    for n in range(NUM):
        w, h, ch, data = dpg.load_image(f"mona lisa 4x4 puzzle/piece{n}.png")
        dpg.add_static_texture(width=w, height=h, default_value=data, tag=f"tex{n}")
        TEX_W[n], TEX_H[n] = w, h

min_x = min(FINAL[n][0] for n in range(NUM))
min_y = min(FINAL[n][1] for n in range(NUM))
pic_w = max(FINAL[n][0] + TEX_W[n] for n in range(NUM)) - min_x
pic_h = max(FINAL[n][1] + TEX_H[n] for n in range(NUM)) - min_y

cell_w = (BOX[2] - BOX[0]) / GRID
cell_h = (BOX[3] - BOX[1]) / GRID
S = min(1.0,
        BOARD_MAX[0] / pic_w, BOARD_MAX[1] / pic_h,
        0.95 * cell_w / max(TEX_W.values()),
        0.95 * cell_h / max(TEX_H.values()))

PW = {n: TEX_W[n] * S for n in range(NUM)}
PH = {n: TEX_H[n] * S for n in range(NUM)}
# offset of each piece inside the finished picture (>= 0)
FIN = {n: ((FINAL[n][0] - min_x) * S, (FINAL[n][1] - min_y) * S) for n in range(NUM)}

# ---------------- drawing: box, board, pieces ----------------
with dpg.window(tag="main", no_scrollbar=True, no_title_bar=True, no_move=True, no_resize=True):
    with dpg.drawlist(width=VIEW_W, height=VIEW_H, tag="canvas"):
        # scatter box
        dpg.draw_rectangle((BOX[0], BOX[1]), (BOX[2], BOX[3]), color=(120, 120, 120, 255), thickness=2)
        dpg.draw_text((BOX[0], BOX[1] - 24), "ScatterBox", size=18)
        # target grid
        dpg.draw_text((BOARD_ORIGIN[0], BOARD_ORIGIN[1] - 24), "Target grid", size=18)
        dpg.draw_rectangle(BOARD_ORIGIN,
                           (BOARD_ORIGIN[0] + pic_w * S, BOARD_ORIGIN[1] + pic_h * S),
                           color=(120, 120, 120, 255), thickness=2)
        for n in range(NUM):
            sx, sy = BOARD_ORIGIN[0] + FIN[n][0], BOARD_ORIGIN[1] + FIN[n][1]
            dpg.draw_rectangle((sx, sy), (sx + PW[n], sy + PH[n]), color=(70, 70, 70, 255))
            dpg.draw_text((sx + 4, sy + 2), str(n), size=14, color=(90, 90, 90, 255))
        # pieces (drawn last so they sit on top)
        for n in range(NUM):
            dpg.draw_image(f"tex{n}", (0, 0), (PW[n], PH[n]), tag=f"img{n}")

# ---------------- piece geometry ----------------
P = {n: [0.0, 0.0] for n in range(NUM)}      # top-left of each piece on screen


def center(n):
    return P[n][0] + PW[n] / 2, P[n][1] + PH[n] / 2


def origin(n):
    """Where the picture's top-left would be if piece n were correctly placed.
    Two correctly related pieces have the same origin."""
    return P[n][0] - FIN[n][0], P[n][1] - FIN[n][1]


def touching(a, b):
    m = TOUCH_MARGIN
    return (P[a][0] < P[b][0] + PW[b] + m and P[b][0] < P[a][0] + PW[a] + m and
            P[a][1] < P[b][1] + PH[b] + m and P[b][1] < P[a][1] + PH[a] + m)


def edges_match(a, b):
    """Stand-in for 'the two edges fit' - replace with a real edge comparison."""
    r1, c1 = divmod(a, GRID)
    r2, c2 = divmod(b, GRID)
    return abs(r1 - r2) + abs(c1 - c2) == 1


def roam_rect():
    return ARENA if ROAM_WHOLE_ARENA else BOX


# ---------------- agents (one per piece or merged group) ----------------
agents = []
agent_of = {}


class Agent:
    def __init__(self, piece):
        self.members = [piece]
        self.settled = False
        self.target = None
        self.repel_left = 0
        self.repel_vel = (0.0, 0.0)
        self.chase_time = 0
        self.random_next = False
        self.failed = set()            # this agent's OWN memory of rejected pairs
        self.pass_roll = {}            # other agent -> does the smaller one pass through?
        self.link_ok = False
        self.link_timer = 0

    # ----- local sensing: only what I am touching -----
    def sense(self):
        out = []
        for a in self.members:
            for b in range(NUM):
                other = agent_of[b]
                if other is not self and touching(a, b):
                    out.append((a, b, other))
        return out

    # ----- hub link (unreliable) -----
    def update_link(self):
        self.link_timer -= 1
        if self.link_timer <= 0:
            self.link_ok = random.random() * 100 < dpg.get_value("quality")
            self.link_timer = LINK_REROLL_FRAMES

    # ----- movement helper -----
    def shift(self, dx, dy, clamp=False):
        if clamp:
            x0, y0, x1, y1 = roam_rect()
            lo_x = min(P[m][0] for m in self.members)
            lo_y = min(P[m][1] for m in self.members)
            hi_x = max(P[m][0] + PW[m] for m in self.members)
            hi_y = max(P[m][1] + PH[m] for m in self.members)
            dx = max(x0 - lo_x, min(dx, x1 - hi_x))
            dy = max(y0 - lo_y, min(dy, y1 - hi_y))
        for m in self.members:
            P[m][0] += dx
            P[m][1] += dy
        return dx, dy

    # ----- one tick: uses only my state + my contacts + (maybe) the hub -----
    def step(self):
        self.update_link()
        contacts = self.sense()

        # correct matches always win
        for a, b, other in contacts:
            if edges_match(a, b):
                merge(self, other, a, b)
                return

        if self.settled:
            return

        if self.link_ok:                     # hub reachable: ask it for my slot
            self.repel_left = 0
            self.home()
            return

        # ---- hub unreachable: peer-to-peer ----
        touched = {id(o) for _, _, o in contacts}
        self.pass_roll = {k: v for k, v in self.pass_roll.items() if k in touched}

        if self.repel_left > 0:
            self.repel_move()
            return

        for a, b, other in contacts:         # only back off from the group I'm chasing
            if self.target is not None and agent_of[self.target] is other:
                if len(other.members) != len(self.members):
                    if id(other) not in self.pass_roll:
                        self.pass_roll[id(other)] = random.random() < PASS_CHANCE
                    if self.pass_roll[id(other)]:
                        continue             # smaller one slips through
                self.bump(a, b, other)
                return

        self.chase()

    # ----- behaviours -----
    def home(self):
        anchor = self.members[0]
        ox, oy = origin(anchor)
        dx, dy = BOARD_ORIGIN[0] - ox, BOARD_ORIGIN[1] - oy
        d = math.hypot(dx, dy)
        if d <= HOME_SPEED:
            self.shift(dx, dy)
            self.settled = True
        else:
            self.shift(dx / d * HOME_SPEED, dy / d * HOME_SPEED)

    def bump(self, a, b, other):
        ax, ay = center(a)
        bx, by = center(b)
        dx, dy = ax - bx, ay - by
        d = math.hypot(dx, dy)
        if d == 0:
            dx, dy, d = random.choice([-1, 1]), random.choice([-1, 1]), 1.414
        self.repel_vel = (dx / d * REPEL_SPEED, dy / d * REPEL_SPEED)
        self.repel_left = REPEL_FRAMES
        for m in self.members:
            for p in other.members:
                self.failed.add(frozenset((m, p)))
        self.target = None
        self.random_next = True

    def repel_move(self):
        vx, vy = self.repel_vel
        adx, ady = self.shift(vx, vy, clamp=True)
        if abs(adx - vx) > 0.01:
            vx = -vx
        if abs(ady - vy) > 0.01:
            vy = -vy
        self.repel_vel = (vx, vy)
        self.repel_left -= 1

    def pick_target(self):
        def candidates():
            return [p for p in range(NUM)
                    if agent_of[p] is not self
                    and not any(frozenset((m, p)) in self.failed for m in self.members)]
        c = candidates()
        if not c:
            self.failed.clear()
            c = candidates()
        if self.random_next:
            return random.choice(c)
        return min(c, key=lambda p: min(math.hypot(center(p)[0] - center(m)[0],
                                                   center(p)[1] - center(m)[1])
                                        for m in self.members))

    def chase(self):
        self.chase_time += 1
        if self.chase_time > CHASE_LIMIT and self.target is not None:
            for m in self.members:
                self.failed.add(frozenset((m, self.target)))
            self.target = None
            self.random_next = True
        if self.target is None or agent_of[self.target] is self:
            self.target = self.pick_target()
            self.random_next = False
            self.chase_time = 0

        tx, ty = center(self.target)
        anchor = min(self.members,
                     key=lambda m: math.hypot(center(m)[0] - tx, center(m)[1] - ty))
        ax, ay = center(anchor)
        dx, dy = tx - ax, ty - ay
        d = math.hypot(dx, dy)
        if d > 0:
            step = min(SPEED, d)
            self.shift(dx / d * step, dy / d * step, clamp=True)


def merge(x, y, a, b):
    """a (in x) and b (in y) fit. The settled / bigger group stays put; the other snaps to it."""
    keep, give, ka, ga = x, y, a, b
    if (y.settled and not x.settled) or (x.settled == y.settled and len(y.members) > len(x.members)):
        keep, give, ka, ga = y, x, b, a
    if not give.settled:
        ok, og = origin(ka), origin(ga)
        give.shift(ok[0] - og[0], ok[1] - og[1])
    for m in give.members:
        agent_of[m] = keep
    keep.members += give.members
    keep.failed |= give.failed
    keep.settled = keep.settled or give.settled
    keep.target = None
    keep.chase_time = 0
    keep.random_next = False
    keep.repel_left = 0
    agents.remove(give)
    print("merged", a, b, "-> group size", len(keep.members), "(settled)" if keep.settled else "")


# ---------------- reset / scatter ----------------
def reset(*_):
    agents.clear()
    slots = [(BOX[0] + c * cell_w, BOX[1] + r * cell_h) for r in range(GRID) for c in range(GRID)]
    random.shuffle(slots)
    for n in range(NUM):
        sx, sy = slots[n]
        P[n][0] = sx + random.uniform(0, max(0, cell_w - PW[n]))
        P[n][1] = sy + random.uniform(0, max(0, cell_h - PH[n]))
        ag = Agent(n)
        agents.append(ag)
        agent_of[n] = ag


def sync():
    for n in range(NUM):
        dpg.configure_item(f"img{n}", pmin=(P[n][0], P[n][1]), pmax=(P[n][0] + PW[n], P[n][1] + PH[n]))


# ---------------- controls ----------------
with dpg.window(label="Controls", pos=(860, 10), width=420, height=95, no_close=True):
    dpg.add_slider_int(label="Hub link quality %", tag="quality", default_value=100, min_value=0, max_value=100, width=200)
    dpg.add_button(label="Scatter again", callback=reset)
    dpg.add_text("", tag="status")

reset()
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("main", True)

while dpg.is_dearpygui_running():
    for ag in list(agents):
        if ag in agents:
            ag.step()
    sync()
    solved = len(agents) == 1
    dpg.set_value("status", f"groups: {len(agents)}   settled pieces: "
                            f"{sum(len(a.members) for a in agents if a.settled)}/{NUM}"
                            + ("   SOLVED" if solved else ""))
    dpg.render_dearpygui_frame()

dpg.destroy_context()
