import colorsys
import math
import random
from collections import deque

import dearpygui.dearpygui as dpg

GRID = 4
NUM = GRID * GRID
VIEW_W, VIEW_H = 1440, 860

# ---------------- layout ----------------
BOX = (20, 50, 760, 770)            # ScatterBox: x0, y0, x1, y1
BOARD_ORIGIN = (800, 50)            # top-left of the finished picture on the target grid
BOARD_MAX = (420, 490)              # max on-screen size of the finished picture

# ---------------- behaviour ----------------
MAX_GROUP = 4          # a group stops growing at this size and docks on the board
SPEED = 1.0            # chase speed (px per tick)
HOME_SPEED = 2.5       # speed when flying to the board (hub slot or full-group dock)
REPEL_SPEED = 1.2
REPEL_FRAMES = 90
CHASE_LIMIT = 1500     # ticks before giving up on a target
PASS_CHANCE = 0.6
TOUCH_MARGIN = 6
LINK_REROLL_FRAMES = 30
EASE = 0.10            # how fast merged pieces glide into alignment

# live values, read from the sliders every frame
QUALITY = 0
MERGE_FRAMES = 75      # how long two matching groups must stay in contact before they merge
PATIENCE = 300         # ticks (60 per second at speed 1) a stuck group waits, then docks on the board anyway
SIM_SPEED = 1.0
SHOW_OVERLAY = True
PAUSED = False

# Top-left of each piece PNG in the finished picture (original PNG pixels), from calibrate.py
FINAL = {
    0:  (0,    0),    1:  (119,  -2),   2:  (394,  -3),   3:  (591,  -5),
    4:  (2,    197),  5:  (120,  258),  6:  (394,  195),  7:  (527,  225),
    8:  (0,    451),  9:  (200,  468),  10: (396,  448),  11: (530,  462),
    12: (-2,   769),  13: (120,  712),  14: (314,  769),  15: (593,  705),
}

GREEN = (80, 220, 120, 255)
GOLD = (255, 200, 60, 255)
RED = (235, 90, 90, 255)
WHITE = (255, 255, 255, 255)

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
FIN = {n: ((FINAL[n][0] - min_x) * S, (FINAL[n][1] - min_y) * S) for n in range(NUM)}

# ---------------- theme ----------------
with dpg.theme() as THEME:
    with dpg.theme_component(dpg.mvAll):
        core = dpg.mvThemeCat_Core
        dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 8, category=core)
        dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 6, category=core)
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5, category=core)
        dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 5, category=core)
        dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 12, 10, category=core)
        dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 4, category=core)
        dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 8, category=core)
        dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (18, 20, 26), category=core)
        dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (26, 29, 37), category=core)
        dpg.add_theme_color(dpg.mvThemeCol_TitleBg, (30, 34, 44), category=core)
        dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (40, 46, 60), category=core)
        dpg.add_theme_color(dpg.mvThemeCol_Border, (55, 60, 75), category=core)
        dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (38, 42, 54), category=core)
        dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (50, 56, 72), category=core)
        dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (60, 68, 88), category=core)
        dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, (90, 160, 255), category=core)
        dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, (130, 190, 255), category=core)
        dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (90, 160, 255), category=core)
        dpg.add_theme_color(dpg.mvThemeCol_Button, (52, 96, 170), category=core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (70, 120, 205), category=core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (90, 140, 225), category=core)
dpg.bind_theme(THEME)

