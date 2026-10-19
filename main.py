import math
import random
import array
from pathlib import Path
import pygame

pygame.init()

# -------------------- WINDOW --------------------
WIDTH, HEIGHT = 1000, 700
FPS = 60

display = pygame.display.set_mode((WIDTH, HEIGHT))
screen = pygame.Surface((WIDTH, HEIGHT))
pygame.display.set_caption("XenonBeam | Adaptive Space Shooter")
clock = pygame.time.Clock()

# -------------------- COLORS --------------------
BLACK = (5, 7, 20)
WHITE = (240, 245, 255)
CYAN = (0, 230, 255)
PURPLE = (155, 80, 255)
RED = (255, 75, 95)
YELLOW = (255, 220, 90)
GREEN = (90, 255, 170)
ORANGE = (255, 155, 60)
GREY = (150, 160, 185)

# -------------------- FONTS --------------------
small_font = pygame.font.Font(None, 23)
font = pygame.font.Font(None, 30)
medium_font = pygame.font.Font(None, 42)
large_font = pygame.font.Font(None, 76)

# -------------------- AUDIO --------------------
# Sound effects are synthesized in Python; no external audio files needed.
SOUNDS = {}
AUDIO_ENABLED = True
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
    def make_tone(start_freq, duration, volume=0.22, sweep=0):
        sample_rate = 22050
        samples = array.array("h")
        total = int(sample_rate * duration)
        for i in range(total):
            t = i / sample_rate
            progress = i / max(1, total)
            freq = start_freq + sweep * progress
            envelope = min(1.0, i / 180) * max(0.0, 1 - progress)
            value = int(32767 * volume * envelope * math.sin(2 * math.pi * freq * t))
            samples.append(value)
        return pygame.mixer.Sound(buffer=samples.tobytes())

    SOUNDS = {
        "shoot": make_tone(880, 0.055, 0.12, -300),
        "enemy": make_tone(260, 0.12, 0.18, -170),
        "powerup": make_tone(520, 0.20, 0.18, 650),
        "boss": make_tone(180, 0.65, 0.22, -100),
        "explosion": make_tone(120, 0.35, 0.22, -90),
        "hit": make_tone(150, 0.22, 0.20, -70),
    }
except Exception:
    AUDIO_ENABLED = False

def play_sound(name):
    if AUDIO_ENABLED and name in SOUNDS:
        try:
            SOUNDS[name].play()
        except pygame.error:
            pass

# -------------------- HIGH SCORE --------------------
HIGH_SCORE_FILE = Path(__file__).with_name("xenonbeam_highscore.txt")
def load_high_score():
    try:
        return max(0, int(HIGH_SCORE_FILE.read_text(encoding="utf-8").strip()))
    except (OSError, ValueError):
        return 0

def save_high_score(score):
    try:
        HIGH_SCORE_FILE.write_text(str(score), encoding="utf-8")
    except OSError:
        pass

high_score = load_high_score()

# -------------------- STARFIELD --------------------
stars = [
    [
        random.randrange(WIDTH),
        random.randrange(HEIGHT),
        random.choice([1, 1, 2, 3]),
        random.uniform(35, 120),
    ]
    for _ in range(110)
]


