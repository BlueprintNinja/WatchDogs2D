import pygame
import sys
import random
import asyncio  # Import asyncio

# Configuration constants
CELL_SIZE = 80               # size of each cell in pixels
SIDEBAR_WIDTH = 300          # width of the terminal sidebar

# Grid difficulty settings
INITIAL_GRID_SIZE = 3
MAX_GRID_SIZE = 8
GRID_INCREASE_INTERVAL = 2   # increase grid size every 2 phases

BASE_LEVEL_TIME = 60000      # base time per phase in ms
LEVEL_TIME_REDUCTION = 5000  # ms reduced per phase
MIN_LEVEL_TIME = 30000       # minimum time per phase in ms
LEVEL_COMPLETE_DELAY = 2000  # delay after phase completion in ms

# UI Bar settings
LARGE_UI_BAR_HEIGHT = 60
SMALL_UI_BAR_HEIGHT = 80    # total height for two rows in small grids

# Auto-solved chance for a puzzle at the start (e.g., 5%)
AUTO_SOLVED_CHANCE = 0.05

# Colors (neon & futuristic aesthetics)
BACKGROUND_COLOR = (10, 10, 10)
GRID_BG_COLOR = (20, 20, 20)
CELL_COLOR = (30, 30, 30)
LINE_COLOR = (57, 255, 20)          # bright neon green for lines
UI_BAR_COLOR = (15, 15, 15)
HIGHLIGHT_COLOR = (255, 215, 0)       # yellow glow for a hacked network
HINT_HIGHLIGHT_COLOR = (0, 255, 0)    # green highlight for the hint path
UI_TEXT_COLOR = (57, 255, 20)
ENTRANCE_NODE_COLOR = (0, 200, 200)
EXIT_NODE_COLOR = (200, 50, 50)
SIDEBAR_BG_COLOR = (5, 5, 5)
SIDEBAR_TEXT_COLOR = (57, 255, 20)
POPUP_BG_COLOR = (20, 20, 20)
POPUP_BORDER_COLOR = (57, 255, 20)

# Directions: 0:Up, 1:Right, 2:Down, 3:Left.
DIRECTIONS = {0: (0, -1), 1: (1, 0), 2: (0, 1), 3: (-1, 0)}
REVERSE_DIR = {0: 2, 1: 3, 2: 0, 3: 1}

# Terminal Sidebar settings
TERMINAL_FONT_SIZE = 18
TERMINAL_MAX_LINES = 20
TERMINAL_UPDATE_INTERVAL = 500  # milliseconds

# Global terminal variables
terminal_messages = []
last_terminal_update = 0

# Global hint-related variables
hint_mode = False
HINT_MODE_MAX_DURATION = 6000   # maximum duration for hint mode in ms
HINT_EXTENSION_DELAY = 1000     # extra delay once pieces are in place
hint_start_time = 0
hint_last_update = 0            # track the last rotation update for hint mode
solution_reached_time = None    # time when all solution nodes reached target

# Optional: Uncomment to enable sound effects
# pygame.mixer.init()
# rotate_sound = pygame.mixer.Sound("rotate.ogg")
# success_sound = pygame.mixer.Sound("success.ogg")

class Cell:
    def __init__(self, piece_type, orientation):
        self.piece_type = piece_type
        self.orientation = orientation
        self.target = orientation

    def rotate(self):
        if self.piece_type == "plus":
            return
        self.orientation = (self.orientation + 90) % 360

    def get_connections(self):
        if self.piece_type == "line":
            return [0, 2] if self.orientation % 180 == 0 else [1, 3]
        elif self.piece_type == "corner":
            if self.orientation == 0:
                return [0, 1]
            elif self.orientation == 90:
                return [1, 2]
            elif self.orientation == 180:
                return [2, 3]
            elif self.orientation == 270:
                return [3, 0]
        elif self.piece_type == "tshape":
            if self.orientation == 0:
                return [0, 1, 3]
            elif self.orientation == 90:
                return [0, 1, 2]
            elif self.orientation == 180:
                return [1, 2, 3]
            elif self.orientation == 270:
                return [0, 2, 3]
        elif self.piece_type == "plus":
            return [0, 1, 2, 3]
        return []