# ---------------- drawing: box, board, pieces, overlay ----------------
with dpg.window(tag="main", no_scrollbar=True, no_title_bar=True, no_move=True, no_resize=True):
    with dpg.drawlist(width=VIEW_W, height=VIEW_H, tag="canvas"):
        dpg.draw_rectangle((BOX[0], BOX[1]), (BOX[2], BOX[3]), color=(70, 78, 100, 255),
                           fill=(26, 29, 37, 255), thickness=2, rounding=6)
        dpg.draw_text((BOX[0], BOX[1] - 26), "ScatterBox", size=18, color=(200, 206, 220, 255))
        dpg.draw_text((BOARD_ORIGIN[0], BOARD_ORIGIN[1] - 26), "Target grid", size=18, color=(200, 206, 220, 255))
        dpg.draw_rectangle((BOARD_ORIGIN[0] - 6, BOARD_ORIGIN[1] - 6),
                           (BOARD_ORIGIN[0] + pic_w * S + 6, BOARD_ORIGIN[1] + pic_h * S + 6),
                           color=(70, 78, 100, 255), fill=(22, 24, 31, 255), thickness=2, rounding=6)
        for n in range(NUM):   # faint ghost of where each piece belongs
            sx, sy = BOARD_ORIGIN[0] + FIN[n][0], BOARD_ORIGIN[1] + FIN[n][1]
            dpg.draw_image(f"tex{n}", (sx, sy), (sx + PW[n], sy + PH[n]), color=(255, 255, 255, 40))
            dpg.draw_rectangle((sx, sy), (sx + PW[n], sy + PH[n]), color=(60, 66, 84, 255))
        for n in range(NUM):
            dpg.draw_image(f"tex{n}", (0, 0), (PW[n], PH[n]), tag=f"img{n}")
        for n in range(NUM):
            dpg.draw_rectangle((0, 0), (1, 1), color=WHITE, thickness=2, tag=f"box{n}")
        for n in range(NUM):
            dpg.draw_line((0, 0), (1, 1), color=WHITE, thickness=2, tag=f"ln{n}", show=False)
        for n in range(NUM):
            dpg.draw_text((0, 0), " ", size=15, color=WHITE, tag=f"lbl{n}", show=False)

# ---------------- piece geometry ----------------
P = {n: [0.0, 0.0] for n in range(NUM)}      # top-left of each piece on screen


def center(n):
    return P[n][0] + PW[n] / 2, P[n][1] + PH[n] / 2


def origin(n):
    """Where the picture's top-left would be if piece n were correctly placed."""
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


def group_color(gid):
    r, g, b = colorsys.hsv_to_rgb((gid * 0.618) % 1.0, 0.6, 1.0)
    return (int(r * 255), int(g * 255), int(b * 255), 255)


# ---------------- event log ----------------
tick = 0
log_lines = deque(maxlen=11)
log_dirty = True


def log(msg):
    global log_dirty
    log_lines.append(f"[{tick // 60:3d}s] {msg}")
    log_dirty = True


# ---------------- agents (one per piece or merged group) ----------------
agents = []
agent_of = {}
next_gid = 0


def can_merge(x, y):
    return (not x.settled and not y.settled and
            len(x.members) + len(y.members) <= MAX_GROUP)


