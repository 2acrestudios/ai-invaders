# AI Invaders by 2 Acre Studios
import pygame
import random
import sys
import requests
import threading
import json
import re
from queue import Queue

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
LEVEL_CHANGE_INCREASE = 0.2  # Reduced from 0.5 to 0.2
GAME_OVER_Y = SCREEN_HEIGHT - 100
SHOOTING_FREQUENCY = 120
UFO_SIZE = 60
UFO_SPEED = 3
UFO_SPAWN_FREQUENCY = 500
EXPLOSION_DURATION = 30
POWER_UP_SIZE = 30
POWER_UP_DURATION = 300

# Adjusted Meteor Constants
METEOR_SIZE = 10
METEOR_FALL_SPEED = 3
METEOR_SHOWER_DURATION = 200
METEOR_CREATION_CHANCE = 1
METEOR_SHOWER_PROBABILITY = 1

# Maximum Difficulty Settings
MAX_DIFFICULTY = 2.0  # Capped maximum difficulty
MAX_ENEMY_SPEED = START_ENEMY_SPEED * MAX_DIFFICULTY

# Colors (same as before)
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
COLOR_GOLD = (255, 215, 0)
COLOR_LIME = (50, 205, 50)
COLOR_MAGENTA = (255, 0, 255)
COLOR_TEAL = (0, 128, 128)
COLOR_OLIVE = (128, 128, 0)

# Screen setup
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('AI Invaders')

# Font setup
font = pygame.font.SysFont('consolas', 20)

# Global Variables Initialization
player_pos = [SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60]
player_speed = 5
player_power_ups = {
    'double_fire': False,
    'rapid_fire': False,
    'invincibility': False,
    'shield': False,
    'score_multiplier': False,
}
power_up_timers = {
    'double_fire': 0,
    'rapid_fire': 0,
    'invincibility': 0,
    'shield': 0,
    'score_multiplier': 0,
}
player_lives = 3
player_positions = []
direction = 1
enemy_speed = START_ENEMY_SPEED
level = 1
score = 0
difficulty = 1.0  # Dynamic difficulty adjustment
ufo = None
ufo_timer = 0
player_bullets = []
enemy_bullets = []
ufo_bullets = []
explosions = []
power_ups = []
meteors = []
meteor_shower_active = False
meteor_shower_timer = 0

# Queues for caching AI messages and decisions
assistant_messages = Queue(maxsize=5)
taunt_messages = Queue(maxsize=5)
ai_decisions = Queue(maxsize=10)

# Shape and Color details (same as before)
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