def get_piece_for_connections(incoming, outgoing):
    directions_set = {incoming, outgoing}
    if directions_set == {0, 2}:
        if random.choice([True, False]):
            return ("line", 0)
        else:
            return ("tshape", random.choice([90, 270]))
    if directions_set == {1, 3}:
        if random.choice([True, False]):
            return ("line", 90)
        else:
            return ("tshape", random.choice([0, 180]))
    if incoming == outgoing:
        return ("line", 0) if incoming in [0, 2] else ("line", 90)
    if directions_set == {0, 1}:
        return ("corner", 0)
    elif directions_set == {1, 2}:
        return ("corner", 90)
    elif directions_set == {2, 3}:
        return ("corner", 180)
    elif directions_set == {3, 0}:
        return ("corner", 270)
    return ("line", 0)

def generate_solution_path(cols, rows):
    rights_needed = cols - 1
    downs_needed = rows - 1
    moves = ['R'] * rights_needed + ['D'] * downs_needed
    random.shuffle(moves)
    path = [(0, 0)]
    x, y = 0, 0
    for move in moves:
        if move == 'R':
            x += 1
        elif move == 'D':
            y += 1
        path.append((x, y))
    return path

def create_board(grid_size):
    board = [[None for _ in range(grid_size)] for _ in range(grid_size)]
    solution_path = generate_solution_path(grid_size, grid_size)
    for i, (x, y) in enumerate(solution_path):
        use_plus = random.random() < 0.1
        if use_plus:
            piece_type = "plus"
            solved_orientation = 0
        else:
            if i == 0:
                next_x, next_y = solution_path[i + 1]
                dx, dy = next_x - x, next_y - y
                for d, (ddx, ddy) in DIRECTIONS.items():
                    if ddx == dx and ddy == dy:
                        out_dir = d
                        break
                solved_orientation = 0 if out_dir in [0, 2] else 90
                piece_type = "line"
            elif i == len(solution_path) - 1:
                prev_x, prev_y = solution_path[i - 1]
                dx, dy = x - prev_x, y - prev_y
                for d, (ddx, ddy) in DIRECTIONS.items():
                    if ddx == dx and ddy == dy:
                        prev_move = d
                        break
                incoming = REVERSE_DIR[prev_move]
                solved_orientation = 0 if incoming in [0, 2] else 90
                piece_type = "line"
            else:
                prev_x, prev_y = solution_path[i - 1]
                next_x, next_y = solution_path[i + 1]
                dx_in, dy_in = x - prev_x, y - prev_y
                for d, (ddx, ddy) in DIRECTIONS.items():
                    if ddx == dx_in and ddy == dy_in:
                        incoming = REVERSE_DIR[d]
                        break
                dx_out, dy_out = next_x - x, next_y - y
                for d, (ddx, ddy) in DIRECTIONS.items():
                    if ddx == dx_out and ddy == dy_out:
                        out_dir = d
                        break
                piece_type, solved_orientation = get_piece_for_connections(incoming, out_dir)
        cell = Cell(piece_type, solved_orientation)
        cell.target = solved_orientation
        board[y][x] = cell
    for y in range(grid_size):
        for x in range(grid_size):
            if board[y][x] is None:
                piece_type = random.choices(
                    ["line", "corner", "tshape", "plus"],
                    weights=[40, 30, 30, 5]
                )[0]
                orientation = random.choice([0, 90, 180, 270])
                board[y][x] = Cell(piece_type, orientation)
    for (x, y) in solution_path:
        cell = board[y][x]
        if cell.piece_type == "plus":
            continue
        possible_orientations = [0, 90, 180, 270]
        if cell.target in possible_orientations:
            possible_orientations.remove(cell.target)
        cell.orientation = random.choice(possible_orientations)
    return board, solution_path