class Agent:
    def __init__(self, piece):
        global next_gid
        self.gid = next_gid
        next_gid += 1
        self.members = [piece]
        self.ref = piece               # the member whose position is authoritative
        self.settled = False
        self.parked = False            # given up: left behind in the box
        self.target = None
        self.repel_left = 0
        self.repel_vel = (0.0, 0.0)
        self.chase_time = 0
        self.random_next = False
        self.failed = set()            # this agent's OWN memory of rejected pairs
        self.cycles = 0
        self.wait = 0                  # how long I have been waiting with nobody to chase
        self.force_dock = False
        self.pass_roll = {}
        self.hold = {}                 # (my piece, their piece) -> ticks in contact
        self.line = None
        self.state = "idle"
        self.link_ok = False
        self.link_timer = 0

    # ----- appearance -----
    def color(self):
        if self.settled:
            return GREEN
        if self.parked:
            return RED
        if len(self.members) >= MAX_GROUP:
            return GOLD
        return group_color(self.gid)

    def label(self):
        pieces = " ".join(str(m) for m in sorted(self.members))
        return f"[{pieces}] {self.state}"

    # ----- local sensing: only what I am touching -----
    def sense(self):
        out = []
        for a in self.members:
            for b in range(NUM):
                other = agent_of[b]
                if other is not self and touching(a, b):
                    out.append((a, b, other))
        return out

    def update_link(self):
        self.link_timer -= 1
        if self.link_timer <= 0:
            self.link_ok = random.random() * 100 < QUALITY
            self.link_timer = LINK_REROLL_FRAMES

    def shift(self, dx, dy, clamp=False):
        if clamp:
            x0, y0, x1, y1 = BOX
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

    def ease(self):
        """After a merge the pieces glide into exact alignment instead of jumping."""
        rx, ry = origin(self.ref)
        for m in self.members:
            if m == self.ref:
                continue
            tx, ty = rx + FIN[m][0], ry + FIN[m][1]
            dx, dy = tx - P[m][0], ty - P[m][1]
            if abs(dx) + abs(dy) < 0.3:
                P[m][0], P[m][1] = tx, ty
            else:
                P[m][0] += dx * EASE
                P[m][1] += dy * EASE

    def outside_vec(self):
        x0, y0, x1, y1 = BOX
        lo_x = min(P[m][0] for m in self.members)
        lo_y = min(P[m][1] for m in self.members)
        hi_x = max(P[m][0] + PW[m] for m in self.members)
        hi_y = max(P[m][1] + PH[m] for m in self.members)
        dx = x0 - lo_x if lo_x < x0 else (x1 - hi_x if hi_x > x1 else 0)
        dy = y0 - lo_y if lo_y < y0 else (y1 - hi_y if hi_y > y1 else 0)
        return dx, dy

    # ----- one tick: only my state, my contacts and (maybe) the hub -----
    def step(self):
        self.line = None
        self.ease()
        self.update_link()
        contacts = self.sense()

        # 1. correct match + room in the group: stay in contact for a while, then merge
        active, linking = set(), False
        for a, b, other in contacts:
            if edges_match(a, b) and can_merge(self, other):
                key = (a, b)
                active.add(key)
                self.hold[key] = self.hold.get(key, 0) + 1
                if self.hold[key] >= MERGE_FRAMES:
                    merge(self, other, a, b)
                    return
                linking = True
                self.state = f"linking {int(100 * self.hold[key] / MERGE_FRAMES)}%"
                self.line = (a, b, WHITE)
        self.hold = {k: v for k, v in self.hold.items() if k in active}
        if linking:
            return

        # 2. already on the board
        if self.settled:
            self.state = "on board"
            return

        # 3. a full group knows its own place in the picture and docks itself (no hub needed)
        if len(self.members) >= MAX_GROUP or self.force_dock:
            self.state = "going to board"
            self.home()
            return

        # 4. hub reachable: ask it for my slot
        if self.link_ok:
            self.parked = False
            self.wait = 0
            self.repel_left = 0
            self.state = "hub: going to slot"
            self.home()
            return

        # 5. hub unreachable: peer to peer
        touched = {id(o) for _, _, o in contacts}
        self.pass_roll = {k: v for k, v in self.pass_roll.items() if k in touched}

        vx, vy = self.outside_vec()
        if abs(vx) + abs(vy) > 0.5:          # flew out of the box when the link dropped
            d = math.hypot(vx, vy)
            step = min(SPEED * 2, d)
            self.shift(vx / d * step, vy / d * step)
            self.state = "back into box"
            return

        if self.parked:
            self.state = "left behind"
            return

        if self.repel_left > 0:
            self.state = "backing off"
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
        ox, oy = origin(self.ref)
        dx, dy = BOARD_ORIGIN[0] - ox, BOARD_ORIGIN[1] - oy
        d = math.hypot(dx, dy)
        if d <= HOME_SPEED:
            for m in self.members:
                P[m][0] = BOARD_ORIGIN[0] + FIN[m][0]
                P[m][1] = BOARD_ORIGIN[1] + FIN[m][1]
            self.settled = True
            log(f"pieces {sorted(self.members)} placed on the board")
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
            out = []
            for p in range(NUM):
                o = agent_of[p]
                if o is self or o.settled or len(o.members) + len(self.members) > MAX_GROUP:
                    continue
                if any(frozenset((m, p)) in self.failed for m in self.members):
                    continue
                out.append(p)
            return out
        c = candidates()
        if not c and self.failed and self.cycles < 1:
            self.cycles += 1                 # tried everyone once: forget and try once more
            self.failed.clear()
            c = candidates()
        if not c:
            return None
        if self.random_next:
            return random.choice(c)
        return min(c, key=lambda p: min(math.hypot(center(p)[0] - center(m)[0],
                                                   center(p)[1] - center(m)[1])
                                        for m in self.members))

    def chase(self):
        if self.target is not None:
            o = agent_of[self.target]
            if o is self or o.settled or len(o.members) + len(self.members) > MAX_GROUP:
                self.target = None
        self.chase_time += 1
        if self.chase_time > CHASE_LIMIT and self.target is not None:
            for m in self.members:
                self.failed.add(frozenset((m, self.target)))
            self.target = None
            self.random_next = True
        if self.target is None:
            self.target = self.pick_target()
            self.random_next = False
            self.chase_time = 0
        if self.target is None:
            # nobody I can chase right now: stay put and let others come to me
            self.wait += 1
            self.state = f"waiting {min(100, int(100 * self.wait / PATIENCE))}%"
            if self.wait >= PATIENCE:
                self.force_dock = True      # nobody can join me: go to my own place in the picture
                log(f"pieces {sorted(self.members)} cannot grow, going to the board")
            return
        self.wait = 0

        tx, ty = center(self.target)
        anchor = min(self.members,
                     key=lambda m: math.hypot(center(m)[0] - tx, center(m)[1] - ty))
        ax, ay = center(anchor)
        dx, dy = tx - ax, ty - ay
        d = math.hypot(dx, dy)
        self.state = f"chasing piece {self.target}"
        self.line = (anchor, self.target, self.color())
        if d > 0:
            step = min(SPEED, d)
            self.shift(dx / d * step, dy / d * step, clamp=True)


