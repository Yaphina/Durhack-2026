import random
import dearpygui.dearpygui as dpg
import numpy

GRID = 4
NUM = GRID * GRID
VIEW_W, VIEW_H = 1200, 680
MARGIN_BOTTOM = 40
REPEL_FRAMES = 60      # how long a wrong match is pushed apart
REPEL_SPEED = 3        # pixels per frame
CHASE_LIMIT = 900      # frames before giving up on a target
PASS_CHANCE = 0.6      # chance a smaller chunk passes through a bigger one on contact

# ---------------- HARDCODED FINAL POSITIONS ----------------
# (x, y) of each piece's PNG top-left in the finished picture, in original PNG pixels.
# Piece size is NOT hardcoded: it comes from the PNG itself.
# Values measured with calibrate.py.
FINAL = {
    0:  (0,    0),    1:  (119,  -2),   2:  (394,  -3),   3:  (591,  -5),
    4:  (2,    197),  5:  (120,  258),  6:  (394,  195),  7:  (527,  225),
    8:  (0,    451),  9:  (200,  468),  10: (396,  448),  11: (530,  462),
    12: (-2,   769),  13: (120,  712),  14: (314,  769),  15: (593,  705),
}
TOUCH_MARGIN = 6   # px of slack when deciding two pieces touch

# ---------------- your teammate's code (unchanged) ----------------
def moveTo(destinationPos, imageTag):
    SPEED = 2
    imgPos = dpg.get_item_pos(imageTag)
    length = [numpy.abs(destinationPos[0] - imgPos[0]), numpy.abs(destinationPos[1] - imgPos[1])]
    if (length[0] == 0):
        dpg.configure_item(imageTag, pos=destinationPos)
        return True
    angle = numpy.arctan(length[1] / length[0])
    xSpeed = numpy.cos(angle) * SPEED
    ySpeed = numpy.sin(angle) * SPEED
    xDirection = numpy.sign(destinationPos[0] - imgPos[0])
    yDirection = numpy.sign(destinationPos[1] - imgPos[1])
    newPos = (imgPos[0] + (xSpeed * xDirection), imgPos[1] + (ySpeed * yDirection))
    dpg.configure_item(imageTag, pos=newPos)
    return False

# ---------------- setup: load textures ----------------
dpg.create_context()
dpg.create_viewport(title="Puzzle", width=VIEW_W, height=VIEW_H)

TEX_W, TEX_H = {}, {}
with dpg.texture_registry():
    for n in range(NUM):                                   # piece0 .. piece15
        w, h, ch, data = dpg.load_image(f"mona lisa 4x4 puzzle/piece{n}.png")
        dpg.add_static_texture(width=w, height=h, default_value=data, tag=f"tex{n}")
        TEX_W[n], TEX_H[n] = w, h

# ---------------- scaling: one uniform scale for every piece (never enlarge) ----------------
max_w = max(TEX_W.values())
max_h = max(TEX_H.values())
cell_w = VIEW_W / GRID
cell_h = (VIEW_H - MARGIN_BOTTOM) / GRID
S = min(1.0, 0.95 * cell_w / max_w, 0.95 * cell_h / max_h)

PW  = {n: TEX_W[n] * S for n in range(NUM)}                # displayed PNG size
PH  = {n: TEX_H[n] * S for n in range(NUM)}
FIN = {n: (FINAL[n][0] * S, FINAL[n][1] * S) for n in range(NUM)}

# start every piece in its own shuffled slot with some jitter so nothing overlaps
slots = [(c * cell_w, r * cell_h) for r in range(GRID) for c in range(GRID)]
random.shuffle(slots)
def start_position(i):
    sx, sy = slots[i]
    return (sx + random.uniform(0, max(0, cell_w - PW[i])),
            sy + random.uniform(0, max(0, cell_h - PH[i])))

with dpg.window(label="Puzzle", tag="Primary Window", width=VIEW_W, height=VIEW_H):
    for n in range(NUM):
        dpg.add_image(f"tex{n}", width=PW[n], height=PH[n], pos=start_position(n), tag=f"piece{n}")

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("Primary Window", True)