def draw_background(dt):
    screen.fill(BLACK)

    for star in stars:
        star[1] += star[3] * dt

        if star[1] > HEIGHT:
            star[0] = random.randrange(WIDTH)
            star[1] = 0

        brightness = min(255, 110 + star[2] * 45)
        pygame.draw.circle(
            screen,
            (brightness // 2, brightness // 2, brightness),
            (int(star[0]), int(star[1])),
            star[2],
        )


def draw_text(text, font_obj, color, x, y, center=True):
    image = font_obj.render(text, True, color)

    if center:
        rect = image.get_rect(center=(x, y))
    else:
        rect = image.get_rect(topleft=(x, y))

    screen.blit(image, rect)


def draw_ship(x, y, scale=1.0):
    points = [
        (int(x), int(y)),
        (int(x - 24 * scale), int(y + 44 * scale)),
        (int(x), int(y + 33 * scale)),
        (int(x + 24 * scale), int(y + 44 * scale)),
    ]

    pygame.draw.polygon(screen, PURPLE, points)
    pygame.draw.polygon(screen, CYAN, points, 3)
    pygame.draw.ellipse(
        screen,
        WHITE,
        (
            int(x - 5 * scale),
            int(y + 13 * scale),
            int(10 * scale),
            int(14 * scale),
        ),
    )


# -------------------- PLAYER --------------------
class Player:
    def __init__(self):
        self.width = 44
        self.height = 48
        self.x = WIDTH / 2 - self.width / 2
        self.y = HEIGHT - 100
        self.speed = 390

        self.lives = 3
        self.invulnerable_timer = 0

        self.shield_timer = 0
        self.rapid_timer = 0
        self.triple_timer = 0

    @property
    def rect(self):
        return pygame.Rect(
            int(self.x), int(self.y), self.width, self.height
        )

    def move(self, dt):
        keys = pygame.key.get_pressed()

        dx = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(
            keys[pygame.K_LEFT] or keys[pygame.K_a]
        )
        dy = int(keys[pygame.K_DOWN] or keys[pygame.K_s]) - int(
            keys[pygame.K_UP] or keys[pygame.K_w]
        )

        direction = pygame.Vector2(dx, dy)

        if direction.length_squared() > 0:
            direction = direction.normalize()

        self.x += direction.x * self.speed * dt
        self.y += direction.y * self.speed * dt

        self.x = max(0, min(WIDTH - self.width, self.x))
        self.y = max(90, min(HEIGHT - self.height, self.y))

        self.invulnerable_timer = max(0, self.invulnerable_timer - dt)
        self.shield_timer = max(0, self.shield_timer - dt)
        self.rapid_timer = max(0, self.rapid_timer - dt)
        self.triple_timer = max(0, self.triple_timer - dt)

    def draw(self):
        flashing = (
            self.invulnerable_timer > 0
            and int(self.invulnerable_timer * 12) % 2 == 0
        )

        if not flashing:
            draw_ship(self.x + self.width / 2, self.y)

        if self.shield_timer > 0:
            pygame.draw.circle(screen, CYAN, self.rect.center, 34, 3)
            pygame.draw.circle(
                screen, (60, 100, 180), self.rect.center, 39, 1
            )


# -------------------- PLAYER BULLETS --------------------
class Bullet:
    def __init__(self, x, y, vx=0):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.speed = 650
        self.rect = pygame.Rect(int(x - 3), int(y - 10), 6, 16)

    def update(self, dt):
        self.x += self.vx * dt
        self.y -= self.speed * dt
        self.rect.center = (int(self.x), int(self.y))

    def draw(self):
        pygame.draw.rect(screen, CYAN, self.rect, border_radius=3)
        pygame.draw.circle(
            screen, WHITE, (self.rect.centerx, self.rect.top), 2
        )


# -------------------- ENEMIES --------------------
class Enemy:
    def __init__(self, level):
        roll = random.random()

        if level >= 2 and roll < 0.25:
            self.kind = "fast"
            self.size = 25
            self.hp = 1
            self.speed = min(230 + level * 15, 425)
            self.color = ORANGE
        elif level >= 3 and roll < 0.50:
            self.kind = "armored"
            self.size = 44
            self.hp = 3
            self.speed = min(90 + level * 10, 210)
            self.color = PURPLE
        else:
            self.kind = "normal"
            self.size = random.randint(28, 40)
            self.hp = 1
            self.speed = min(130 + level * 17, 355)
            self.color = RED

        self.x = random.randint(0, WIDTH - self.size)
        self.y = -self.size
        self.rect = pygame.Rect(
            int(self.x), int(self.y), self.size, self.size
        )

    def update(self, dt):
        self.y += self.speed * dt
        self.rect.topleft = (int(self.x), int(self.y))

    def draw(self):
        pygame.draw.rect(
            screen, self.color, self.rect, border_radius=8
        )
        pygame.draw.rect(
            screen,
            WHITE if self.kind == "armored" else YELLOW,
            self.rect,
            2,
            border_radius=8,
        )
        pygame.draw.circle(screen, WHITE, self.rect.center, 4)

        if self.kind == "armored":
            draw_text(
                str(self.hp),
                small_font,
                WHITE,
                self.rect.centerx,
                self.rect.centery + 17,
            )


# -------------------- PARTICLE EFFECTS --------------------
class Particle:
    def __init__(self, x, y, color):
        self.x = float(x)
        self.y = float(y)

        angle = random.uniform(0, math.tau)
        speed = random.uniform(60, 260)

        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.color = color
        self.life = random.uniform(0.25, 0.7)
        self.max_life = self.life
        self.size = random.randint(2, 5)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    def draw(self):
        if self.life <= 0:
            return

        radius = max(1, int(self.size * self.life / self.max_life))
        pygame.draw.circle(
            screen,
            self.color,
            (int(self.x), int(self.y)),
            radius,
        )


def create_explosion(particles, x, y, color, count=18):
    for _ in range(count):
        particles.append(Particle(x, y, color))


# -------------------- BOSS PROJECTILES --------------------
class BossProjectile:
    def __init__(self, x, y, target_x, target_y):
        self.x = float(x)
        self.y = float(y)

        direction = pygame.Vector2(target_x - x, target_y - y)

        if direction.length_squared() > 0:
            direction = direction.normalize()

        self.vx = direction.x * 230
        self.vy = direction.y * 230
        self.radius = 7
        self.rect = pygame.Rect(
            int(x - self.radius),
            int(y - self.radius),
            self.radius * 2,
            self.radius * 2,
        )

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.rect.center = (int(self.x), int(self.y))

    def draw(self):
        pygame.draw.circle(screen, RED, self.rect.center, self.radius)
        pygame.draw.circle(screen, YELLOW, self.rect.center, 3)


# -------------------- BOSS --------------------
class Boss:
    def __init__(self, level):
        self.width = 180
        self.height = 90
        self.x = WIDTH / 2 - self.width / 2
        self.y = 100

        self.max_hp = 25 + level * 5
        self.hp = self.max_hp

        self.speed = 150
        self.direction = 1
        self.attack_timer = 1.2
        self.phase = 0

        self.rect = pygame.Rect(
            int(self.x), int(self.y), self.width, self.height
        )

    def update(self, dt):
        self.x += self.speed * self.direction * dt

        if self.x <= 15:
            self.x = 15
            self.direction = 1
        elif self.x + self.width >= WIDTH - 15:
            self.x = WIDTH - self.width - 15
            self.direction = -1

        self.phase += dt
        self.rect.topleft = (int(self.x), int(self.y))

    def draw(self):
        pygame.draw.rect(
            screen, PURPLE, self.rect.inflate(12, 12), border_radius=22
        )
        pygame.draw.rect(
            screen, (35, 20, 75), self.rect, border_radius=18
        )
        pygame.draw.rect(
            screen, CYAN, self.rect, 3, border_radius=18
        )

        eye_y = int(self.y + 35)
        left_eye = (int(self.x + 48), eye_y)
        right_eye = (int(self.x + self.width - 48), eye_y)

        pygame.draw.circle(screen, RED, left_eye, 13)
        pygame.draw.circle(screen, RED, right_eye, 13)
        pygame.draw.circle(screen, WHITE, left_eye, 5)
        pygame.draw.circle(screen, WHITE, right_eye, 5)

        pulse = 5 * math.sin(self.phase * 5)
        pygame.draw.circle(
            screen,
            CYAN,
            (int(self.x + self.width / 2), int(self.y + 60)),
            max(4, int(12 + pulse)),
        )

    def shoot(self, projectiles, player):
        origin_x = self.x + self.width / 2
        origin_y = self.y + self.height

        for offset in (-100, 0, 100):
            projectiles.append(
                BossProjectile(
                    origin_x,
                    origin_y,
                    player.rect.centerx + offset,
                    player.rect.centery,
                )
            )


def draw_boss_health(boss):
    if boss is None:
        return

    bar_width = 440
    bar_height = 18
    x = WIDTH // 2 - bar_width // 2
    y = 88

    pygame.draw.rect(
        screen, (50, 25, 45),
        (x, y, bar_width, bar_height),
        border_radius=6,
    )

    ratio = max(0, boss.hp / boss.max_hp)
    pygame.draw.rect(
        screen, RED,
        (x, y, int(bar_width * ratio), bar_height),
        border_radius=6,
    )
    pygame.draw.rect(
        screen, WHITE,
        (x, y, bar_width, bar_height),
        2,
        border_radius=6,
    )

    draw_text("BOSS", small_font, WHITE, WIDTH // 2, y - 10)


# -------------------- POWER-UPS --------------------
class PowerUp:
    TYPES = ("shield", "rapid", "triple")

    def __init__(self, x, y):
        self.kind = random.choice(self.TYPES)
        self.x = float(x)
        self.y = float(y)
        self.speed = 145
        self.size = 28
        self.rect = pygame.Rect(
            int(x), int(y), self.size, self.size
        )

    @property
    def color(self):
        return {
            "shield": CYAN,
            "rapid": YELLOW,
            "triple": PURPLE,
        }[self.kind]

    @property
    def symbol(self):
        return {
            "shield": "S",
            "rapid": "R",
            "triple": "T",
        }[self.kind]

    def update(self, dt):
        self.y += self.speed * dt
        self.rect.topleft = (int(self.x), int(self.y))

    def draw(self):
        pulse = int(3 * math.sin(pygame.time.get_ticks() / 130))
        radius = self.size // 2 + pulse
        pygame.draw.circle(
            screen, self.color, self.rect.center, radius, 3
        )
        draw_text(
            self.symbol, font, WHITE,
            self.rect.centerx, self.rect.centery
        )


def activate_powerup(player, kind):
    if kind == "shield":
        player.shield_timer = 6.0
    elif kind == "rapid":
        player.rapid_timer = 7.0
    elif kind == "triple":
        player.triple_timer = 7.0


# -------------------- GAME STATE --------------------
def reset_game():
    return {
        "player": Player(),
        "bullets": [],
        "enemies": [],
        "powerups": [],
        "score": 0,
        "spawn_timer": 0,
        "shoot_cooldown": 0,
        "boss": None,
        "boss_projectiles": [],
        "particles": [],
        "boss_levels_done": set(),
        "boss_message_timer": 0,
    }


game = reset_game()
state = "menu"
shake_timer = 0.0
flash_timer = 0.0
menu_time = 0
running = True

# -------------------- MAIN LOOP --------------------
while running:
    dt = min(clock.tick(FPS) / 1000, 0.04)
    menu_time += dt
    draw_background(dt)

    # -------------------- INPUT --------------------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if state == "playing":
                    state = "paused"
                elif state in ("paused", "help"):
                    state = "menu"
                else:
                    running = False

            elif event.key == pygame.K_h:
                if state == "menu":
                    state = "help"
                elif state == "help":
                    state = "menu"

            elif event.key == pygame.K_RETURN:
                if state in ("menu", "game_over"):
                    game = reset_game()
                    state = "playing"
                elif state == "paused":
                    state = "playing"
                elif state == "help":
                    state = "menu"

            elif event.key == pygame.K_p:
                if state == "playing":
                    state = "paused"
                elif state == "paused":
                    state = "playing"

            elif event.key == pygame.K_r and state == "game_over":
                game = reset_game()
                state = "playing"

    # -------------------- START MENU --------------------
    if state == "menu":
        draw_text(
            "XENON", large_font, CYAN,
            WIDTH // 2, 180 + int(5 * math.sin(menu_time * 2))
        )
        draw_text(
            "BEAM", large_font, PURPLE,
            WIDTH // 2, 250 + int(5 * math.sin(menu_time * 2))
        )
        draw_ship(WIDTH // 2, 310, 1.5)

        pygame.draw.rect(
            screen, (18, 28, 60),
            (WIDTH // 2 - 150, 410, 300, 58),
            border_radius=12,
        )
        pygame.draw.rect(
            screen, CYAN,
            (WIDTH // 2 - 150, 410, 300, 58),
            2,
            border_radius=12,
        )
        draw_text(
            "PRESS ENTER TO PLAY", font, WHITE,
            WIDTH // 2, 439
        )
        draw_text(
            "H - HOW TO PLAY", small_font, GREY,
            WIDTH // 2, 505
        )
        draw_text(
            f"BEST SCORE: {high_score}",
            font, YELLOW, WIDTH // 2, 535
        )
        draw_text(
            "SURVIVE. ADAPT. DOMINATE.",
            small_font, CYAN, WIDTH // 2, 585
        )
        draw_text(
            "SOUND EFFECTS ENABLED" if AUDIO_ENABLED else "AUDIO UNAVAILABLE",
            small_font, GREY, WIDTH // 2, 625
        )

    # -------------------- HELP SCREEN --------------------
    elif state == "help":
        draw_text(
            "HOW TO PLAY", large_font, CYAN,
            WIDTH // 2, 140
        )

        instructions = [
            ("WASD / ARROWS", "Move your spaceship"),
            ("SPACE", "Shoot enemies"),
            ("P", "Pause or resume"),
            ("POWER-UPS", "Collect glowing S, R and T orbs"),
            ("S", "Shield: temporary collision protection"),
            ("R", "Rapid fire: shoot faster"),
            ("T", "Triple shot: fire three bullets"),
        ]

        for i, (key, description) in enumerate(instructions):
            y = 225 + i * 47
            draw_text(
                key, font, PURPLE,
                WIDTH // 2 - 300, y, center=False
            )
            draw_text(
                description, small_font, WHITE,
                WIDTH // 2 - 50, y + 4, center=False
            )

        draw_text(
            "PRESS ENTER OR H TO RETURN",
            font, CYAN, WIDTH // 2, 590
        )

    # -------------------- GAMEPLAY --------------------
    elif state in ("playing", "paused", "game_over"):
        player = game["player"]

        if state == "playing":
            player.move(dt)

            level = 1 + game["score"] // 100
            spawn_interval = max(
                0.75 - (level - 1) * 0.045, 0.22
            )

            # Spawn a boss once when reaching each fifth level.
            boss_milestone = (level // 5) * 5
            if level >= 5 and boss_milestone not in game["boss_levels_done"]:
                if game["boss"] is None:
                    game["boss"] = Boss(boss_milestone)
                    game["boss_levels_done"].add(boss_milestone)
                    game["boss_message_timer"] = 2.5
                    play_sound("boss")

            if game["boss_message_timer"] > 0:
                game["boss_message_timer"] = max(
                    0, game["boss_message_timer"] - dt
                )

            # Shooting
            game["shoot_cooldown"] -= dt
            keys = pygame.key.get_pressed()

            if keys[pygame.K_SPACE] and game["shoot_cooldown"] <= 0:
                center_x = player.x + player.width / 2

                if player.triple_timer > 0:
                    game["bullets"].extend([
                        Bullet(center_x, player.y, -170),
                        Bullet(center_x, player.y, 0),
                        Bullet(center_x, player.y, 170),
                    ])
                else:
                    game["bullets"].append(
                        Bullet(center_x, player.y)
                    )

                game["shoot_cooldown"] = (
                    0.09 if player.rapid_timer > 0 else 0.20
                )
                play_sound("shoot")

            # Spawn regular enemies only when no boss is active.
            game["spawn_timer"] += dt
            if game["spawn_timer"] >= spawn_interval:
                game["spawn_timer"] = 0
                if game["boss"] is None:
                    game["enemies"].append(Enemy(level))

            # Update bullets
            for bullet in game["bullets"]:
                bullet.update(dt)

            game["bullets"] = [
                bullet for bullet in game["bullets"]
                if (
                    bullet.rect.bottom > 0
                    and bullet.rect.right > 0
                    and bullet.rect.left < WIDTH
                )
            ]

            # Update regular enemies
            for enemy in game["enemies"]:
                enemy.update(dt)

            # Update boss and its attacks
            boss = game["boss"]
            if boss is not None:
                boss.update(dt)
                boss.attack_timer -= dt

                if boss.attack_timer <= 0:
                    boss.shoot(game["boss_projectiles"], player)
                    boss.attack_timer = max(
                        0.55, 1.25 - level * 0.025
                    )

            for projectile in game["boss_projectiles"]:
                projectile.update(dt)

            game["boss_projectiles"] = [
                projectile
                for projectile in game["boss_projectiles"]
                if (
                    -20 < projectile.rect.centerx < WIDTH + 20
                    and projectile.rect.top < HEIGHT + 20
                )
            ]

            # Update particles
            for particle in game["particles"]:
                particle.update(dt)

            game["particles"] = [
                particle for particle in game["particles"]
                if particle.life > 0
            ]

            # Bullet-enemy collisions
            for enemy in game["enemies"][:]:
                for bullet in game["bullets"][:]:
                    if enemy.rect.colliderect(bullet.rect):
                        game["bullets"].remove(bullet)
                        enemy.hp -= 1

                        if enemy.hp <= 0:
                            game["enemies"].remove(enemy)
                            game["score"] += (
                                30 if enemy.kind == "armored"
                                else 20 if enemy.kind == "fast"
                                else 10
                            )

                            play_sound("enemy")
                            create_explosion(
                                game["particles"],
                                enemy.rect.centerx,
                                enemy.rect.centery,
                                enemy.color,
                                count=18,
                            )

                            if random.random() < 0.24:
                                game["powerups"].append(
                                    PowerUp(
                                        enemy.rect.centerx - 14,
                                        enemy.rect.centery - 14,
                                    )
                                )
                        break

            # Player bullets damage the boss
            boss = game["boss"]
            if boss is not None:
                for bullet in game["bullets"][:]:
                    if boss.rect.colliderect(bullet.rect):
                        game["bullets"].remove(bullet)
                        boss.hp -= 1

                        create_explosion(
                            game["particles"],
                            bullet.x,
                            bullet.y,
                            CYAN,
                            count=3,
                        )

                        if boss.hp <= 0:
                            create_explosion(
                                game["particles"],
                                boss.rect.centerx,
                                boss.rect.centery,
                                PURPLE,
                                count=70,
                            )
                            game["score"] += 250
                            play_sound("explosion")
                            shake_timer = 0.55
                            flash_timer = 0.18
                            game["boss"] = None
                            game["boss_projectiles"].clear()
                            break

            # Update and collect power-ups
            for powerup in game["powerups"]:
                powerup.update(dt)

            for powerup in game["powerups"][:]:
                if powerup.rect.colliderect(player.rect):
                    activate_powerup(player, powerup.kind)
                    play_sound("powerup")
                    game["powerups"].remove(powerup)

            game["powerups"] = [
                powerup for powerup in game["powerups"]
                if powerup.rect.top < HEIGHT
            ]

            # Player collision with regular enemies
            protected = (
                player.shield_timer > 0
                or player.invulnerable_timer > 0
            )

            if not protected:
                for enemy in game["enemies"][:]:
                    if enemy.rect.colliderect(player.rect):
                        game["enemies"].remove(enemy)
                        player.lives -= 1
                        player.invulnerable_timer = 1.5
                        play_sound("hit")
                        shake_timer = 0.22
                        create_explosion(
                            game["particles"],
                            player.rect.centerx,
                            player.rect.centery,
                            RED,
                            count=12,
                        )
                        break

            # Boss projectile collisions
            if (
                player.shield_timer <= 0
                and player.invulnerable_timer <= 0
            ):
                for projectile in game["boss_projectiles"][:]:
                    if projectile.rect.colliderect(player.rect):
                        game["boss_projectiles"].remove(projectile)
                        player.lives -= 1
                        player.invulnerable_timer = 1.5
                        play_sound("hit")
                        shake_timer = 0.22

                        create_explosion(
                            game["particles"],
                            player.rect.centerx,
                            player.rect.centery,
                            RED,
                            count=12,
                        )
                        break

            # Escaped enemies cost a life unless shielded
            for enemy in game["enemies"][:]:
                if enemy.rect.top > HEIGHT:
                    game["enemies"].remove(enemy)

                    if player.shield_timer <= 0:
                        player.lives -= 1
                        player.invulnerable_timer = max(
                            player.invulnerable_timer, 1.0
                        )

            if player.lives <= 0:
                player.lives = 0
                state = "game_over"

        # -------------------- DRAW GAME OBJECTS --------------------
        for bullet in game["bullets"]:
            bullet.draw()

        for enemy in game["enemies"]:
            enemy.draw()

        for powerup in game["powerups"]:
            powerup.draw()

        for projectile in game["boss_projectiles"]:
            projectile.draw()

        for particle in game["particles"]:
            particle.draw()

        if game["boss"] is not None:
            game["boss"].draw()
            draw_boss_health(game["boss"])

        if game["boss_message_timer"] > 0:
            draw_text(
                "WARNING: BOSS INCOMING!",
                medium_font,
                RED,
                WIDTH // 2,
                135,
            )

        player.draw()

        # Save a new record immediately when achieved.
        if game["score"] > high_score:
            high_score = game["score"]
            save_high_score(high_score)

        # -------------------- HUD --------------------
        level = 1 + game["score"] // 100

        pygame.draw.rect(
            screen, (15, 20, 45), (0, 0, WIDTH, 76)
        )
        pygame.draw.line(
            screen, CYAN, (0, 76), (WIDTH, 76), 2
        )

        draw_text(
            f"SCORE {game['score']}", font, WHITE, 105, 38
        )
        draw_text(
            f"LIVES {player.lives}",
            font,
            GREEN if player.lives > 1 else RED,
            WIDTH // 2,
            38,
        )
        draw_text(
            f"LEVEL {level}", font, CYAN, WIDTH - 100, 38
        )

        active = []
        if player.shield_timer > 0:
            active.append(("SHIELD", player.shield_timer, CYAN))
        if player.rapid_timer > 0:
            active.append(("RAPID", player.rapid_timer, YELLOW))
        if player.triple_timer > 0:
            active.append(("TRIPLE", player.triple_timer, PURPLE))

        for i, (name, timer, color) in enumerate(active):
            draw_text(
                f"{name} {timer:.1f}s",
                small_font,
                color,
                100,
                95 + i * 23,
                center=False,
            )

        draw_text(
            "MOVE: WASD / ARROWS   SHOOT: SPACE   PAUSE: P",
            small_font,
            GREY,
            WIDTH // 2,
            HEIGHT - 20,
        )

        # -------------------- PAUSE OVERLAY --------------------
        if state == "paused":
            overlay = pygame.Surface(
                (WIDTH, HEIGHT), pygame.SRCALPHA
            )
            overlay.fill((0, 0, 10, 205))
            screen.blit(overlay, (0, 0))

            draw_text(
                "PAUSED", large_font, CYAN,
                WIDTH // 2, HEIGHT // 2 - 40
            )
            draw_text(
                "PRESS P OR ENTER TO RESUME",
                font, WHITE, WIDTH // 2, HEIGHT // 2 + 25
            )
            draw_text(
                "ESC TO RETURN TO MENU",
                small_font, GREY,
                WIDTH // 2, HEIGHT // 2 + 70
            )

        # -------------------- GAME OVER OVERLAY --------------------
        elif state == "game_over":
            overlay = pygame.Surface(
                (WIDTH, HEIGHT), pygame.SRCALPHA
            )
            overlay.fill((0, 0, 10, 215))
            screen.blit(overlay, (0, 0))

            draw_text(
                "GAME OVER", large_font, RED,
                WIDTH // 2, HEIGHT // 2 - 85
            )
            draw_text(
                f"FINAL SCORE: {game['score']}",
                font, WHITE, WIDTH // 2, HEIGHT // 2 - 20
            )
            draw_text(
                "PRESS ENTER OR R TO RESTART",
                font, CYAN, WIDTH // 2, HEIGHT // 2 + 35
            )
            draw_text(
                "ESC TO QUIT",
                small_font, GREY,
                WIDTH // 2, HEIGHT // 2 + 78
            )

    # Screen shake and brief white flash add impact without changing gameplay.
    shake_x = shake_y = 0
    if shake_timer > 0:
        shake_timer = max(0.0, shake_timer - dt)
        shake_x = random.randint(-5, 5)
        shake_y = random.randint(-4, 4)

    if flash_timer > 0:
        flash_timer = max(0.0, flash_timer - dt)
        flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        flash.fill((180, 220, 255, int(100 * flash_timer / 0.18)))
        screen.blit(flash, (0, 0))

    display.fill(BLACK)
    display.blit(screen, (shake_x, shake_y))
    pygame.display.flip()

pygame.quit()