def merge(x, y, a, b):
    """a (in x) and b (in y) fit. The bigger group keeps going; the other joins and glides into place."""
    keep, give = (x, y) if len(x.members) >= len(y.members) else (y, x)
    for m in give.members:
        agent_of[m] = keep
    keep.members += give.members
    keep.failed |= give.failed
    keep.hold = {}
    keep.target = None
    keep.chase_time = 0
    keep.random_next = False
    keep.repel_left = 0
    keep.parked = False
    keep.cycles = 0
    keep.wait = 0
    agents.remove(give)
    log(f"pieces {a} and {b} fit: group is now {sorted(keep.members)}")


# ---------------- reset / sync / overlay ----------------
def reset(*_):
    global next_gid, tick, log_dirty
    agents.clear()
    log_lines.clear()
    next_gid = 0
    tick = 0
    slots = [(BOX[0] + c * cell_w, BOX[1] + r * cell_h) for r in range(GRID) for c in range(GRID)]
    random.shuffle(slots)
    for n in range(NUM):
        sx, sy = slots[n]
        P[n][0] = sx + random.uniform(0, max(0, cell_w - PW[n]))
        P[n][1] = sy + random.uniform(0, max(0, cell_h - PH[n]))
        ag = Agent(n)
        agents.append(ag)
        agent_of[n] = ag
    log("pieces scattered")


def toggle_pause(*_):
    global PAUSED
    PAUSED = not PAUSED
    dpg.set_item_label("pause_btn", "Resume" if PAUSED else "Pause")


def sync():
    for n in range(NUM):
        dpg.configure_item(f"img{n}", pmin=(P[n][0], P[n][1]), pmax=(P[n][0] + PW[n], P[n][1] + PH[n]))


def update_overlay():
    leads = {ag.members[0]: ag for ag in agents}
    for n in range(NUM):
        if not SHOW_OVERLAY:
            dpg.configure_item(f"box{n}", show=False)
            dpg.configure_item(f"ln{n}", show=False)
            dpg.configure_item(f"lbl{n}", show=False)
            continue
        ag = agent_of[n]
        if ag.settled:                       # on the board: drop the overlay
            dpg.configure_item(f"box{n}", show=False)
            dpg.configure_item(f"ln{n}", show=False)
            dpg.configure_item(f"lbl{n}", show=False)
            continue
        dpg.configure_item(f"box{n}", pmin=(P[n][0], P[n][1]), pmax=(P[n][0] + PW[n], P[n][1] + PH[n]),
                           color=ag.color(), thickness=3 if ag.hold else 2, show=True)
        if n in leads and not ag.settled:
            dpg.configure_item(f"lbl{n}", pos=(P[n][0], max(0, P[n][1] - 18)), text=ag.label(),
                               color=ag.color(), show=True)
        else:
            dpg.configure_item(f"lbl{n}", show=False)
        if n in leads and ag.line:
            p, q, col = ag.line
            dpg.configure_item(f"ln{n}", p1=center(p), p2=center(q), color=col, show=True)
        else:
            dpg.configure_item(f"ln{n}", show=False)


