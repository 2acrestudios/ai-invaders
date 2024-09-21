# AI Invaders by 2 Acre Studios
import pygame
import random
import sys
import requests
import threading
import json
import re

pygame.init()

# Constants
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
PLAYER_SIZE = 50
ENEMY_SIZE = 40
BULLET_SIZE = 5
BULLET_SPEED = 15
ENEMY_BULLET_SPEED = 5
START_ENEMY_SPEED = 2
MOVE_DOWN_STEP = 10
LEVEL_CHANGE_INCREASE = 0.5
GAME_OVER_Y = SCREEN_HEIGHT - 100
SHOOTING_FREQUENCY = 120
UFO_SIZE = 60
UFO_SPEED = 3
UFO_SPAWN_FREQUENCY = 500  # UFO appears every 500 frames
EXPLOSION_DURATION = 30  # Frames

# Colors
COLOR_WHITE = (255, 255, 255)
COLOR_GREEN = (0, 255, 0)
COLOR_RED = (255, 0, 0)
COLOR_BLUE = (0, 0, 255)
COLOR_YELLOW = (255, 255, 0)
COLOR_PURPLE = (128, 0, 128)
COLOR_CYAN = (0, 255, 255)
COLOR_ORANGE = (255, 165, 0)
COLOR_PINK = (255, 20, 147)
COLOR_SILVER = (192, 192, 192)
COLOR_BLACK = (0, 0, 0)

# Screen setup
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('AI Invaders')

# Player setup
player_pos = [SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60]

# Enemy setup
def initialize_invaders():
    invaders = []
    for row in range(4):
        for col in range(10):
            x = col * (ENEMY_SIZE + 20) + 100
            y = row * (ENEMY_SIZE + 20) + 50
            invaders.append({'pos': [x, y], 'explosion_timer': 0})
    return invaders

invaders = initialize_invaders()
direction = 1
enemy_speed = START_ENEMY_SPEED
level = 1
score = 0

# UFO setup
ufo = None  # UFO will be a dictionary with position and direction when active
ufo_timer = 0  # Timer to control UFO spawning

# Bullet setups
player_bullets = []
enemy_bullets = []
ufo_bullets = []

# Explosion effects
explosions = []

# Font setup
font = pygame.font.SysFont('consolas', 20)

# Shape and Color details
def get_level_details(level):
    shapes = {
        1: ("rectangle", COLOR_RED),
        2: ("circle", COLOR_BLUE),
        3: ("triangle", COLOR_GREEN),
        4: ("rectangle", COLOR_PURPLE),
        5: ("circle", COLOR_YELLOW),
        6: ("triangle", COLOR_ORANGE),
        7: ("rectangle", COLOR_PINK),
        8: ("circle", COLOR_CYAN),
        9: ("triangle", COLOR_SILVER),
        10: ("rectangle", COLOR_WHITE)
    }
    return shapes[(level - 1) % len(shapes) + 1]