# Draw shapes based on type and color (same as before)
def draw_shape(screen, shape_type, color, x, y, size=ENEMY_SIZE):
    if shape_type == "rectangle":
        pygame.draw.rect(screen, color, (x, y, size, size))
    elif shape_type == "circle":
        pygame.draw.circle(screen, color, (x + size // 2, y + size // 2), size // 2)
    elif shape_type == "triangle":
        points = [(x, y + size), (x + size // 2, y), (x + size, y + size)]
        pygame.draw.polygon(screen, color, points)

def draw_elements():
    global level, player_lives
    shape, invader_color = get_level_details(level)
    # Draw player
    if player_power_ups['invincibility']:
        pygame.draw.rect(screen, COLOR_GOLD, (player_pos[0], player_pos[1], PLAYER_SIZE, PLAYER_SIZE))
    else:
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
    # Draw power-ups
    for power_up in power_ups:
        x, y = power_up['pos']
        color = get_power_up_color(power_up['type'])
        pygame.draw.rect(screen, color, (x, y, POWER_UP_SIZE, POWER_UP_SIZE))
    # Draw meteors
    for meteor in meteors:
        x, y = meteor['pos']
        pygame.draw.circle(screen, COLOR_ORANGE, (x, y), METEOR_SIZE)
    # Draw lives
    lives_text = font.render(f'Lives: {player_lives}', True, COLOR_WHITE)
    screen.blit(lives_text, (10, 50))

def get_power_up_color(power_up_type):
    colors = {
        'screen_clear': COLOR_LIME,
        'double_fire': COLOR_MAGENTA,
        'rapid_fire': COLOR_CYAN,
        'invincibility': COLOR_GOLD,
        'shield': COLOR_BLUE,
        'extra_life': COLOR_PINK,
        'slow_motion': COLOR_TEAL,
        'score_multiplier': COLOR_YELLOW,
    }
    return colors.get(power_up_type, COLOR_WHITE)

def draw_invaders_row(y_position):
    num_invaders = 10
    invader_spacing = (SCREEN_WIDTH - (num_invaders * ENEMY_SIZE)) // (num_invaders + 1)

    for i in range(num_invaders):
        shape, color = get_level_details(i + 1)
        x_position = invader_spacing + i * (ENEMY_SIZE + invader_spacing)
        draw_shape(screen, shape, color, x_position, y_position)

def fetch_ai_message_for_game_over():
    prompt = f"Say something to the player about their performance based on them scoring {score} points in the game against you as the Invaders. An average score is 500 points."
    return fetch_ai_response(prompt)

def wrap_text(text, font, max_width):
    words = text.split(' ')
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + word + " "
        if font.size(test_line)[0] > max_width:
            lines.append(current_line)
            current_line = word + " "
        else:
            current_line += word + " "
    if current_line:
        lines.append(current_line)
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
    draw_invaders_row(120)

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
    global score, level, invaders, player_bullets, enemy_bullets, ufo_bullets, direction
    global ufo, ufo_timer, player_power_ups, power_up_timers, meteors, meteor_shower_active, meteor_shower_timer
    global difficulty, player_lives, player_speed
    score = 0
    level = 1
    difficulty = 1.0
    enemy_speed = START_ENEMY_SPEED
    invaders.clear()
    invaders.extend(initialize_invaders())
    player_bullets.clear()
    enemy_bullets.clear()
    ufo_bullets.clear()
    power_ups.clear()
    direction = 1
    ufo = None
    ufo_timer = 0
    player_power_ups = {key: False for key in player_power_ups}
    power_up_timers = {key: 0 for key in power_up_timers}
    meteors.clear()
    meteor_shower_active = False
    meteor_shower_timer = 0
    player_lives = 3
    player_speed = 5
    game_loop()

def ai_controlled_shoot():
    if not ai_decisions.empty() and invaders:
        decision = ai_decisions.get()
        if decision is not None:
            shooter_idx = int(decision) % len(invaders)
            shooter = invaders[shooter_idx]['pos']
            enemy_bullets.append([shooter[0] + ENEMY_SIZE // 2, shooter[1] + ENEMY_SIZE])
    else:
        # Default behavior if no AI decision available
        if invaders:
            shooter = random.choice(invaders)['pos']
            enemy_bullets.append([shooter[0] + ENEMY_SIZE // 2, shooter[1] + ENEMY_SIZE])

def fetch_ai_decision():
    prompt = "Based on the player's position and behavior, decide which invader should fire next. Return the index of the invader (0 to {}).".format(len(invaders) - 1)
    response = fetch_ai_response(prompt)
    match = re.search(r'\b\d+\b', response)
    if match:
        decision = match.group(0)
        return decision
    return None

def fetch_ai_response(prompt):
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={'model': 'gemma:2b-instruct', 'prompt': prompt}
        )
        response.raise_for_status()

        complete_message = ""
        lines = response.text.strip().split('\n')
        for line in lines:
            try:
                data = json.loads(line)
                if data.get('done', False):
                    break
                complete_message += data.get('response', '')
            except json.JSONDecodeError:
                continue

        if not complete_message:
            return "No response available."
        return complete_message.strip()

    except requests.RequestException as e:
        print(f"Error fetching AI response: {e}")
        return "AI service unavailable."

def generate_ai_formation():
    prompt = "Generate a list of positions for enemy invaders in the format [(x1, y1), (x2, y2), ...]. Ensure they are within screen bounds."
    response = fetch_ai_response(prompt)
    positions = []
    try:
        positions = eval(response)
        valid_positions = []
        for pos in positions:
            x, y = pos
            if 0 <= x <= SCREEN_WIDTH - ENEMY_SIZE and 0 <= y <= SCREEN_HEIGHT / 2:
                valid_positions.append([x, y])
        if valid_positions:
            return valid_positions
    except:
        pass
    # Default formation if AI fails
    positions = []
    for row in range(4):
        for col in range(10):
            x = col * (ENEMY_SIZE + 20) + 100
            y = row * (ENEMY_SIZE + 20) + 50
            positions.append([x, y])
    return positions

def adjust_difficulty():
    global difficulty, enemy_speed
    # Increase difficulty based on score
    difficulty = min(1 + (score / 2000), MAX_DIFFICULTY)  # Adjusted divisor from 500 to 2000
    enemy_speed = min(START_ENEMY_SPEED * difficulty, MAX_ENEMY_SPEED)  # Apply maximum speed cap

def ai_assistant_message():
    prompt = "Provide a hint or commentary to help the player improve."
    message = fetch_ai_response(prompt)
    return message

def ai_invader_taunt():
    prompt = "Generate a taunt or message from the invaders to the player."
    message = fetch_ai_response(prompt)
    return message

def ai_special_event():
    global meteor_shower_active, meteor_shower_timer
    if not meteor_shower_active and random.randint(0, 1000) < METEOR_SHOWER_PROBABILITY:
        meteor_shower_active = True
        meteor_shower_timer = METEOR_SHOWER_DURATION

def game_loop():
    global direction, enemy_speed, level, score, invaders, ufo, ufo_timer
    global player_power_ups, power_up_timers, meteors, meteor_shower_active, meteor_shower_timer, player_lives
    global player_speed
    running = True
    clock = pygame.time.Clock()
    frame_count = 0
    assistant_message_timer = 0
    taunt_message_timer = 0
    assistant_message = ""
    taunt_message = ""

    while running:
        screen.fill((0, 0, 0))
        level_text = font.render(f'Level: {level}', True, COLOR_WHITE)
        score_text = font.render(f'Score: {score}', True, COLOR_WHITE)
        screen.blit(level_text, (10, 10))
        screen.blit(score_text, (10, 30))

        if assistant_message_timer > 0:
            assistant_text = font.render(assistant_message, True, COLOR_CYAN)
            screen.blit(assistant_text, (10, 70))
            assistant_message_timer -= 1

        if taunt_message_timer > 0:
            taunt_text = font.render(taunt_message, True, COLOR_RED)
            screen.blit(taunt_text, (10, 90))
            taunt_message_timer -= 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_x:
                    pygame.quit()
                    sys.exit()

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and player_pos[0] > 0:
            player_pos[0] -= player_speed
        if keys[pygame.K_RIGHT] and player_pos[0] < SCREEN_WIDTH - PLAYER_SIZE:
            player_pos[0] += player_speed

        # Shooting logic with power-ups
        shoot_cooldown = 10 if not player_power_ups['rapid_fire'] else 5
        if keys[pygame.K_SPACE] and frame_count % shoot_cooldown == 0:
            if player_power_ups['double_fire']:
                player_bullets.append([player_pos[0] + PLAYER_SIZE // 4, player_pos[1]])
                player_bullets.append([player_pos[0] + 3 * PLAYER_SIZE // 4, player_pos[1]])
            else:
                player_bullets.append([player_pos[0] + PLAYER_SIZE // 2, player_pos[1]])

        player_positions.append(player_pos[0])
        if len(player_positions) > 100:
            player_positions.pop(0)

        update_bullets()
        if frame_count % int(SHOOTING_FREQUENCY / difficulty) == 0:
            threading.Thread(target=ai_controlled_shoot, daemon=True).start()

        update_invaders()
        update_ufo()
        update_power_ups()
        update_meteors()
        ai_special_event()
        adjust_difficulty()
        update_power_up_timers()

        # Get cached assistant message
        if frame_count % 600 == 0:
            try:
                assistant_message = assistant_messages.get_nowait()
            except:
                assistant_message = ""
            assistant_message_timer = 300

        # Get cached taunt message
        if frame_count % 800 == 0:
            try:
                taunt_message = taunt_messages.get_nowait()
            except:
                taunt_message = ""
            taunt_message_timer = 300

        draw_elements()
        pygame.display.flip()
        clock.tick(60)
        frame_count += 1

def update_power_up_timers():
    global player_power_ups, power_up_timers, enemy_speed
    for power_up, active in player_power_ups.items():
        if active:
            power_up_timers[power_up] -= 1
            if power_up_timers[power_up] <= 0:
                player_power_ups[power_up] = False
                # Reset any modified attributes
                if power_up == 'rapid_fire':
                    pass  # Reset handled in shooting logic
                elif power_up == 'invincibility':
                    pass  # Visual indication handled in drawing logic
                elif power_up == 'slow_motion':
                    enemy_speed /= 0.5
                elif power_up == 'score_multiplier':
                    pass

def update_bullets():
    global player_bullets, enemy_bullets, ufo_bullets, score, ufo, power_ups, player_power_ups, player_lives
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
                    points = 10 if not player_power_ups['score_multiplier'] else 20
                    score += points
                    # Random chance to drop a power-up
                    if random.randint(0, 100) < 20:
                        drop_power_up(x, y)
                    break
            # Check collision with UFO
            if ufo:
                x, y = ufo['pos']
                if x <= bullet[0] <= x + UFO_SIZE and y <= bullet[1] <= y + UFO_SIZE:
                    player_bullets.remove(bullet)
                    explosions.append([x + UFO_SIZE // 2, y + UFO_SIZE // 2, EXPLOSION_DURATION])
                    ufo = None
                    points = 50 if not player_power_ups['score_multiplier'] else 100
                    score += points

    # Enemy bullets
    for bullet in enemy_bullets[:]:
        bullet[1] += ENEMY_BULLET_SPEED * difficulty
        if bullet[1] > SCREEN_HEIGHT:
            enemy_bullets.remove(bullet)
        elif player_pos[0] <= bullet[0] <= player_pos[0] + PLAYER_SIZE and player_pos[1] <= bullet[1] <= player_pos[1] + PLAYER_SIZE:
            if player_power_ups['invincibility']:
                enemy_bullets.remove(bullet)
            elif player_power_ups['shield']:
                enemy_bullets.remove(bullet)
                player_power_ups['shield'] = False
            else:
                enemy_bullets.remove(bullet)
                player_lives -= 1
                if player_lives <= 0:
                    show_game_over()

    # UFO bullets
    for bullet in ufo_bullets[:]:
        bullet[1] += (ENEMY_BULLET_SPEED + 2) * difficulty
        if bullet[1] > SCREEN_HEIGHT:
            ufo_bullets.remove(bullet)
        elif player_pos[0] <= bullet[0] <= player_pos[0] + PLAYER_SIZE and player_pos[1] <= bullet[1] <= player_pos[1] + PLAYER_SIZE:
            if player_power_ups['invincibility']:
                ufo_bullets.remove(bullet)
            elif player_power_ups['shield']:
                ufo_bullets.remove(bullet)
                player_power_ups['shield'] = False
            else:
                ufo_bullets.remove(bullet)
                player_lives -= 1
                if player_lives <= 0:
                    show_game_over()

    # Update explosions
    for explosion in explosions[:]:
        explosion[2] -= 1
        if explosion[2] <= 0:
            explosions.remove(explosion)

def drop_power_up(x, y):
    global power_ups
    power_up_types = ['screen_clear', 'double_fire', 'rapid_fire', 'invincibility', 'shield', 'extra_life', 'slow_motion', 'score_multiplier']
    power_up_type = random.choice(power_up_types)
    power_ups.append({'pos': [x, y], 'type': power_up_type})

def update_invaders():
    global invaders, direction, level, enemy_speed, score, difficulty
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
        enemy_speed += LEVEL_CHANGE_INCREASE  # Less aggressive increase
        score += 100
        invaders = initialize_invaders()

def update_ufo():
    global ufo, ufo_timer, ufo_bullets
    if not ufo:
        ufo_timer += 1
        if ufo_timer >= UFO_SPAWN_FREQUENCY:
            ufo = {'pos': [0, 30], 'direction': UFO_SPEED * random.choice([-1, 1])}
            ufo_timer = 0
    else:
        ufo['pos'][0] += ufo['direction']
        if ufo['pos'][0] > SCREEN_WIDTH or ufo['pos'][0] < -UFO_SIZE:
            ufo = None
        else:
            # UFO fires bullets occasionally
            if random.randint(0, 100) < 1:
                ufo_bullets.append([ufo['pos'][0] + UFO_SIZE // 2, ufo['pos'][1] + UFO_SIZE])

def update_power_ups():
    global score, player_power_ups, power_up_timers, player_speed, enemy_speed, player_lives
    for power_up in power_ups[:]:
        power_up['pos'][1] += 2
        x, y = power_up['pos']
        if y > SCREEN_HEIGHT:
            power_ups.remove(power_up)
        elif player_pos[0] <= x <= player_pos[0] + PLAYER_SIZE and player_pos[1] <= y <= player_pos[1] + PLAYER_SIZE:
            power_ups.remove(power_up)
            power_type = power_up['type']
            if power_type == 'screen_clear':
                # Destroy all invaders
                for invader in invaders:
                    invader['explosion_timer'] = EXPLOSION_DURATION
                score += 100
            elif power_type == 'double_fire':
                player_power_ups['double_fire'] = True
                power_up_timers['double_fire'] = POWER_UP_DURATION
            elif power_type == 'rapid_fire':
                player_power_ups['rapid_fire'] = True
                power_up_timers['rapid_fire'] = POWER_UP_DURATION
            elif power_type == 'invincibility':
                player_power_ups['invincibility'] = True
                power_up_timers['invincibility'] = POWER_UP_DURATION
            elif power_type == 'shield':
                player_power_ups['shield'] = True
                power_up_timers['shield'] = POWER_UP_DURATION
            elif power_type == 'extra_life':
                player_lives += 1
            elif power_type == 'slow_motion':
                player_power_ups['slow_motion'] = True
                power_up_timers['slow_motion'] = POWER_UP_DURATION
                enemy_speed *= 0.5
            elif power_type == 'score_multiplier':
                player_power_ups['score_multiplier'] = True
                power_up_timers['score_multiplier'] = POWER_UP_DURATION

def update_meteors():
    global meteors, meteor_shower_active, meteor_shower_timer, player_lives
    if meteor_shower_active:
        meteor_shower_timer -= 1
        if meteor_shower_timer <= 0:
            meteor_shower_active = False
        else:
            if random.randint(0, 100) < METEOR_CREATION_CHANCE:
                x = random.randint(0, SCREEN_WIDTH)
                meteors.append({'pos': [x, 0]})
    for meteor in meteors[:]:
        meteor['pos'][1] += METEOR_FALL_SPEED
        x, y = meteor['pos']
        if y > SCREEN_HEIGHT:
            meteors.remove(meteor)
        elif player_pos[0] <= x <= player_pos[0] + PLAYER_SIZE and player_pos[1] <= y <= player_pos[1] + PLAYER_SIZE:
            if player_power_ups['invincibility']:
                meteors.remove(meteor)
            elif player_power_ups['shield']:
                meteors.remove(meteor)
                player_power_ups['shield'] = False
            else:
                meteors.remove(meteor)
                player_lives -= 1
                if player_lives <= 0:
                    show_game_over()

def initialize_invaders():
    invaders = []
    formation = generate_ai_formation()
    for pos in formation:
        invaders.append({'pos': pos, 'explosion_timer': 0})
    return invaders

# Background threads for fetching AI messages and decisions (same as before)
def background_fetch_assistant_messages():
    while True:
        try:
            message = ai_assistant_message()
            assistant_messages.put(message, timeout=5)
        except Exception as e:
            print(f"Error in background_fetch_assistant_messages: {e}")
            continue

def background_fetch_taunt_messages():
    while True:
        try:
            message = ai_invader_taunt()
            taunt_messages.put(message, timeout=5)
        except Exception as e:
            print(f"Error in background_fetch_taunt_messages: {e}")
            continue

def background_fetch_ai_decisions():
    while True:
        if len(invaders) > 0:
            decision = fetch_ai_decision()
            try:
                ai_decisions.put(decision, timeout=5)
            except:
                pass

# Initialize invaders after defining all functions
invaders = initialize_invaders()

# Start background threads for AI messages and decisions
threading.Thread(target=background_fetch_assistant_messages, daemon=True).start()
threading.Thread(target=background_fetch_taunt_messages, daemon=True).start()
threading.Thread(target=background_fetch_ai_decisions, daemon=True).start()

# Start game loop
game_loop()
