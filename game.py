import pygame
import sys
import random
from collections import deque

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
# rotate_sound = pygame.mixer.Sound("rotate.wav")
# success_sound = pygame.mixer.Sound("success.wav")

class Cell:
    def __init__(self, piece_type, orientation):
        # piece_type: "line", "corner", "tshape", or "plus"
        # orientation: one of 0, 90, 180, or 270 degrees
        self.piece_type = piece_type
        self.orientation = orientation
        # target stores the solved orientation (used in hint mode)
        self.target = orientation

    def rotate(self):
        # For plus shaped nodes, rotation doesn't change connectivity.
        if self.piece_type == "plus":
            return
        self.orientation = (self.orientation + 90) % 360
        # Uncomment to play a rotation sound:
        # rotate_sound.play()

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
            # T-shaped piece: three connections, missing one
            if self.orientation == 0:    # missing down
                return [0, 1, 3]
            elif self.orientation == 90:   # missing left
                return [0, 1, 2]
            elif self.orientation == 180:  # missing up
                return [1, 2, 3]
            elif self.orientation == 270:  # missing right
                return [0, 2, 3]
        elif self.piece_type == "plus":
            # Plus shaped piece: all four connections.
            return [0, 1, 2, 3]
        return []

def get_piece_for_connections(incoming, outgoing):
    """
    Returns a piece_type and orientation for a connection defined by the two required connection directions.
    The order of incoming and outgoing does not matter.
    Handles straight (opposite) connections with added variety: sometimes a line,
    sometimes a T shaped piece with an extra connection.
    For non-straight connections, returns a corner piece.
    """
    directions_set = {incoming, outgoing}
    # Handle straight line cases, with variety.
    if directions_set == {0, 2}:
        # Vertical straight: choose between a line or a T shape that still has vertical connectivity.
        if random.choice([True, False]):
            return ("line", 0)
        else:
            return ("tshape", random.choice([90, 270]))
    if directions_set == {1, 3}:
        # Horizontal straight.
        if random.choice([True, False]):
            return ("line", 90)
        else:
            return ("tshape", random.choice([0, 180]))
    # For one connection (if both are same) use a line piece.
    if incoming == outgoing:
        return ("line", 0) if incoming in [0, 2] else ("line", 90)
    # Handle corners.
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
    """
    Generates a random monotonic path from (0,0) to (cols-1, rows-1)
    using only right ('R') and down ('D') moves.
    """
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
    """
    Creates a board (grid_size x grid_size) with a guaranteed solution path.
    The solution path nodes are built with matching connection directions and may
    occasionally incorporate a plus node for added hacker flair.
    After building the board, we scramble the solution path nodes so the phase doesn't start solved.
    Returns:
      - board: a 2D list of Cell objects.
      - solution_path: list of (x,y) tuples representing the solution path.
    """
    board = [[None for _ in range(grid_size)] for _ in range(grid_size)]
    solution_path = generate_solution_path(grid_size, grid_size)

    # Build solution path nodes with proper connectivity.
    for i, (x, y) in enumerate(solution_path):
        # Increase rarity of plus nodes in the solution: only 10% chance.
        use_plus = random.random() < 0.1
        if use_plus:
            piece_type = "plus"
            solved_orientation = 0  # Orientation is irrelevant for plus pieces.
        else:
            if i == 0:
                # First node: only an outgoing connection.
                next_x, next_y = solution_path[i + 1]
                dx, dy = next_x - x, next_y - y
                for d, (ddx, ddy) in DIRECTIONS.items():
                    if ddx == dx and ddy == dy:
                        out_dir = d
                        break
                solved_orientation = 0 if out_dir in [0, 2] else 90
                piece_type = "line"
            elif i == len(solution_path) - 1:
                # Last node: only an incoming connection.
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
                # Intermediate node: gets an incoming connection from the previous node
                # and an outgoing connection towards the next node.
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
        cell.target = solved_orientation  # record the solved orientation
        board[y][x] = cell

    # Fill in the remaining board nodes with random pieces.
    # Increase rarity of plus pieces here using weights: line 40, corner 30, tshape 30, plus 5.
    for y in range(grid_size):
        for x in range(grid_size):
            if board[y][x] is None:
                piece_type = random.choices(
                    ["line", "corner", "tshape", "plus"],
                    weights=[40, 30, 30, 5]
                )[0]
                orientation = random.choice([0, 90, 180, 270])
                board[y][x] = Cell(piece_type, orientation)
    
    # --- Scramble the solution path nodes ---
    # Prevent the game from starting with a solved path by rotating each
    # solution node to a random orientation that is not the solved one.
    for (x, y) in solution_path:
        cell = board[y][x]
        # Only scramble pieces that are not plus, as plus nodes remain constant.
        if cell.piece_type == "plus":
            continue
        possible_orientations = [0, 90, 180, 270]
        if cell.target in possible_orientations:
            possible_orientations.remove(cell.target)
        cell.orientation = random.choice(possible_orientations)

    return board, solution_path