# ---------------- puzzle knowledge ----------------
def tag(n):
    return f"piece{n}"

def pos(n):
    """Top-left of the PNG."""
    return list(dpg.get_item_pos(tag(n)))

def origin(n):
    """Where the finished picture's top-left would be if this piece were correctly placed.
    Two correctly placed pieces have the same origin."""
    x, y = pos(n)
    return (x - FIN[n][0], y - FIN[n][1])

def center(n):
    x, y = pos(n)
    return (x + PW[n] / 2, y + PH[n] / 2)

def touching_bodies(a, b):
    """True if the two PNG rectangles overlap (with a little slack)."""
    ax, ay = pos(a)
    bx, by = pos(b)
    m = TOUCH_MARGIN
    return (ax < bx + PW[b] + m and bx < ax + PW[a] + m and
            ay < by + PH[b] + m and by < ay + PH[a] + m)

def grid_pos(n):
    return divmod(n, GRID)              # (row, col) in the finished picture

def are_neighbors(a, b):
    """Stand-in for 'edges match perfectly'."""
    r1, c1 = grid_pos(a)
    r2, c2 = grid_pos(b)
    return abs(r1 - r2) + abs(c1 - c2) == 1

# ---------------- group state ----------------
group_of    = {n: n for n in range(NUM)}      # piece -> group id
members     = {n: [n] for n in range(NUM)}    # group id -> list of pieces
target      = {n: None for n in range(NUM)}   # group id -> piece it is chasing
repel_left  = {n: 0 for n in range(NUM)}      # frames of repelling remaining
repel_vel   = {n: (0, 0) for n in range(NUM)}
chase_time  = {n: 0 for n in range(NUM)}
random_next = {n: False for n in range(NUM)}  # True -> next target is a random piece anywhere
failed      = set()                           # frozenset({a, b}) pairs that already rejected each other
passing     = {}                              # frozenset({gid_a, gid_b}) -> True if this contact is a pass-through

def shift_group(gid, dx, dy, clamp=False):
    """Move every member by the same amount. Returns the movement that actually happened."""
    if clamp:
        xs = [pos(m)[0] for m in members[gid]]
        ys = [pos(m)[1] for m in members[gid]]
        x2 = [pos(m)[0] + PW[m] for m in members[gid]]
        y2 = [pos(m)[1] + PH[m] for m in members[gid]]
        dx = max(-min(xs), min(dx, VIEW_W - max(x2)))
        dy = max(-min(ys), min(dy, VIEW_H - MARGIN_BOTTOM - max(y2)))
    for m in members[gid]:
        x, y = pos(m)
        dpg.configure_item(tag(m), pos=(x + dx, y + dy))
    return dx, dy

def pick_target(gid, randomize):
    """Random piece anywhere (after a failure) or the nearest one, never one I've already failed with."""
    def candidates():
        return [p for p in range(NUM)
                if group_of[p] != gid
                and not any(frozenset((m, p)) in failed for m in members[gid])]
    c = candidates()
    if not c:               # everything rejected: forget the history and start over
        failed.clear()
        c = candidates()
    if randomize:
        return random.choice(c)
    def dist(p):
        px, py = center(p)
        return min(numpy.hypot(px - center(m)[0], py - center(m)[1]) for m in members[gid])
    return min(c, key=dist)

def chase(gid):
    chase_time[gid] += 1
    if chase_time[gid] > CHASE_LIMIT and target[gid] is not None:
        for m in members[gid]:
            failed.add(frozenset((m, target[gid])))   # give up on this target
        target[gid] = None
        random_next[gid] = True

    if target[gid] is None or group_of[target[gid]] == gid:
        target[gid] = pick_target(gid, random_next[gid])
        random_next[gid] = False
        chase_time[gid] = 0

    targetPos = pos(target[gid])
    # the member closest to the target drives the group
    anchor = min(members[gid], key=lambda m: numpy.hypot(pos(m)[0] - targetPos[0], pos(m)[1] - targetPos[1]))
    before = pos(anchor)
    moveTo(targetPos, tag(anchor))          # teammate's function moves the anchor one step
    after = pos(anchor)
    dx, dy = after[0] - before[0], after[1] - before[1]
    for m in members[gid]:                  # everyone else copies the same step
        if m != anchor:
            x, y = pos(m)
            dpg.configure_item(tag(m), pos=(x + dx, y + dy))
    shift_group(gid, 0, 0, clamp=True)      # keep chasing groups on screen