# Draw shapes based on type and color
def draw_shape(screen, shape_type, color, x, y, size=ENEMY_SIZE):
    if shape_type == "rectangle":
        pygame.draw.rect(screen, color, (x, y, size, size))
    elif shape_type == "circle":
        pygame.draw.circle(screen, color, (x + size // 2, y + size // 2), size // 2)
    elif shape_type == "triangle":
        points = [(x, y + size), (x + size // 2, y), (x + size, y + size)]
        pygame.draw.polygon(screen, color, points)

def draw_elements():
    global level
    shape, invader_color = get_level_details(level)
    # Draw player
    pygame.draw.rect(screen, COLOR_GREEN, (player_pos[0], player_pos[1], PLAYER_SIZE, PLAYER_SIZE))
    # Draw player bullets
    for bullet in player_bullets:
        pygame.draw.rect(screen, COLOR_WHITE, (bullet[0], bullet[1], BULLET_SIZE, BULLET_SIZE))
    # Draw enemy bullets
    for bullet in enemy_bullets:
        pygame.draw.rect(screen, invader_color, (bullet[0], bullet[1], BULLET_SIZE, BULLET_SIZE))
    # Draw UFO bullets
    for bullet in ufo_bullets:
        pygame.draw.rect(screen, COLOR_RED, (bullet[0], bullet[1], BULLET_SIZE + 2, BULLET_SIZE + 10))
    # Draw invaders
    for invader in invaders:
        x, y = invader['pos']
        if invader['explosion_timer'] > 0:
            # Draw explosion effect
            pygame.draw.circle(screen, COLOR_ORANGE, (x + ENEMY_SIZE // 2, y + ENEMY_SIZE // 2), ENEMY_SIZE // 2)
        else:
            draw_shape(screen, shape, invader_color, x, y)
    # Draw UFO
    if ufo:
        x, y = ufo['pos']
        draw_shape(screen, "rectangle", COLOR_SILVER, x, y, UFO_SIZE)
    # Draw explosions
    for explosion in explosions:
        x, y, timer = explosion
        pygame.draw.circle(screen, COLOR_YELLOW, (x, y), 20)
        explosion[2] -= 1
        if explosion[2] <= 0:
            explosions.remove(explosion)

def draw_invaders_row(y_position):
    num_invaders = 10
    invader_spacing = (SCREEN_WIDTH - (num_invaders * ENEMY_SIZE)) // (num_invaders + 1)

    for i in range(num_invaders):
        shape, color = get_level_details(i + 1)
        x_position = invader_spacing + i * (ENEMY_SIZE + invader_spacing)
        draw_shape(screen, shape, color, x_position, y_position)

def fetch_ai_message_for_game_over():
    """Fetch a dynamic game-over message from the AI model, commenting on the player's score."""
    prompt = f"Say something to the player about their performance based on them scoring {score} points in the game against you as the Invaders. An average score is 300 points."
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={'model': 'gemma:2b-instruct', 'prompt': prompt}
        )
        response.raise_for_status()

        # Initialize an empty string to accumulate messages
        complete_message = ""
        lines = response.text.strip().split('\n')
        for line in lines:
            try:
                data = json.loads(line)
                # Check if the 'done' flag is True, if so, break the loop
                if data.get('done', False):
                    break
                # Append each part of the message to the complete_message string
                complete_message += data.get('response', '')  # Extract the response part
            except json.JSONDecodeError:
                print("Failed to parse JSON from line:", line)
                continue

        # If complete_message is empty after the loop, provide a default message
        if not complete_message:
            return "Thank you for playing! No dynamic message available."
        return complete_message.strip()

    except requests.RequestException as e:
        print(f"Error fetching AI message: {e}")
        return "Thank you for playing! (Could not fetch dynamic message)"

def wrap_text(text, font, max_width):
    words = text.split(' ')
    lines = []
    current_line = ""
    for word in words:
        # Check if adding the next word would exceed the length limit
        test_line = current_line + word + " "
        if font.size(test_line)[0] > max_width:
            lines.append(current_line)  # Add the current line to lines
            current_line = word + " "  # Start a new line with the current word
        else:
            current_line += word + " "  # Add the word to the current line
    if current_line:
        lines.append(current_line)  # Add any remaining text as the last line
    return lines

def show_game_over():
    ai_message = fetch_ai_message_for_game_over()
    screen.fill((0, 0, 0))

    # Larger font for the game title
    title_font = pygame.font.SysFont('consolas', 90)
    title_text = title_font.render('AI Invaders', True, COLOR_GREEN)
    title_pos = (SCREEN_WIDTH // 2 - title_text.get_width() // 2, 10)
    screen.blit(title_text, title_pos)

    # Draw a row of Invaders with adjusted y_position
    draw_invaders_row(120)  # Adjust this value based on your layout preferences

    game_over_text = font.render('Game Over!', True, COLOR_RED)
    final_score_text = font.render(f'Score: {score}', True, COLOR_CYAN)
    instructions_text = font.render('Press C to Play Again or X to Exit', True, COLOR_PINK)

    # Blit the Game Over, Final Score, and Instructions texts
    screen.blit(game_over_text, (SCREEN_WIDTH // 2 - game_over_text.get_width() // 2, SCREEN_HEIGHT // 2 - 100))
    screen.blit(final_score_text, (SCREEN_WIDTH // 2 - final_score_text.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
    screen.blit(instructions_text, (SCREEN_WIDTH // 2 - instructions_text.get_width() // 2, SCREEN_HEIGHT - 40))

    # Wrap and blit the AI message text
    wrapped_text = wrap_text(ai_message, font, SCREEN_WIDTH - 20)
    y_offset = SCREEN_HEIGHT // 2 + 10
    for line in wrapped_text:
        rendered_line = font.render(line, True, COLOR_WHITE)
        screen.blit(rendered_line, (SCREEN_WIDTH // 2 - rendered_line.get_width() // 2, y_offset))
        y_offset += font.get_height() + 5

    pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_x:
                    pygame.quit()
                    sys.exit()
                elif event.key == pygame.K_c:
                    restart_game()

def restart_game():
    global score, level, invaders, player_bullets, enemy_bullets, ufo_bullets, direction, ufo, ufo_timer
    score = 0
    level = 1
    invaders = initialize_invaders()
    player_bullets = []
    enemy_bullets = []
    ufo_bullets = []
    direction = 1
    ufo = None
    ufo_timer = 0
    game_loop()

def ai_controlled_shoot():
    global invaders, enemy_bullets
    decision = fetch_ai_decision()
    if decision is not None and invaders:
        shooter_idx = int(decision) % len(invaders)
        shooter = invaders[shooter_idx]['pos']
        enemy_bullets.append([shooter[0] + ENEMY_SIZE // 2, shooter[1] + ENEMY_SIZE])

def fetch_ai_decision():
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                'model': 'gemma:2b-instruct',
                'prompt': 'You are playing a game of Space Invaders against a human player. You are the Invaders. Which Invader (0-39) should fire next? Reply with only a number.'
            }
        )
        response.raise_for_status()

        full_response = ""
        if not response.text.strip():
            print("Received an empty response from AI.")
            return None

        lines = response.text.strip().split('\n')
        for line in lines:
            if line.strip():
                try:
                    data = json.loads(line)
                    if 'response' in data:
                        full_response += data['response']
                    if 'done' in data and data['done']:
                        break
                except json.JSONDecodeError as e:
                    print(f"JSON parsing error on line: {line} with error {e}")

        match = re.search(r'\b\d+\b', full_response)
        if match:
            decision = match.group(0)
            return decision

        print("No valid AI decision found in the reassembled response.")
        return None
    except requests.RequestException as e:
        print(f"Error fetching decision from AI: {e}")
        return None

def game_loop():
    global direction, enemy_speed, level, score, invaders, ufo, ufo_timer
    running = True
    clock = pygame.time.Clock()
    frame_count = 0

    while running:
        screen.fill((0, 0, 0))
        level_text = font.render(f'Level: {level}', True, COLOR_WHITE)
        score_text = font.render(f'Score: {score}', True, COLOR_WHITE)
        screen.blit(level_text, (10, 10))
        screen.blit(score_text, (10, 30))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and player_pos[0] > 0:
            player_pos[0] -= 5
        if keys[pygame.K_RIGHT] and player_pos[0] < SCREEN_WIDTH - PLAYER_SIZE:
            player_pos[0] += 5
        if keys[pygame.K_SPACE] and len(player_bullets) < 3 and frame_count % 10 == 0:
            player_bullets.append([player_pos[0] + PLAYER_SIZE // 2, player_pos[1]])

        update_bullets()
        if frame_count % SHOOTING_FREQUENCY == 0:
            threading.Thread(target=ai_controlled_shoot, daemon=True).start()

        update_invaders()
        update_ufo()

        draw_elements()

        pygame.display.flip()
        clock.tick(60)
        frame_count += 1

def update_bullets():
    global player_bullets, enemy_bullets, ufo_bullets, score, ufo
    # Player bullets
    for bullet in player_bullets[:]:
        bullet[1] -= BULLET_SPEED
        if bullet[1] < 0:
            player_bullets.remove(bullet)
        else:
            # Check collision with invaders
            for invader in invaders[:]:
                x, y = invader['pos']
                if x <= bullet[0] <= x + ENEMY_SIZE and y <= bullet[1] <= y + ENEMY_SIZE:
                    player_bullets.remove(bullet)
                    invader['explosion_timer'] = EXPLOSION_DURATION
                    score += 10
                    break
            # Check collision with UFO
            if ufo:
                x, y = ufo['pos']
                if x <= bullet[0] <= x + UFO_SIZE and y <= bullet[1] <= y + UFO_SIZE:
                    player_bullets.remove(bullet)
                    explosions.append([x + UFO_SIZE // 2, y + UFO_SIZE // 2, EXPLOSION_DURATION])
                    ufo = None
                    score += 50

    # Enemy bullets
    for bullet in enemy_bullets[:]:
        bullet[1] += ENEMY_BULLET_SPEED
        if bullet[1] > SCREEN_HEIGHT:
            enemy_bullets.remove(bullet)
        elif player_pos[0] <= bullet[0] <= player_pos[0] + PLAYER_SIZE and player_pos[1] <= bullet[1] <= player_pos[1] + PLAYER_SIZE:
            show_game_over()

    # UFO bullets
    for bullet in ufo_bullets[:]:
        bullet[1] += ENEMY_BULLET_SPEED + 2
        if bullet[1] > SCREEN_HEIGHT:
            ufo_bullets.remove(bullet)
        elif player_pos[0] <= bullet[0] <= player_pos[0] + PLAYER_SIZE and player_pos[1] <= bullet[1] <= player_pos[1] + PLAYER_SIZE:
            show_game_over()

def update_invaders():
    global invaders, direction, level, enemy_speed, score
    move_down = False
    for invader in invaders:
        invader['pos'][0] += direction * enemy_speed
        x, y = invader['pos']
        if x + ENEMY_SIZE > SCREEN_WIDTH or x < 0:
            move_down = True
        if y > GAME_OVER_Y:
            show_game_over()
        # Update explosion timer
        if invader['explosion_timer'] > 0:
            invader['explosion_timer'] -= 1
            if invader['explosion_timer'] <= 0:
                invaders.remove(invader)

    if move_down:
        direction *= -1
        for invader in invaders:
            invader['pos'][1] += MOVE_DOWN_STEP

    if not invaders:
        level += 1
        enemy_speed += LEVEL_CHANGE_INCREASE
        score += 100
        invaders.extend(initialize_invaders())

def update_ufo():
    global ufo, ufo_timer, ufo_bullets
    if not ufo:
        ufo_timer += 1
        if ufo_timer >= UFO_SPAWN_FREQUENCY:
            ufo = {'pos': [0, 30], 'direction': UFO_SPEED}
            ufo_timer = 0
    else:
        ufo['pos'][0] += ufo['direction']
        if ufo['pos'][0] > SCREEN_WIDTH or ufo['pos'][0] < -UFO_SIZE:
            ufo = None
        else:
            # UFO fires bullets occasionally
            if random.randint(0, 100) < 1:
                ufo_bullets.append([ufo['pos'][0] + UFO_SIZE // 2, ufo['pos'][1] + UFO_SIZE])

# Start game loop
game_loop()