def draw_cell(screen, cell, x, y, top_ui_height):
    """
    Draws a node and its connection lines at grid coordinate (x, y).
    """
    cell_x = x * CELL_SIZE
    cell_y = y * CELL_SIZE + top_ui_height
    rect = pygame.Rect(cell_x, cell_y, CELL_SIZE, CELL_SIZE)
    pygame.draw.rect(screen, CELL_COLOR, rect)
    pygame.draw.rect(screen, BACKGROUND_COLOR, rect, 1)
    
    cx = cell_x + CELL_SIZE // 2
    cy = cell_y + CELL_SIZE // 2
    for direction in cell.get_connections():
        dx, dy = DIRECTIONS[direction]
        end_x = cx + (CELL_SIZE // 2 - 10) * dx
        end_y = cy + (CELL_SIZE // 2 - 10) * dy
        pygame.draw.line(screen, LINE_COLOR, (cx, cy), (end_x, end_y), 8)

def draw_highlighted_lines(screen, cell, x, y, top_ui_height, color):
    """
    Draws the node's connection lines in a highlight color.
    """
    cell_x = x * CELL_SIZE
    cell_y = y * CELL_SIZE + top_ui_height
    cx = cell_x + CELL_SIZE // 2
    cy = cell_y + CELL_SIZE // 2
    for direction in cell.get_connections():
        dx, dy = DIRECTIONS[direction]
        end_x = cx + (CELL_SIZE // 2 - 10) * dx
        end_y = cy + (CELL_SIZE // 2 - 10) * dy
        pygame.draw.line(screen, color, (cx, cy), (end_x, end_y), 8)

def draw_endpoint_box(screen, x, y, top_ui_height, color):
    """
    Draws a box around a node to indicate an endpoint.
    """
    cell_x = x * CELL_SIZE
    cell_y = y * CELL_SIZE + top_ui_height
    rect = pygame.Rect(cell_x + 5, cell_y + 5, CELL_SIZE - 10, CELL_SIZE - 10)
    pygame.draw.rect(screen, color, rect, 3)

def draw_ui_bar(screen, level, points, time_left, game_width, top_ui_height):
    """
    Draws a single UI bar at the top.
    """
    ui_rect = pygame.Rect(0, 0, game_width, top_ui_height)
    pygame.draw.rect(screen, UI_BAR_COLOR, ui_rect)
    font = pygame.font.SysFont(None, 30)
    section_width = game_width // 3
    # Hacker-themed terminology.
    phase_text = font.render(f"Phase: {level}", True, UI_TEXT_COLOR)
    credits_text = font.render(f"Credits: {points}", True, UI_TEXT_COLOR)
    countdown_text = font.render(f"Countdown: {int(time_left/1000)}s", True, UI_TEXT_COLOR)
    screen.blit(phase_text, (10, 10))
    screen.blit(credits_text, (section_width + 10, 10))
    screen.blit(countdown_text, (2 * section_width + 10, 10))

def draw_ui_double_bar(screen, level, points, time_left, game_width, total_ui_height):
    """
    Draws two UI bar rows for small grids.
    """
    row_height = total_ui_height // 2
    ui_rect1 = pygame.Rect(0, 0, game_width, row_height)
    pygame.draw.rect(screen, UI_BAR_COLOR, ui_rect1)
    ui_rect2 = pygame.Rect(0, row_height, game_width, row_height)
    pygame.draw.rect(screen, UI_BAR_COLOR, ui_rect2)
    font = pygame.font.SysFont(None, 24)
    phase_text = font.render(f"Phase: {level}", True, UI_TEXT_COLOR)
    credits_text = font.render(f"Credits: {points}", True, UI_TEXT_COLOR)
    screen.blit(phase_text, (10, 5))
    screen.blit(credits_text, (game_width // 2, 5))
    countdown_text = font.render(f"Countdown: {int(time_left/1000)}s", True, UI_TEXT_COLOR)
    screen.blit(countdown_text, (10, row_height + 5))

def draw_glitch_effect(screen, width, height):
    """
    Draws a neon glitch effect overlaying the UI bar.
    """
    glitch_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    for _ in range(10):
        x = random.randint(0, width)
        y = random.randint(0, height)
        glitch_width = random.randint(20, 50)
        glitch_height = random.randint(2, 6)
        color = (random.randint(50, 100), random.randint(200, 255), random.randint(50, 100), 100)
        pygame.draw.rect(glitch_surface, color, (x, y, glitch_width, glitch_height))
    screen.blit(glitch_surface, (0, 0))

def update_terminal_messages():
    """
    Updates terminal messages with random cryptic output.
    """
    global terminal_messages, last_terminal_update
    current_time = pygame.time.get_ticks()
    if current_time - last_terminal_update > TERMINAL_UPDATE_INTERVAL:
        new_msg = generate_random_terminal_message()
        terminal_messages.append(new_msg)
        if len(terminal_messages) > TERMINAL_MAX_LINES:
            terminal_messages.pop(0)
        last_terminal_update = current_time

def generate_random_terminal_message():
    """
    Generates a random terminal-style log message.
    """
    prefixes = ["DEBUG", "TRACE", "INFO", "WARN", "ERR"]
    messages = [
        "Accessing matrix node 0x{:04X}".format(random.randint(0, 0xFFFF)),
        "Initializing cyber protocol layer {}...".format(random.randint(1, 5)),
        "Packet intercepted: {} bytes".format(random.randint(50, 500)),
        "Infiltration sequence {} activated".format(random.choice(["A", "B", "C", "D"])),
        "Decrypting security node 0x{:03X}".format(random.randint(0, 0xFFF)),
        "System vulnerability detected!",
        "Bypassing firewall...{}%".format(random.randint(0, 100))
    ]
    return "[{}] {}".format(random.choice(prefixes), random.choice(messages))

def draw_terminal_sidebar(screen, sidebar_rect):
    """
    Draws the terminal sidebar with cryptic messages.
    """
    pygame.draw.rect(screen, SIDEBAR_BG_COLOR, sidebar_rect)
    font = pygame.font.SysFont("Courier", TERMINAL_FONT_SIZE)
    line_height = TERMINAL_FONT_SIZE + 4
    y_offset = sidebar_rect.y + 10
    for msg in terminal_messages:
        text = font.render(msg, True, SIDEBAR_TEXT_COLOR)
        screen.blit(text, (sidebar_rect.x + 10, y_offset))
        y_offset += line_height

def draw_popup_notification(screen, message, game_width, screen_height):
    """
    Draws a retro pop-up notification window emulating an old computer style.
    The message is split into two lines.
    """
    # Determine popup dimensions based on game area
    popup_width = int(game_width * 0.8)
    popup_height = 80
    popup_x = (game_width - popup_width) // 2
    popup_y = (screen_height - popup_height) // 2

    # Draw popup background and border
    popup_rect = pygame.Rect(popup_x, popup_y, popup_width, popup_height)
    pygame.draw.rect(screen, POPUP_BG_COLOR, popup_rect)
    pygame.draw.rect(screen, POPUP_BORDER_COLOR, popup_rect, 3)

    # Adjust font size based on available popup width.
    font_size = 20 if game_width >= 400 else 16
    font = pygame.font.SysFont("Courier", font_size)

    # Split the message into two lines if not already split
    if "\n" in message:
        lines = message.split("\n")
    else:
        # For messages without a newline, split roughly in half
        mid = len(message) // 2
        split_index = message.rfind(" ", 0, mid)
        if split_index == -1:
            split_index = mid
        lines = [message[:split_index], message[split_index:].lstrip()]

    # Render each line and position them
    rendered_lines = [font.render(line, True, LINE_COLOR) for line in lines]
    total_height = sum(line.get_height() for line in rendered_lines)
    current_y = popup_rect.y + (popup_height - total_height) // 2

    for line in rendered_lines:
        text_rect = line.get_rect(centerx=popup_rect.centerx, y=current_y)
        screen.blit(line, text_rect)
        current_y += line.get_height()

def find_connection_path(board):
    """
    Uses DFS to find a valid path from the entrance (0,0) to the exit node.
    Returns the path as a list of (x, y) tuples if found; otherwise, None.
    """
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
    """Calculates the allowed time for a phase."""
    time_allowed = BASE_LEVEL_TIME - (level - 1) * LEVEL_TIME_REDUCTION
    return max(time_allowed, MIN_LEVEL_TIME)

def get_grid_size_for_level(level):
    """Determines grid size based on the current phase."""
    additional = (level - 1) // GRID_INCREASE_INTERVAL
    return min(MAX_GRID_SIZE, INITIAL_GRID_SIZE + additional)

def main():
    global hint_mode, hint_start_time, hint_last_update, solution_reached_time
    pygame.init()
    global terminal_messages, last_terminal_update
    terminal_messages = []
    last_terminal_update = pygame.time.get_ticks()
    
    level = 1
    points = 0
    state = "playing"  # states: playing, hacked, timeout
    
    grid_size = get_grid_size_for_level(level)
    current_level_time = get_level_time(level)
    top_ui_height = SMALL_UI_BAR_HEIGHT if grid_size < 5 else LARGE_UI_BAR_HEIGHT

    board, solution_path = create_board(grid_size)
    # Occasionally start with a solved puzzle.
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

    # Rotation interval for hint mode (in ms)
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
                # Activate hint mode by pressing 'h'
                if event.key == pygame.K_h and not hint_mode:
                    hint_mode = True
                    hint_start_time = current_time
                    hint_last_update = current_time
                    solution_reached_time = None
                    # Initialize each solution node to a starting offset: target - 90 degrees.
                    for (x, y) in solution_path:
                        board[y][x].orientation = (board[y][x].target - 90) % 360
            elif event.type == pygame.MOUSEBUTTONDOWN and state == "playing":
                mx, my = pygame.mouse.get_pos()
                if mx < game_width:
                    grid_x = mx // CELL_SIZE
                    grid_y = (my - top_ui_height) // CELL_SIZE
                    if 0 <= grid_x < grid_size and 0 <= grid_y < grid_size:
                        board[grid_y][grid_x].rotate()

        # Animate hint mode: rotate each solution node until its target orientation is reached.
        if hint_mode:
            if current_time - hint_last_update > rotation_interval:
                for (x, y) in solution_path:
                    target = board[y][x].target
                    current_orient = board[y][x].orientation
                    if current_orient != target:
                        diff = (target - current_orient) % 360
                        # If diff is 270°, rotating counter-clockwise is shorter.
                        if diff == 270:
                            board[y][x].orientation = (current_orient - 90) % 360
                        else:
                            board[y][x].orientation = (current_orient + 90) % 360
                hint_last_update = current_time

            # Confirm all solution nodes are in their target positions.
            all_correct = all(board[y][x].orientation == board[y][x].target for (x, y) in solution_path)
            if all_correct and solution_reached_time is None:
                solution_reached_time = current_time

            # End hint mode when maximum duration is reached or after an extra delay once all nodes match.
            if (current_time - hint_start_time > HINT_MODE_MAX_DURATION) or \
               (solution_reached_time is not None and current_time - solution_reached_time > HINT_EXTENSION_DELAY):
                hint_mode = False

        update_terminal_messages()

        # Only check for a valid connecting path when hint mode is off.
        connection_path = None
        if not hint_mode:
            connection_path = find_connection_path(board)
        
        if state == "playing":
            if connection_path:
                bonus = int(time_left / 100)
                points += bonus + 100
                state = "hacked"
                level_complete_start = current_time
                # Uncomment to play success sound:
                # success_sound.play()
            elif time_left <= 0:
                state = "timeout"
                timeout_start = current_time
        elif state == "hacked":
            if current_time - level_complete_start > LEVEL_COMPLETE_DELAY:
                level += 1
                grid_size = get_grid_size_for_level(level)
                current_level_time = get_level_time(level)
                board, solution_path = create_board(grid_size)
                # Occasionally auto-solve new puzzle at start.
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
                # Occasionally auto-solve puzzle at start.
                if random.random() < AUTO_SOLVED_CHANCE:
                    for (x, y) in solution_path:
                        board[y][x].orientation = board[y][x].target
                level_start_time = current_time
                current_level_time = get_level_time(level)
                state = "playing"
        
        # Draw game area.
        game_area = pygame.Rect(0, 0, game_width, screen_height)
        pygame.draw.rect(screen, GRID_BG_COLOR, game_area)
        for y in range(grid_size):
            for x in range(grid_size):
                draw_cell(screen, board[y][x], x, y, top_ui_height)
        
        # Draw hint path or valid connection path.
        if hint_mode:
            for (x, y) in solution_path:
                draw_highlighted_lines(screen, board[y][x], x, y, top_ui_height, HINT_HIGHLIGHT_COLOR)
        elif connection_path:
            for (x, y) in connection_path:
                draw_highlighted_lines(screen, board[y][x], x, y, top_ui_height, HIGHLIGHT_COLOR)
        
        # Always draw endpoint boxes.
        entrance_box_color = HINT_HIGHLIGHT_COLOR if (hint_mode or connection_path) else ENTRANCE_NODE_COLOR
        exit_box_color = HINT_HIGHLIGHT_COLOR if (hint_mode or connection_path) else EXIT_NODE_COLOR
        draw_endpoint_box(screen, 0, 0, top_ui_height, entrance_box_color)
        draw_endpoint_box(screen, grid_size - 1, grid_size - 1, top_ui_height, exit_box_color)
        
        # Draw UI bar and terminal sidebar.
        if grid_size < 5:
            draw_ui_double_bar(screen, level, points, time_left, game_width, top_ui_height)
        else:
            draw_ui_bar(screen, level, points, time_left, game_width, top_ui_height)
            draw_glitch_effect(screen, game_width, top_ui_height)
        
        sidebar_rect = pygame.Rect(game_width, 0, SIDEBAR_WIDTH, screen_height)
        draw_terminal_sidebar(screen, sidebar_rect)
        
        # Draw pop-up notification for hack success or timeout in a retro old computer style.
        if state == "hacked":
            draw_popup_notification(screen, "Network Breached!\nAccess Granted.", game_width, screen_height)
        elif state == "timeout":
            draw_popup_notification(screen, "Access Denied!\nSystem Rebooting...", game_width, screen_height)
        
        pygame.display.flip()
        clock.tick(30)

if __name__ == "__main__":
    main()