def find_connection_path(board):
    grid_size = len(board)
    visited = set()
    parent = {}
    def dfs(x, y):
        if (x, y) == (grid_size - 1, grid_size - 1):
            return True
        visited.add((x, y))
        for d in board[y][x].get_connections():
            dx, dy = DIRECTIONS[d]
            nx, ny = x + dx, y + dy
            if 0 <= nx < grid_size and 0 <= ny < grid_size:
                neighbor = board[ny][nx]
                if REVERSE_DIR[d] in neighbor.get_connections() and (nx, ny) not in visited:
                    parent[(nx, ny)] = (x, y)
                    if dfs(nx, ny):
                        return True
        return False
    if dfs(0, 0):
        path = []
        cur = (grid_size - 1, grid_size - 1)
        while cur != (0, 0):
            path.append(cur)
            cur = parent[cur]
        path.append((0, 0))
        path.reverse()
        return path
    return None

def get_level_time(level):
    time_allowed = BASE_LEVEL_TIME - (level - 1) * LEVEL_TIME_REDUCTION
    return max(time_allowed, MIN_LEVEL_TIME)

def get_grid_size_for_level(level):
    additional = (level - 1) // GRID_INCREASE_INTERVAL
    return min(MAX_GRID_SIZE, INITIAL_GRID_SIZE + additional)