finished_logged = False


def update_status():
    global finished_logged, log_dirty
    on_board = sum(len(a.members) for a in agents if a.settled)
    waiting = sum(len(a.members) for a in agents if a.wait > 0 and not a.settled)
    finished = all(a.settled for a in agents)
    dpg.set_value("st_groups", f"Groups: {len(agents)}")
    dpg.set_value("st_board", f"On board: {on_board}/{NUM}")
    dpg.set_value("st_left", f"Waiting: {waiting}")
    if PAUSED:
        dpg.set_value("st_state", "Paused")
    elif finished:
        dpg.set_value("st_state", "Finished")
    else:
        dpg.set_value("st_state", "Running")
    if finished and not finished_logged:
        finished_logged = True
        log(f"done: all {on_board} pieces are on the board")
    elif not finished:
        finished_logged = False
    if log_dirty:
        dpg.set_value("log", "\n".join(log_lines))
        log_dirty = False


# ---------------- GUI panels ----------------
with dpg.window(label="Controls", tag="ctrl", pos=(800, 556), width=620, height=265,
                no_close=True, no_collapse=True, no_move=True, no_resize=True):
    with dpg.group(horizontal=True):
        with dpg.child_window(width=290, height=215, border=False):
            dpg.add_slider_int(label="Hub link %", tag="quality", default_value=0,
                               min_value=0, max_value=100, width=150)
            dpg.add_slider_float(label="Speed", tag="speed", default_value=1.0,
                                 min_value=0.1, max_value=8.0, format="%.2fx", width=150)
            dpg.add_slider_int(label="Link hold", tag="hold", default_value=MERGE_FRAMES,
                               min_value=15, max_value=240, width=150)
            dpg.add_slider_int(label="Patience (s)", tag="patience", default_value=PATIENCE // 60,
                               min_value=1, max_value=30, width=150)
            dpg.add_checkbox(label="Show groups / labels", tag="overlay", default_value=True)
            with dpg.group(horizontal=True):
                dpg.add_button(label="Pause", tag="pause_btn", width=90, callback=toggle_pause)
                dpg.add_button(label="Scatter again", width=130, callback=reset)
        with dpg.child_window(width=-1, height=215, border=True):
            dpg.add_text("Event log", color=(140, 170, 230))
            dpg.add_text("", tag="log", wrap=290)

with dpg.window(label="Status", tag="status", pos=(1232, 50), width=190, height=250,
                no_close=True, no_collapse=True, no_move=True, no_resize=True):
    dpg.add_text("", tag="st_state", color=(140, 170, 230))
    dpg.add_text("", tag="st_groups")
    dpg.add_text("", tag="st_board", color=GREEN)
    dpg.add_text("", tag="st_left", color=(160, 166, 180))
    dpg.add_separator()
    dpg.add_text("Outline colours", color=(160, 166, 180))
    dpg.add_text("coloured = a group", color=(120, 190, 255))
    dpg.add_text("gold = full, docking", color=GOLD)
    dpg.add_text("gray text = waiting", color=(160, 166, 180))
    dpg.add_text("white line = linking", color=WHITE)

reset()
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("main", True)

sim_accum = 0.0
while dpg.is_dearpygui_running():
    QUALITY = dpg.get_value("quality")
    SIM_SPEED = dpg.get_value("speed")
    MERGE_FRAMES = dpg.get_value("hold")
    PATIENCE = dpg.get_value("patience") * 60
    SHOW_OVERLAY = dpg.get_value("overlay")
    if not PAUSED:
        sim_accum += SIM_SPEED
        steps = int(sim_accum)
        sim_accum -= steps
        for _ in range(steps):
            tick += 1
            for ag in list(agents):
                if ag in agents:
                    ag.step()
    sync()
    update_overlay()
    update_status()
    dpg.render_dearpygui_frame()

dpg.destroy_context()