def merge(a, b):
    """a and b touch and are true neighbors: snap b's group into place and join the groups."""
    ga, gb = group_of[a], group_of[b]
    oa, ob = origin(a), origin(b)
    shift_group(gb, oa[0] - ob[0], oa[1] - ob[1])   # snap b's group into place
    for m in members[gb]:
        group_of[m] = ga
    members[ga] += members.pop(gb)
    for d in (target, repel_left, repel_vel, chase_time, random_next):
        d.pop(gb)
    target[ga] = None
    chase_time[ga] = 0
    random_next[ga] = False
    shift_group(ga, 0, 0, clamp=True)       # keep the merged group on screen
    print("merged", a, b, "-> group size", len(members[ga]))

def repel(a, b):
    """a and b touched but aren't neighbors: push apart any group that isn't already repelling,
    and send each one after a random piece anywhere."""
    ga, gb = group_of[a], group_of[b]
    ax, ay = center(a)
    bx, by = center(b)
    dx, dy = ax - bx, ay - by
    d = numpy.hypot(dx, dy)
    if d == 0:
        dx, dy, d = random.choice([-1, 1]), random.choice([-1, 1]), 1.414
    ux, uy = dx / d, dy / d
    for g, sign in ((ga, 1), (gb, -1)):
        if repel_left[g] == 0:
            repel_vel[g] = (sign * ux * REPEL_SPEED, sign * uy * REPEL_SPEED)
            repel_left[g] = REPEL_FRAMES
            target[g] = None
            random_next[g] = True
    failed.add(frozenset((a, b)))

def handle_touches():
    touching = [(i, j) for i in range(NUM) for j in range(i + 1, NUM)
                if group_of[i] != group_of[j] and touching_bodies(i, j)]
    # pass 1: correct matches always win (even mid-repel, even mid pass-through)
    for i, j in touching:
        if group_of[i] != group_of[j] and are_neighbors(i, j):
            merge(i, j)
    # pass 2: a wrong touch only repels if one group was actually chasing the other
    live = set()
    for i, j in touching:
        gi, gj = group_of[i], group_of[j]
        if gi == gj or are_neighbors(i, j):
            continue
        key = frozenset((gi, gj))
        live.add(key)
        if len(members[gi]) != len(members[gj]):
            if key not in passing:                       # roll once per contact
                passing[key] = random.random() < PASS_CHANCE
            if passing[key]:
                continue                                 # smaller one passes through
        chasing = target[gi] in members[gj] or target[gj] in members[gi]
        if chasing and (repel_left[gi] == 0 or repel_left[gj] == 0):
            repel(i, j)
    for key in list(passing):                            # contact ended (or groups merged): forget it
        if key not in live:
            del passing[key]

# ---------------- main loop ----------------
solved = False
while dpg.is_dearpygui_running():
    if len(members) > 1:
        for gid in list(members):
            if repel_left[gid] > 0:
                vx, vy = repel_vel[gid]
                adx, ady = shift_group(gid, vx, vy, clamp=True)
                if abs(adx - vx) > 0.01: vx = -vx      # hit a side wall, bounce
                if abs(ady - vy) > 0.01: vy = -vy      # hit top/bottom, bounce
                repel_vel[gid] = (vx, vy)
                repel_left[gid] -= 1
            else:
                chase(gid)
        handle_touches()
        # debug (uncomment if it stalls): once a second, print size, target, repel frames, chase time
        # if dpg.get_frame_count() % 60 == 0:
        #     print({g: (len(members[g]), target[g], repel_left[g], chase_time[g]) for g in members})
    elif not solved:
        solved = True
        print("Puzzle solved!")
    dpg.render_dearpygui_frame()

dpg.destroy_context()