async def main():
    global hint_mode, hint_start_time, hint_last_update, solution_reached_time
    pygame.init()
    global terminal_messages, last_terminal_update
    terminal_messages = []
    last_terminal_update = pygame.time.get_ticks()
    level = 1
    points = 0
    state = "playing"
    grid_size = get_grid_size_for_level(level)
    current_level_time = get_level_time(level)
    top_ui_height = SMALL_UI_BAR_HEIGHT if grid_size < 5 else LARGE_UI_BAR_HEIGHT
    board, solution_path = create_board(grid_size)
    if random.random() < AUTO_SOLVED_CHANCE:
        for (x, y) in solution_path:
            board[y][x].orientation = board[y][x].target
    game_width = grid_size * CELL_SIZE
    screen_width = game_width + SIDEBAR_WIDTH
    screen_height = grid_size * CELL_SIZE + top_ui_height
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Neon Network Breach")
    level_start_time = pygame.time.get_ticks()
    clock = pygame.time.Clock()
    timeout_start = 0
    rotation_interval = 1000
    while True:
        current_time = pygame.time.get_ticks()
        elapsed = current_time - level_start_time
        time_left = max(0, current_level_time - elapsed)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_h and not hint_mode:
                    hint_mode = True
                    hint_start_time = current_time
                    hint_last_update = current_time
                    solution_reached_time = None
                    for (x, y) in solution_path:
                        board[y][x].orientation = (board[y][x].target - 90) % 360
            elif event.type == pygame.MOUSEBUTTONDOWN and state == "playing":
                mx, my = pygame.mouse.get_pos()
                if mx < game_width:
                    grid_x = mx // CELL_SIZE
                    grid_y = (my - top_ui_height) // CELL_SIZE
                    if 0 <= grid_x < grid_size and 0 <= grid_y < grid_size:
                        board[grid_y][grid_x].rotate()
        if hint_mode:
            if current_time - hint_last_update > rotation_interval:
                for (x, y) in solution_path:
                    target = board[y][x].target
                    current_orient = board[y][x].orientation
                    if current_orient != target:
                        diff = (target - current_orient) % 360
                        if diff == 270:
                            board[y][x].orientation = (current_orient - 90) % 360
                        else:
                            board[y][x].orientation = (current_orient + 90) % 360
                hint_last_update = current_time
            all_correct = all(board[y][x].orientation == board[y][x].target for (x, y) in solution_path)
            if all_correct and solution_reached_time is None:
                solution_reached_time = current_time
            if (current_time - hint_start_time > HINT_MODE_MAX_DURATION) or \
               (solution_reached_time is not None and current_time - solution_reached_time > HINT_EXTENSION_DELAY):
                hint_mode = False
        if (current_time - last_terminal_update) > TERMINAL_UPDATE_INTERVAL:
            new_msg = generate_random_terminal_message()
            terminal_messages.append(new_msg)
            if len(terminal_messages) > TERMINAL_MAX_LINES:
                terminal_messages.pop(0)
            last_terminal_update = current_time
        connection_path = None
        if not hint_mode:
            connection_path = find_connection_path(board)
        if state == "playing":
            if connection_path:
                bonus = int(time_left / 100)
                points += bonus + 100
                state = "hacked"
                level_complete_start = current_time
            elif time_left <= 0:
                state = "timeout"
                timeout_start = current_time
        elif state == "hacked":
            if current_time - level_complete_start > LEVEL_COMPLETE_DELAY:
                level += 1
                grid_size = get_grid_size_for_level(level)
                current_level_time = get_level_time(level)
                board, solution_path = create_board(grid_size)
                if random.random() < AUTO_SOLVED_CHANCE:
                    for (x, y) in solution_path:
                        board[y][x].orientation = board[y][x].target
                top_ui_height = SMALL_UI_BAR_HEIGHT if grid_size < 5 else LARGE_UI_BAR_HEIGHT
                game_width = grid_size * CELL_SIZE
                screen_width = game_width + SIDEBAR_WIDTH
                screen_height = grid_size * CELL_SIZE + top_ui_height
                screen = pygame.display.set_mode((screen_width, screen_height))
                level_start_time = current_time
                state = "playing"
        elif state == "timeout":
            if current_time - timeout_start > LEVEL_COMPLETE_DELAY:
                board, solution_path = create_board(grid_size)
                if random.random() < AUTO_SOLVED_CHANCE:
                    for (x, y) in solution_path:
                        board[y][x].orientation = board[y][x].target
                level_start_time = current_time
                current_level_time = get_level_time(level)
                state = "playing"
        game_area = pygame.Rect(0, 0, game_width, screen_height)
        pygame.draw.rect(screen, GRID_BG_COLOR, game_area)
        for y in range(grid_size):
            for x in range(grid_size):
                draw_cell(screen, board[y][x], x, y, top_ui_height)
        if hint_mode:
            for (x, y) in solution_path:
                draw_highlighted_lines(screen, board[y][x], x, y, top_ui_height, HINT_HIGHLIGHT_COLOR)
        elif connection_path:
            for (x, y) in connection_path:
                draw_highlighted_lines(screen, board[y][x], x, y, top_ui_height, HIGHLIGHT_COLOR)
        entrance_box_color = HINT_HIGHLIGHT_COLOR if (hint_mode or connection_path) else ENTRANCE_NODE_COLOR
        exit_box_color = HINT_HIGHLIGHT_COLOR if (hint_mode or connection_path) else EXIT_NODE_COLOR
        draw_endpoint_box(screen, 0, 0, top_ui_height, entrance_box_color)
        draw_endpoint_box(screen, grid_size - 1, grid_size - 1, top_ui_height, exit_box_color)
        if grid_size < 5:
            draw_ui_double_bar(screen, level, points, time_left, game_width, top_ui_height)
        else:
            draw_ui_bar(screen, level, points, time_left, game_width, top_ui_height)
            draw_glitch_effect(screen, game_width, top_ui_height)
        sidebar_rect = pygame.Rect(game_width, 0, SIDEBAR_WIDTH, screen_height)
        draw_terminal_sidebar(screen, sidebar_rect)
        if state == "hacked":
            draw_popup_notification(screen, "Network Breached!\nAccess Granted.", game_width, screen_height)
        elif state == "timeout":
            draw_popup_notification(screen, "Access Denied!\nSystem Rebooting...", game_width, screen_height)
        pygame.display.flip()
        await asyncio.sleep(0)
        clock.tick(30)

if __name__ == "__main__":
    asyncio.run(main())
