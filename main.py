import os
import sys
import pygame
import random
import math



def resource_path(relative_path):
    """Get the correct asset path when running normally or inside PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

def play_next_song():
    global current_track_index, current_song_name, song_text_start_time

    if not music_tracks:
        return

    current_track_index = (current_track_index + 1) % len(music_tracks)
    current_song_name = os.path.splitext(music_tracks[current_track_index])[0]
    song_text_start_time = pygame.time.get_ticks()

    pygame.mixer.music.load(os.path.join(resource_path("assets"), music_tracks[current_track_index]))
    pygame.mixer.music.play()

# --- INITIALIZATION ---
pygame.init()
MUSIC_END_EVENT = pygame.USEREVENT + 1
music_tracks = []
current_track_index = 0
current_song_name = ""
song_text_start_time = 0
song_text_duration = 3500
try:
    pygame.mixer.init()
    music_loaded = False
    try:
        music_folder = resource_path("assets")
        music_tracks = [
            file_name for file_name in os.listdir(music_folder)
            if file_name.lower().endswith((".mp3", ".ogg", ".wav"))
        ]

        random.shuffle(music_tracks)

        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.set_endevent(MUSIC_END_EVENT)

        if music_tracks:
            current_track_index = 0
            current_song_name = os.path.splitext(music_tracks[current_track_index])[0]
            song_text_start_time = pygame.time.get_ticks()

            pygame.mixer.music.load(os.path.join(music_folder, music_tracks[current_track_index]))
            pygame.mixer.music.play()
            music_loaded = True
    except Exception as e:
        print("Failed to load music:", e)
except Exception:
    # Some platforms may not support mixer init in the same way
    music_loaded = False

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("2D Infinite Roguelike")
clock = pygame.time.Clock()

# Initialize Font System for UI text rendering
FONT_PATH = resource_path("assets/fonts/VCR_OSD_MONO_1.001.ttf")
font = pygame.font.Font(FONT_PATH, 24)
small_font = pygame.font.Font(FONT_PATH, 18)
large_font = pygame.font.Font(FONT_PATH, 64)


ESP_COST = 100
WALL_COST = 50
ARROWS_COST = 100
MARKSMAN_COST = 150
SNIPER_COST = 200
SPINNY_SWORD_COST = 500
DOUBLE_BLADE_COST = 1000
QUAD_BLADE_COST = 1500
LASER_COST = 500
DOUBLE_LASER_COST = 500
GOLD_PULSE_COST = 50
GOLD_PULSE_UPGRADE_COST = 200
MAGNET_COST = 200
MAGNET_UPGRADE_COST = 300
STAT_MAX_UPGRADE_COST = 500
STAT_MAX_UPGRADE_AMOUNT = 5
WALL_UPGRADE_1_COST = 250
WALL_UPGRADE_2_COST = 1000
BOSS_SPAWN_EVENTS = [
    (120000, 1.0, 1.0),
    (180000, 2.0, 1.5),
    (210000, 2.0, 5.0),
    (250000, 4.0, 5.0),
    (300000, 4.0, 5.0),
    (310000, 4.5, 5.0),
    (310000, 10.0, 0.5),
]

# --- GAME STATE CONTROL ---
game_state = "PLAYING"  # Can be "PLAYING" or "GAME_OVER"

# --- GAME OBJECTS ---
class Player:
    def __init__(self):
        self.x = 0  # World X coordinate (Infinite map)
        self.y = 0  # World Y coordinate
        self.speed = 5
        self.radius = 15
        self.color = (0, 255, 204) # Teal
        self.arrow_level = 0
        self.blade_level = 0
        self.laser_level = 0
        self.gold_pulse_level = 0
        self.last_arrow_time = 0
        self.magnet_level = 0
        self.last_magnet_time = 0
        self.magnet_cooldown = 6000  # 6 seconds
        self.xp_growth_multiplier = 1.1
        self.xp_growth_decay = 0.8
        self.wall_level = 0
        self.stat_max_levels = {
            "speed": 10,
            "damage": 10,
            "health": 10,
            "regen": 10,
            "attack_size": 10,
            "attack_speed": 10
        }

        # HP Engine Variables
        self.base_max_hp = 100
        self.hp = self.base_max_hp
        
        # Experience/Mana System
        self.max_experience = 1
        self.experience = 0
        
        # Ability Cooldown Tracking
        self.last_shockwave_time = 0
        self.last_slash_time = 0
        self.last_q_attack_time = 0
        self.shockwave_cooldown = 2000  # 2 seconds in milliseconds
        self.slash_cooldown = 300       # 0.3 seconds in milliseconds
        self.q_attack_cooldown = 2000   # 2 seconds in milliseconds
        self.has_active_charge = False
        
        # Stat upgrade system
        self.stat_points = 0
        self.total_stat_points = 0
        self.gold = 0
        self.speed_level = 0
        self.damage_level = 0
        self.health_level = 0
        self.regen_level = 0
        self.attack_speed_level = 0
        self.attack_size_level = 0
        self.shockwave_unlocked = False
        self.wall_attack_unlocked = False
        
        self.last_regen_time = pygame.time.get_ticks()
        
        # Movement Direction Tracking
        self.facing_x = 0
        self.facing_y = -1  # Default facing up

    def get_stat_max(self, stat_name):
        return self.stat_max_levels[stat_name]
    
    def can_buy_stat_max_upgrade(self, stat_name):
        return self.gold >= STAT_MAX_UPGRADE_COST
    
    def buy_stat_max_upgrade(self, stat_name):
        if self.can_buy_stat_max_upgrade(stat_name):
            self.gold -= STAT_MAX_UPGRADE_COST
            self.stat_max_levels[stat_name] += STAT_MAX_UPGRADE_AMOUNT
            return True
        return False

    def get_cooldown_multiplier(self):
        return max(0.5, 1.0 - self.attack_speed_level * 0.05)
    def can_use_magnet(self):
        if self.magnet_level <= 0:
            return False
        current_time = pygame.time.get_ticks()
        return current_time - self.last_magnet_time >= self.magnet_cooldown * self.get_cooldown_multiplier()
    def use_magnet(self):
        if self.can_use_magnet():
            self.last_magnet_time = pygame.time.get_ticks()
            return True
        return False
    def get_arrow_cooldown(self):
        if self.arrow_level == 1:
            base_cooldown = 1000
        elif self.arrow_level == 2:
            base_cooldown = 500
        elif self.arrow_level == 3:
            base_cooldown = 300
        else:
            return None
        
        return base_cooldown * self.get_cooldown_multiplier()

    def get_arrow_damage(self):
        if self.arrow_level == 1:
            return 3
        if self.arrow_level == 2:
            return 4.5
        if self.arrow_level == 3:
            return 9
        return 0

    def get_arrow_speed(self):
        if self.arrow_level == 2:
            return 24
        return 8

    def can_fire_arrow(self):
        if self.arrow_level <= 0:
            return False
        current_time = pygame.time.get_ticks()
        return current_time - self.last_arrow_time >= self.get_arrow_cooldown()

    def use_arrow(self):
        self.last_arrow_time = pygame.time.get_ticks()

    def get_speed_multiplier(self):
        return 1.0 + self.speed_level * 0.1

    def get_damage_multiplier(self):
        return 1.0 + self.damage_level * 0.3

    def get_shockwave_max_radius(self):
        return 250 + self.attack_size_level * 20

    def get_shockwave_count(self):
        if self.attack_size_level >= 8:
            return 4
        if self.attack_size_level >= 5:
            return 3
        if self.attack_size_level >= 2:
            return 2
        return 1

    def get_slash_range(self):
        return 80 + self.attack_size_level * 10

    def get_q_attack_range(self):
        return 220 + self.attack_size_level * 12

    def get_q_attack_arc(self):
        return 80 + self.attack_size_level * 3

    def get_max_hp(self):
        return self.base_max_hp

    def get_health_regen(self):
        return min(10, 1 + self.regen_level)

    def can_upgrade(self):
        return self.stat_points > 0

    def move(self, keys):
        move_x = 0
        move_y = 0
        actual_speed = self.speed * self.get_speed_multiplier()
        
        if keys[pygame.K_UP]:
            move_y -= actual_speed
        if keys[pygame.K_DOWN]:
            move_y += actual_speed
        if keys[pygame.K_LEFT]:
            move_x -= actual_speed
        if keys[pygame.K_RIGHT]:
            move_x += actual_speed
        
        # Update facing direction if moving
        if move_x != 0 or move_y != 0:
            dist = math.sqrt(move_x**2 + move_y**2)
            self.facing_x = move_x / dist
            self.facing_y = move_y / dist
        
        self.x += move_x
        self.y += move_y
    
    def can_use_shockwave(self):
        if not self.shockwave_unlocked:
            return False
        current_time = pygame.time.get_ticks()
        return current_time - self.last_shockwave_time >= self.shockwave_cooldown * self.get_cooldown_multiplier()
    
    def can_use_slash(self):
        current_time = pygame.time.get_ticks()
        return current_time - self.last_slash_time >= self.slash_cooldown * self.get_cooldown_multiplier()
    
    def use_shockwave(self):
        if self.can_use_shockwave():
            self.last_shockwave_time = pygame.time.get_ticks()
            return True
        return False
    
    def use_slash(self):
        if self.can_use_slash():
            self.last_slash_time = pygame.time.get_ticks()
            return True
        return False
    
    def get_shockwave_cooldown_percent(self):
        current_time = pygame.time.get_ticks()
        elapsed = current_time - self.last_shockwave_time
        cooldown = self.shockwave_cooldown * self.get_cooldown_multiplier()
        return min(1.0, elapsed / cooldown)
    
    def get_slash_cooldown_percent(self):
        current_time = pygame.time.get_ticks()
        elapsed = current_time - self.last_slash_time
        cooldown = self.slash_cooldown * self.get_cooldown_multiplier()
        return min(1.0, elapsed / cooldown)
    
    def can_use_q_attack(self):
        if not self.wall_attack_unlocked:
            return False
        current_time = pygame.time.get_ticks()
        return current_time - self.last_q_attack_time >= self.q_attack_cooldown * self.get_cooldown_multiplier()
    
    def use_q_attack(self):
        if self.can_use_q_attack() and not self.has_active_charge:
            self.last_q_attack_time = pygame.time.get_ticks()
            self.has_active_charge = True
            return True
        return False
    
    def get_q_attack_cooldown_percent(self):
        current_time = pygame.time.get_ticks()
        elapsed = current_time - self.last_q_attack_time
        cooldown = self.q_attack_cooldown * self.get_cooldown_multiplier()
        return min(1.0, elapsed / cooldown)

def is_on_screen(item, camera_x, camera_y):
    screen_x = item.x + camera_x
    screen_y = item.y + camera_y
    return 0 <= screen_x <= SCREEN_WIDTH and 0 <= screen_y <= SCREEN_HEIGHT
class EnemyProjectile:
    def __init__(self, x, y, target_x, target_y, damage=5):
        self.x = x
        self.y = y
        self.speed = 7
        self.radius = 4
        self.damage = damage
        self.color = (255, 100, 100)

        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx**2 + dy**2)

        self.dx = (dx / distance) if distance > 0 else 0
        self.dy = (dy / distance) if distance > 0 else 0

    def update(self):
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed

class BigEnemyProjectile:
    def __init__(self, x, y, target_x, target_y, damage=20):
        self.x = x
        self.y = y
        self.speed = 4
        self.radius = 12
        self.color = (100, 120, 255)
        self.damage = damage

        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)

        self.dx = (dx / dist) if dist > 0 else 0
        self.dy = (dy / dist) if dist > 0 else 0

    def update(self):
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed

class PlayerArrow:
    def __init__(self, x, y, target, damage, speed):
        self.x = x
        self.y = y
        self.damage = damage
        self.speed = speed
        self.radius = 5
        self.color = (230, 230, 120)
        self.is_active = True

        dx = target.x - x
        dy = target.y - y
        dist = math.sqrt(dx * dx + dy * dy)

        self.dx = (dx / dist) if dist > 0 else 0
        self.dy = (dy / dist) if dist > 0 else -1

    def update(self):
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed

class SpinningSword:
    def __init__(self, player, angle_offset):
        self.player = player
        self.angle_offset = angle_offset
        self.orbit_radius = 62
        self.base_length = 42
        self.width = 10
        self.damage = 5
        self.hit_cooldown = 350
        self.hit_times = {}

    def get_angle(self):
        spin_speed = 0.008 * (1.0 + self.player.attack_speed_level * 0.08)
        return pygame.time.get_ticks() * spin_speed + self.angle_offset

    def get_length(self):
        return self.base_length + self.player.attack_size_level * 5

    def get_position(self):
        angle = self.get_angle()
        length = self.get_length()
        center_distance = self.orbit_radius + length / 2

        x = self.player.x + math.cos(angle) * center_distance
        y = self.player.y + math.sin(angle) * center_distance
        return x, y

    def get_tip_position(self):
        angle = self.get_angle()
        length = self.get_length()
        tip_distance = self.orbit_radius + length

        x = self.player.x + math.cos(angle) * tip_distance
        y = self.player.y + math.sin(angle) * tip_distance
        return x, y

    def can_hit(self, enemy):
        current_time = pygame.time.get_ticks()
        last_hit = self.hit_times.get(enemy, 0)
        return current_time - last_hit >= self.hit_cooldown

    def mark_hit(self, enemy):
        self.hit_times[enemy] = pygame.time.get_ticks()

class Shockwave:
    def __init__(self, x, y, delay=0, max_radius=250):
        self.x = x
        self.y = y
        self.max_radius = max_radius
        self.current_radius = 0
        self.expansion_speed = 15
        self.alpha = 200
        self.color = (100, 200, 255)  # Light blue
        self.damage = 0.5
        self.is_active = True
        self.delay = delay
        self.spawn_time = pygame.time.get_ticks()
        self.hit_enemies = set()
    
    def update(self):
        current_time = pygame.time.get_ticks()
        if current_time < self.spawn_time + self.delay:
            return
        self.current_radius += self.expansion_speed
        self.alpha = int(200 * (1 - self.current_radius / self.max_radius))
        
        if self.current_radius >= self.max_radius:
            self.is_active = False
    
    def get_knockback_force(self, enemy_x, enemy_y):
        current_time = pygame.time.get_ticks()
        if current_time < self.spawn_time + self.delay:
            return 0
        """Returns knockback force if enemy is in shockwave range"""
        dx = enemy_x - self.x
        dy = enemy_y - self.y
        dist = math.sqrt(dx**2 + dy**2)
        
        if dist <= self.current_radius and dist > 0:
            knockback_strength = 20
            return (dx / dist) * knockback_strength
        return 0

class Slash:
    def __init__(self, player):
        self.player = player
        self.facing_x = player.facing_x
        self.facing_y = player.facing_y
        self.range = player.get_slash_range()
        self.arc_angle = 120  # 120 degree arc
        self.lifetime = 150  # milliseconds
        self.spawn_time = pygame.time.get_ticks()
        self.color = (255, 200, 100)  # Orange
        self.damage = 3
        self.is_active = True
        self.hit_enemies = set()
    
    def update(self):
        current_time = pygame.time.get_ticks()
        if current_time - self.spawn_time > self.lifetime:
            self.is_active = False
    
    def get_alpha(self):
        """Returns alpha value based on lifetime"""
        current_time = pygame.time.get_ticks()
        elapsed = current_time - self.spawn_time
        return int(255 * (1 - elapsed / self.lifetime))
    
    def is_in_range(self, enemy_x, enemy_y):
        """Check if enemy is within slash range and arc"""
        dx = enemy_x - self.player.x
        dy = enemy_y - self.player.y
        dist = math.sqrt(dx**2 + dy**2)
        
        if dist > self.range:
            return False
        
        # Enemies on top of the player always get hit
        if dist == 0:
            return True
        
        # Calculate angle to enemy
        enemy_angle = math.atan2(dy, dx)
        # Calculate facing angle
        facing_angle = math.atan2(self.facing_y, self.facing_x)
        
        # Calculate angle difference
        angle_diff = abs(enemy_angle - facing_angle)
        # Normalize to 0-180
        if angle_diff > math.pi:
            angle_diff = 2 * math.pi - angle_diff
        
        # Check if within arc (120 degrees = 2.094 radians)
        arc_radians = math.radians(self.arc_angle / 2)
        return angle_diff <= arc_radians

class HealItem:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 8
        self.color = (0, 255, 0)  # Green
        self.heal_amount = 25
    
    def is_collected(self, player_x, player_y, player_radius):
        dx = self.x - player_x
        dy = self.y - player_y
        dist = math.sqrt(dx**2 + dy**2)
        return dist < (self.radius + player_radius)

class XPItem:

    def __init__(self, x, y, xp_amount=1):
        self.x = x
        self.y = y
        self.radius = 6
        self.magnetized = False
        self.magnet_start_time = 0
        self.color = (0, 100, 255)  # Blue
        self.xp_amount = xp_amount

        if xp_amount >= 10:
            self.color = (60, 255, 100)  # Green for high-value XP
        elif xp_amount > 1:
            self.color = (150, 50, 200)  # Purple for tank XP
    
    def update(self, player_x, player_y):
        dx = player_x - self.x
        dy = player_y - self.y
        dist = math.sqrt(dx**2 + dy**2)

        if self.magnetized:
            elapsed = pygame.time.get_ticks() - self.magnet_start_time
            pull_speed = 4 + (elapsed / 1000) ** 2 * 60

            if dist > 0:
                self.x += (dx / dist) * min(pull_speed, dist)
                self.y += (dy / dist) * min(pull_speed, dist)
            return

        follow_radius = 150
        follow_speed = 2.5
        if 0 < dist < follow_radius:
            self.x += (dx / dist) * follow_speed
            self.y += (dy / dist) * follow_speed
    
    def is_collected(self, player_x, player_y, player_radius):
        dx = self.x - player_x
        dy = self.y - player_y
        dist = math.sqrt(dx**2 + dy**2)
        return dist < (self.radius + player_radius)

class GoldItem:

    def __init__(self, x, y, gold_amount=1):
        self.x = x
        self.y = y
        self.radius = 7
        self.color = (220, 180, 40)
        self.gold_amount = gold_amount
        self.magnetized = False
        self.magnet_start_time = 0
    def update(self, player_x, player_y):
        dx = player_x - self.x
        dy = player_y - self.y
        dist = math.sqrt(dx**2 + dy**2)

        if self.magnetized:
            elapsed = pygame.time.get_ticks() - self.magnet_start_time
            pull_speed = 4 + (elapsed / 1000) ** 2 * 60

            if dist > 0:
                self.x += (dx / dist) * min(pull_speed, dist)
                self.y += (dy / dist) * min(pull_speed, dist)
            return

        follow_radius = 50
        follow_speed = 2.5
        if 0 < dist < follow_radius:
            self.x += (dx / dist) * follow_speed
            self.y += (dy / dist) * follow_speed

    def is_collected(self, player_x, player_y, player_radius):
        dx = self.x - player_x
        dy = self.y - player_y
        dist = math.sqrt(dx**2 + dy**2)
        return dist < (self.radius + player_radius)


def drop_gold_for_enemy(enemy, gold_items_list):
    if enemy.type == "SPEEDY":
        gold_amount = random.randint(3, 7)
    elif enemy.type == "CHASER":
        gold_amount = random.randint(5, 12)
    else:
        gold_amount = random.randint(10, 30)
    if gold_amount > 0:
        gold_items_list.append(GoldItem(enemy.x, enemy.y, gold_amount))


def drop_xp_for_enemy(enemy, xp_items_list):
    if enemy.type == "BOSS":
        for _ in range(3):
            xp_items_list.append(XPItem(
                enemy.x + random.randint(-25, 25),
                enemy.y + random.randint(-25, 25),
                random.randint(10, 15)
            ))
        return

    if enemy.type == "TANK" and random.random() < 0.1:
        xp_items_list.append(XPItem(enemy.x, enemy.y, random.randint(10, 15)))
        return

    base_amount = 3 if enemy.type == "TANK" else 1
    if enemy.type in ("CHASER", "SPEEDY") and random.random() < 0.1:
        base_amount = 3

    xp_roll = random.random()
    if xp_roll < 0.05:
        xp_amount = base_amount * 3
    elif xp_roll < 0.25:
        xp_amount = base_amount * 2
    else:
        xp_amount = base_amount

    xp_items_list.append(XPItem(enemy.x, enemy.y, xp_amount))


def repel_item_groups(*groups):
    all_items = []
    for group in groups:
        all_items.extend(group)

    for i, item in enumerate(all_items):
        for other in all_items[i + 1:]:
            dx = item.x - other.x
            dy = item.y - other.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist == 0:
                angle = random.uniform(0, math.pi * 2)
                dx = math.cos(angle)
                dy = math.sin(angle)
                dist = 1

            target_distance = item.radius + other.radius + 4
            if dist < target_distance:
                push = (target_distance - dist) * 0.1
                offset_x = dx / dist
                offset_y = dy / dist
                item.x += offset_x * push
                item.y += offset_y * push
                other.x -= offset_x * push
                other.y -= offset_y * push

class WallCharge:
    def __init__(self, player, facing_x, facing_y):
        self.player = player
        self.x = player.x
        self.y = player.y
        self.facing_x = facing_x if (facing_x != 0 or facing_y != 0) else 1
        self.facing_y = facing_y
        dist = math.sqrt(self.facing_x**2 + self.facing_y**2)
        if dist > 0:
            self.facing_x /= dist
            self.facing_y /= dist
        # Wall/charge properties
        self.range = player.get_q_attack_range()
        self.width = 48  # approximate thickness of the wall (outer - inner)
        self.spawn_time = pygame.time.get_ticks()
        self.initial_speed = 8.0
        self.speed = float(self.initial_speed)
        self.fade_duration = 1000  # ms to slow and fade out
        self.alpha = 255
        self.color = (200, 180, 255)
        self.arc_angle = player.get_q_attack_arc()
        # inner radius used to make the wall have thickness
        self.inner_radius = 80
        self.is_active = True
        self.hit_enemies = set()

    def update(self):
        # Move immediately
        self.x += self.facing_x * self.speed
        self.y += self.facing_y * self.speed

        # Calculate elapsed since spawn for fade/deceleration
        elapsed = pygame.time.get_ticks() - self.spawn_time
        t = min(1.0, elapsed / self.fade_duration)
        # Linearly reduce speed to 0 over fade_duration
        self.speed = self.initial_speed * (1.0 - t)
        # Fade alpha over same duration
        self.alpha = int(255 * (1.0 - t))

        if t >= 1.0:
            self.is_active = False

    def is_in_range(self, enemy_x, enemy_y):
        # Sector check (curved wall) centered at the charge position
        dx = enemy_x - self.x
        dy = enemy_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        # within outer radius
        if dist > self.range:
            return False
        # allow very close enemies
        if dist == 0:
            return True
        # angle check
        enemy_angle = math.atan2(dy, dx)
        facing_angle = math.atan2(self.facing_y, self.facing_x)
        angle_diff = abs(enemy_angle - facing_angle)
        if angle_diff > math.pi:
            angle_diff = 2 * math.pi - angle_diff
        arc_radians = math.radians(self.arc_angle / 2)
        if angle_diff > arc_radians:
            return False
        # also ensure within thickness (between inner_radius and range)
        return dist >= self.inner_radius

    def check_collision(self, enemies):
        hit_enemies = []
        for enemy in enemies:
            if enemy not in self.hit_enemies and self.is_in_range(enemy.x, enemy.y):
                hit_enemies.append(enemy)
                self.hit_enemies.add(enemy)
        return hit_enemies

class Enemy:
    def __init__(self, x, y, enemy_type):
        self.x = x
        self.y = y
        self.type = enemy_type
        self.damage = 10
        self.projectile_damage = 0
        self.knockback_x = 0
        self.knockback_y = 0
        self.knockback_friction = 0.88

        if enemy_type == "CHASER":
            self.speed = 2.5
            self.color = (255, 51, 51)
            self.radius = 12
            self.attack_range = 250
            self.is_waiting = False
            self.wait_start_time = 0
            self.hp = 5
            self.damage = 7
            self.projectile_damage = 5

        elif enemy_type == "SPEEDY":
            self.speed = 4.0
            self.color = (255, 153, 0)
            self.radius = 8
            self.hp = 1
            self.damage = 3
            self.projectile_damage = 0

        elif enemy_type == "TANK":
            self.speed = 1.5
            self.color = (80, 80, 200)
            self.radius = 28
            self.attack_range = 400
            self.shoot_cooldown = 900
            self.is_waiting = False
            self.wait_start_time = 0
            self.hp = 20
            self.damage = 20
            self.projectile_damage = 10
        
        elif enemy_type == "BOSS":
            self.speed = 1.0
            self.color = (40, 190, 70)
            self.radius = 55
            self.attack_range = 520
            self.shoot_cooldown = 1400
            self.stomp_cooldown = 3500
            self.last_shot_time = 0
            self.last_stomp_time = 0
            self.hp = 250
            self.damage = 99999999
            self.projectile_damage = 18

    def update_behavior(self, player_x, player_y, enemy_projectiles_list, all_enemies):
        dx = player_x - self.x
        dy = player_y - self.y
        distance = math.sqrt(dx**2 + dy**2)

        move_x = 0
        move_y = 0

        if self.type == "SPEEDY":
            if distance > 0:
                move_x = (dx / distance) * self.speed
                move_y = (dy / distance) * self.speed

        elif self.type == "CHASER":
            if distance > self.attack_range:
                self.is_waiting = False
                if distance > 0:
                    move_x = (dx / distance) * self.speed
                    move_y = (dy / distance) * self.speed
            else:
                current_time = pygame.time.get_ticks()
                if not self.is_waiting:
                    self.is_waiting = True
                    self.wait_start_time = current_time
                elif current_time - self.wait_start_time >= 400:
                    enemy_projectiles_list.append(
                        EnemyProjectile(self.x, self.y, player_x, player_y, self.projectile_damage)
                    )
                    self.wait_start_time = current_time

                min_safe_distance = 100
                if distance < min_safe_distance and distance > 0:
                    move_x = (self.x - player_x) / distance * self.speed
                    move_y = (self.y - player_y) / distance * self.speed

        elif self.type == "TANK":
            if distance > self.attack_range:
                self.is_waiting = False
                if distance > 0:
                    move_x = (dx / distance) * self.speed
                    move_y = (dy / distance) * self.speed
            else:
                current_time = pygame.time.get_ticks()
                if not self.is_waiting:
                    self.is_waiting = True
                    self.wait_start_time = current_time
                elif current_time - self.wait_start_time >= self.shoot_cooldown:
                    enemy_projectiles_list.append(
                        BigEnemyProjectile(self.x, self.y, player_x, player_y, self.projectile_damage)
                    )
                    self.wait_start_time = current_time

                min_safe_distance = 30
                if distance < min_safe_distance and distance > 0:
                    move_x = (self.x - player_x) / distance * self.speed
                    move_y = (self.y - player_y) / distance * self.speed

        elif self.type == "BOSS":
            current_time = pygame.time.get_ticks()

            if distance > 220 and distance > 0:
                move_x = (dx / distance) * self.speed
                move_y = (dy / distance) * self.speed
            
            if distance < self.attack_range and current_time - self.last_shot_time >= self.shoot_cooldown:
                for angle_offset in (-0.25, 0, 0.25):
                    base_angle = math.atan2(dy, dx) + angle_offset
                    target_x = self.x + math.cos(base_angle) * 100
                    target_y = self.y + math.sin(base_angle) * 100
                    enemy_projectiles_list.append(
                        BigEnemyProjectile(self.x, self.y, target_x, target_y, self.projectile_damage)
                    )
                    self.last_shot_time = current_time

            if distance < 180 and current_time - self.last_stomp_time >= self.stomp_cooldown:
                enemy_projectiles_list.append(
                    BigEnemyProjectile(self.x, self.y, player_x, player_y, self.projectile_damage * 2)
                )
                enemy_projectiles_list[-1].radius = 28
                enemy_projectiles_list[-1].speed = 2
                enemy_projectiles_list[-1].color = (80, 255, 120)
                self.last_stomp_time = current_time


        separation_distance = 30
        separation_force = 1.2
        for other in all_enemies:
            if other is self:
                continue

            s_dx = self.x - other.x
            s_dy = self.y - other.y
            s_dist = math.sqrt(s_dx**2 + s_dy**2)

            if 0 < s_dist < separation_distance:
                move_x += (s_dx / s_dist) * separation_force
                move_y += (s_dy / s_dist) * separation_force

        knockback_speed = math.sqrt(self.knockback_x**2 + self.knockback_y**2)

        if knockback_speed > 0.5:
            move_x *= 0.35
            move_y *= 0.35

        self.x += move_x + self.knockback_x
        self.y += move_y + self.knockback_y

        self.knockback_x *= self.knockback_friction
        self.knockback_y *= self.knockback_friction

        if abs(self.knockback_x) < 0.05:
            self.knockback_x = 0
        if abs(self.knockback_y) < 0.05:
            self.knockback_y = 0



# --- ENTITY GENERATION SYSTEM ---
player = Player()
enemies = []
enemy_projectiles = []
shockwaves = []
slashes = []
heal_items = []
xp_items = []
gold_items = []
charges = []
player_arrows = []
sniper_trails = []
spinning_swords = []


# Enemy spawn timing settings
SPAWN_INTERVAL_BASE = 1500

ENEMY_STAT_SCALING_INTERVAL = 10000
ENEMY_STAT_SCALING_FACTOR = 1.05

SPAWN_INTERVAL_SCALING_INTERVAL = 1000
SPAWN_INTERVAL_SCALING_FACTOR = 0.98
MIN_SPAWN_INTERVAL = 250

TANK_SPAWN_DELAY = 20000

spawn_start_time = pygame.time.get_ticks()
last_spawn_time = spawn_start_time
boss_spawn_index = 0

def get_enemy_stat_scale():
    elapsed = pygame.time.get_ticks() - spawn_start_time
    steps = elapsed // ENEMY_STAT_SCALING_INTERVAL
    return ENEMY_STAT_SCALING_FACTOR ** steps


def get_spawn_interval_scale():
    elapsed = pygame.time.get_ticks() - spawn_start_time
    steps = elapsed // SPAWN_INTERVAL_SCALING_INTERVAL
    return SPAWN_INTERVAL_SCALING_FACTOR ** steps

def spawn_enemy_offscreen():
    angle = random.uniform(0, math.pi * 2)
    spawn_distance = max(SCREEN_WIDTH, SCREEN_HEIGHT) / 1.3
    spawn_x = player.x + math.cos(angle) * spawn_distance
    spawn_y = player.y + math.sin(angle) * spawn_distance
    
    roll = random.random()
    elapsed = pygame.time.get_ticks() - spawn_start_time
    if elapsed >= TANK_SPAWN_DELAY and player.total_stat_points >= 3 and roll < 0.18:
        enemy_type = "TANK"
    elif roll < 0.6:
        enemy_type = "CHASER"
    else:
        enemy_type = "SPEEDY"

    enemy = Enemy(spawn_x, spawn_y, enemy_type)

    stat_scale = get_enemy_stat_scale()
    enemy.hp *= stat_scale
    enemy.damage *= stat_scale
    enemy.projectile_damage *= stat_scale

    enemies.append(enemy)

def spawn_boss_offscreen(hp_multiplier=1.0, damage_multiplier=1.0):
    global boss_spawn_index
    angle = random.uniform(0, math.pi * 2)
    spawn_distance = max(SCREEN_WIDTH, SCREEN_HEIGHT) / 1.1
    spawn_x = player.x + math.cos(angle) * spawn_distance
    spawn_y = player.y + math.sin(angle) * spawn_distance

    boss = Enemy(spawn_x, spawn_y, "BOSS")
    boss.hp *= hp_multiplier
    boss.damage *= damage_multiplier
    boss.projectile_damage *= damage_multiplier
    enemies.append(boss)

def set_spinning_swords_for_level():
    spinning_swords.clear()

    if player.blade_level == 1:
        offsets = [0]
    elif player.blade_level == 2:
        offsets = [0, math.pi]
    elif player.blade_level == 3:
        offsets = [0, math.pi / 2, math.pi, math.pi * 1.5]
    else:
        offsets = []

    for offset in offsets:
        spinning_swords.append(SpinningSword(player, offset))

def reset_game():
    global player, enemies, enemy_projectiles, game_state, shockwaves, slashes, heal_items, xp_items, gold_items, charges, player_arrows, sniper_trails, spinning_swords, spawn_start_time, last_spawn_time, boss_spawn_index
    player = Player()
    enemies = []
    enemy_projectiles = []
    shockwaves = []
    slashes = []
    heal_items = []
    xp_items = []
    gold_items = []
    charges = []
    player_arrows = []
    sniper_trails = []
    spinning_swords = []
    game_state = "PLAYING"
    spawn_start_time = pygame.time.get_ticks()
    last_spawn_time = spawn_start_time
    boss_spawn_index = 0
    try:
        if music_loaded:
            pygame.mixer.music.play()
    except Exception:
        pass

# --- MAIN RUN LOOP ---
running = True
while running:
    clock.tick(60)
    mouse_pos = pygame.mouse.get_pos()
    stat_panel_x = 20
    button_x = stat_panel_x + 10
    button_width = 220
    button_height = 24
    button_start_y = SCREEN_HEIGHT - 194

    speed_upgrade_rect = pygame.Rect(button_x, button_start_y, button_width, button_height)
    damage_upgrade_rect = pygame.Rect(button_x, button_start_y + 30, button_width, button_height)
    health_upgrade_rect = pygame.Rect(button_x, button_start_y + 60, button_width, button_height)
    regen_upgrade_rect = pygame.Rect(button_x, button_start_y + 90, button_width, button_height)
    attack_size_upgrade_rect = pygame.Rect(button_x, button_start_y + 120, button_width, button_height)
    attack_speed_upgrade_rect = pygame.Rect(button_x, button_start_y + 150, button_width, button_height)

    max_button_width = 58
    max_button_x = button_x + button_width + 8

    speed_max_rect = pygame.Rect(max_button_x, button_start_y, max_button_width, button_height)
    damage_max_rect = pygame.Rect(max_button_x, button_start_y + 30, max_button_width, button_height)
    health_max_rect = pygame.Rect(max_button_x, button_start_y + 60, max_button_width, button_height)
    regen_max_rect = pygame.Rect(max_button_x, button_start_y + 90, max_button_width, button_height)
    attack_size_max_rect = pygame.Rect(max_button_x, button_start_y + 120, max_button_width, button_height)
    attack_speed_max_rect = pygame.Rect(max_button_x, button_start_y + 150, max_button_width, button_height)

    shop_box_size = 40
    shop_start_x = SCREEN_WIDTH - 20 - shop_box_size
    shop_start_y = 20
    esp_box_rect = pygame.Rect(shop_start_x, shop_start_y, shop_box_size, shop_box_size)
    wall_box_rect = pygame.Rect(shop_start_x, shop_start_y + shop_box_size + 20, shop_box_size, shop_box_size)
    arrow_box_rect = pygame.Rect(shop_start_x - 90, shop_start_y + (shop_box_size + 20) * 2, 130, shop_box_size)
    magnet_box_rect = pygame.Rect(shop_start_x - 90, shop_start_y + (shop_box_size + 20) * 3, 130, shop_box_size)
    sword_box_rect = pygame.Rect(shop_start_x - 90, shop_start_y + (shop_box_size + 20) * 4, 130, shop_box_size)
    
    # 1. ENGINE INPUT EVENTS
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == MUSIC_END_EVENT:
            play_next_song()
            
        if game_state == "PLAYING":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1 and player.stat_points > 0 and player.speed_level < player.get_stat_max("speed"):
                    player.speed_level += 1
                    player.stat_points -= 1

                elif event.key == pygame.K_2 and player.stat_points > 0 and player.damage_level < player.get_stat_max("damage"):
                    player.damage_level += 1
                    player.stat_points -= 1

                elif event.key == pygame.K_3 and player.stat_points > 0 and player.health_level < player.get_stat_max("health"):
                    player.health_level += 1
                    player.base_max_hp += 20
                    player.hp = min(player.hp + 20, player.get_max_hp())
                    player.stat_points -= 1

                elif event.key == pygame.K_4 and player.stat_points > 0 and player.regen_level < player.get_stat_max("regen"):
                    player.regen_level += 1
                    player.stat_points -= 1

                elif event.key == pygame.K_5 and player.stat_points > 0 and player.attack_size_level < player.get_stat_max("attack_size"):
                    player.attack_size_level += 1
                    player.stat_points -= 1

                elif event.key == pygame.K_6 and player.stat_points > 0 and player.attack_speed_level < player.get_stat_max("attack_speed"):
                    player.attack_speed_level += 1
                    player.stat_points -= 1
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if sword_box_rect.collidepoint(event.pos):
                    if player.blade_level == 0 and player.gold >= SPINNY_SWORD_COST:
                        player.gold -= SPINNY_SWORD_COST
                        player.blade_level = 1
                        set_spinning_swords_for_level()
                    elif player.blade_level == 1 and player.gold >= DOUBLE_BLADE_COST:
                        player.gold -= DOUBLE_BLADE_COST
                        player.blade_level = 2
                        set_spinning_swords_for_level()
                    elif player.blade_level == 2 and player.gold >= QUAD_BLADE_COST:
                        player.gold -= QUAD_BLADE_COST
                        player.blade_level = 3
                        set_spinning_swords_for_level()
                if speed_upgrade_rect.collidepoint(event.pos) and player.stat_points > 0 and player.speed_level < player.get_stat_max("speed"):
                    player.speed_level += 1
                    player.stat_points -= 1
                if damage_upgrade_rect.collidepoint(event.pos) and player.stat_points > 0 and player.damage_level < player.get_stat_max("damage"):
                    player.damage_level += 1
                    player.stat_points -= 1
                if health_upgrade_rect.collidepoint(event.pos) and player.stat_points > 0 and player.health_level < player.get_stat_max("health"):
                    player.health_level += 1
                    player.base_max_hp += 20
                    player.hp = min(player.hp + 20, player.get_max_hp())
                    player.stat_points -= 1
                if regen_upgrade_rect.collidepoint(event.pos) and player.stat_points > 0 and player.regen_level < player.get_stat_max("regen"):
                    player.regen_level += 1
                    player.stat_points -= 1
                if attack_size_upgrade_rect.collidepoint(event.pos) and player.stat_points > 0 and player.attack_size_level < player.get_stat_max("attack_size"):
                    player.attack_size_level += 1
                    player.stat_points -= 1
                if attack_speed_upgrade_rect.collidepoint(event.pos) and player.stat_points > 0 and player.attack_speed_level < player.get_stat_max("attack_speed"):
                    player.attack_speed_level += 1
                    player.stat_points -= 1
                if magnet_box_rect.collidepoint(event.pos):
                    if player.magnet_level == 0 and player.gold >= MAGNET_COST:
                        player.gold -= MAGNET_COST
                        player.magnet_level = 1
                    elif player.magnet_level == 1 and player.gold >= MAGNET_UPGRADE_COST:
                        player.gold -= MAGNET_UPGRADE_COST
                        player.magnet_level = 2
                if esp_box_rect.collidepoint(event.pos) and not player.shockwave_unlocked and player.gold >= ESP_COST:
                    player.gold -= ESP_COST
                    player.shockwave_unlocked = True
                if wall_box_rect.collidepoint(event.pos):
                    if player.wall_level == 0 and player.gold >= WALL_COST:
                        player.gold -= WALL_COST
                        player.wall_level = 1
                        player.wall_attack_unlocked = True
                    elif player.wall_level == 1 and player.gold >= WALL_UPGRADE_1_COST:
                        player.gold -= WALL_UPGRADE_1_COST
                        player.wall_level = 2
                    elif player.wall_level == 2 and player.gold >= WALL_UPGRADE_2_COST:
                        player.gold -= WALL_UPGRADE_2_COST
                        player.wall_level = 3
                if arrow_box_rect.collidepoint(event.pos):
                    if player.arrow_level == 0 and player.gold >= ARROWS_COST:
                        player.gold -= ARROWS_COST
                        player.arrow_level = 1
                    elif player.arrow_level == 1 and player.gold >= MARKSMAN_COST:
                        player.gold -= MARKSMAN_COST
                        player.arrow_level = 2
                    elif player.arrow_level == 2 and player.gold >= SNIPER_COST:
                        player.gold -= SNIPER_COST
                        player.arrow_level = 3
                if speed_max_rect.collidepoint(event.pos):
                    player.buy_stat_max_upgrade("speed")
                if damage_max_rect.collidepoint(event.pos):
                    player.buy_stat_max_upgrade("damage")
                if health_max_rect.collidepoint(event.pos):
                    player.buy_stat_max_upgrade("health")
                if regen_max_rect.collidepoint(event.pos):
                    player.buy_stat_max_upgrade("regen")
                if attack_size_max_rect.collidepoint(event.pos):
                    player.buy_stat_max_upgrade("attack_size")
                if attack_speed_max_rect.collidepoint(event.pos):
                    player.buy_stat_max_upgrade("attack_speed")

        elif game_state == "GAME_OVER":
            if event.type == pygame.MOUSEBUTTONDOWN:
                restart_btn = pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 20, 200, 50)
                if restart_btn.collidepoint(mouse_pos):
                    reset_game()

    # 2. RUNTIME LOGIC CALCULATIONS
    if game_state == "PLAYING":
        current_time = pygame.time.get_ticks()
        for sword in spinning_swords:
            base_x = player.x + math.cos(sword.get_angle()) * sword.orbit_radius
            base_y = player.y + math.sin(sword.get_angle()) * sword.orbit_radius
            tip_x, tip_y = sword.get_tip_position()

            for enemy in enemies[:]:
                blade_dx = tip_x - base_x
                blade_dy = tip_y - base_y
                blade_len_sq = blade_dx * blade_dx + blade_dy * blade_dy

                if blade_len_sq == 0:
                    continue

                t = ((enemy.x - base_x) * blade_dx + (enemy.y - base_y) * blade_dy) / blade_len_sq
                t = max(0, min(1, t))

                closest_x = base_x + blade_dx * t
                closest_y = base_y + blade_dy * t

                dx = enemy.x - closest_x
                dy = enemy.y - closest_y
                dist = math.sqrt(dx * dx + dy * dy)

                if dist < enemy.radius + sword.width / 2 and sword.can_hit(enemy):
                    sword.mark_hit(enemy)
                    enemy.hp -= sword.damage * player.get_damage_multiplier()

                    if enemy.hp <= 0:
                        if random.random() < 0.1:
                            heal_items.append(HealItem(enemy.x, enemy.y))
                        else:
                            drop_xp_for_enemy(enemy, xp_items)
                        drop_gold_for_enemy(enemy, gold_items)
                        enemies.remove(enemy)
        elapsed_since_start = current_time - spawn_start_time
        if boss_spawn_index < len(BOSS_SPAWN_EVENTS):
            boss_spawn_time, boss_hp_mult, boss_damage_mult = BOSS_SPAWN_EVENTS[boss_spawn_index]
            if elapsed_since_start >= boss_spawn_time:
                spawn_boss_offscreen(boss_hp_mult, boss_damage_mult)
                boss_spawn_index += 1
        for trail in sniper_trails[:]:
            if current_time - trail["spawn_time"] >= trail["duration"]:
                sniper_trails.remove(trail)  
        spawn_interval_scale = get_spawn_interval_scale()
        current_spawn_interval = max(MIN_SPAWN_INTERVAL, int(SPAWN_INTERVAL_BASE * spawn_interval_scale))
        if current_time - last_spawn_time >= current_spawn_interval:
            spawn_enemy_offscreen()
            last_spawn_time = current_time

        keys = pygame.key.get_pressed()
        player.move(keys)

        # Handle ability inputs
        if keys[pygame.K_e]:
            if player.use_shockwave():
                wave_count = player.get_shockwave_count()
                for i in range(wave_count):
                    shockwaves.append(Shockwave(player.x, player.y, delay=i * 200, max_radius=player.get_shockwave_max_radius()))
        if keys[pygame.K_r]:
            if player.use_magnet():
                camera_x = SCREEN_WIDTH // 2 - player.x
                camera_y = SCREEN_HEIGHT // 2 - player.y
                current_time = pygame.time.get_ticks()

                for item in xp_items + gold_items:
                    if player.magnet_level >= 2 or is_on_screen(item, camera_x, camera_y):
                        item.magnetized = True
                        item.magnet_start_time = current_time
        if keys[pygame.K_SPACE]:
            if player.use_slash():
                slashes.append(Slash(player))
        
        if keys[pygame.K_q]:
            if player.use_q_attack():
                forward_x = player.facing_x
                forward_y = player.facing_y

                directions = [(forward_x, forward_y)]

                if player.wall_level >= 2:
                    directions.append((-forward_x, -forward_y))

                if player.wall_level >= 3:
                    directions.append((-forward_y, forward_x))
                    directions.append((forward_y, -forward_x))

                for dir_x, dir_y in directions:
                    charges.append(WallCharge(player, dir_x, dir_y))
        if player.can_fire_arrow() and enemies:
            nearest_enemy = min(
                enemies,
                key=lambda enemy: (enemy.x - player.x) ** 2 + (enemy.y - player.y) ** 2
            )

            player.use_arrow()

            if player.arrow_level == 3:
                sniper_trails.append({
                    "start_x": player.x,
                    "start_y": player.y,
                    "end_x": nearest_enemy.x,
                    "end_y": nearest_enemy.y,
                    "spawn_time": pygame.time.get_ticks(),
                    "duration": 100
                })

                nearest_enemy.hp -= player.get_arrow_damage()
                if nearest_enemy.hp <= 0:
                    if random.random() < 0.1:
                        heal_items.append(HealItem(nearest_enemy.x, nearest_enemy.y))
                    else:
                        drop_xp_for_enemy(nearest_enemy, xp_items)
                    drop_gold_for_enemy(nearest_enemy, gold_items)
                    enemies.remove(nearest_enemy)
            else:
                player_arrows.append(
                    PlayerArrow(
                        player.x,
                        player.y,
                        nearest_enemy,
                        player.get_arrow_damage(),
                        player.get_arrow_speed()
                    )
                )
        # Update shockwaves and apply knockback
        for shockwave in shockwaves[:]:
            shockwave.update()
            if not shockwave.is_active:
                shockwaves.remove(shockwave)
            else:
                # Apply knockback to enemies once per target
                for enemy in enemies[:]:
                    dx = enemy.x - shockwave.x
                    dy = enemy.y - shockwave.y
                    dist = math.sqrt(dx**2 + dy**2)

                    if dist <= shockwave.current_radius and dist > 0 and enemy not in shockwave.hit_enemies:
                        shockwave.hit_enemies.add(enemy)
                        enemy.hp -= shockwave.damage
                        if enemy.hp <= 0:
                            if random.random() < 0.1:
                                heal_items.append(HealItem(enemy.x, enemy.y))
                            else:
                                drop_xp_for_enemy(enemy, xp_items)
                            drop_gold_for_enemy(enemy, gold_items)
                            enemies.remove(enemy)
                            continue
                        dx = enemy.x - shockwave.x
                        dy = enemy.y - shockwave.y
                        dist = math.sqrt(dx**2 + dy**2)

                        if dist > 0:
                            knockback_force = 28
                            enemy.knockback_x += (dx / dist) * knockback_force
                            enemy.knockback_y += (dy / dist) * knockback_force

        # Update slashes and check hits
        for slash in slashes[:]:
            slash.update()
            if not slash.is_active:
                slashes.remove(slash)
            else:
                # Check enemy hits
                for enemy in enemies[:]:
                    if enemy not in slash.hit_enemies and slash.is_in_range(enemy.x, enemy.y):
                        slash.hit_enemies.add(enemy)
                        enemy.hp -= slash.damage * player.get_damage_multiplier()
                        if enemy.hp <= 0:
                            if random.random() < 0.1:  # 10% chance for heal
                                heal_items.append(HealItem(enemy.x, enemy.y))
                            else:  # Always drop XP
                                drop_xp_for_enemy(enemy, xp_items)
                            drop_gold_for_enemy(enemy, gold_items)
                            enemies.remove(enemy)

        # Update charges and check hits
        for charge in charges[:]:
            charge.update()
            if not charge.is_active:
                charges.remove(charge)
                if not charges:
                    player.has_active_charge = False
            else:
                # Check enemy collisions
                hit_enemies = charge.check_collision(enemies)
                for enemy in hit_enemies:
                    enemy.hp -= 5 * player.get_damage_multiplier()
                    if enemy.hp <= 0:
                        if random.random() < 0.1:  # 10% chance for heal
                            heal_items.append(HealItem(enemy.x, enemy.y))
                        else:  # Always drop XP
                            drop_xp_for_enemy(enemy, xp_items)
                        drop_gold_for_enemy(enemy, gold_items)
                        enemies.remove(enemy)

        # Update and check enemy vectors
        for enemy in enemies[:]:
            enemy.update_behavior(player.x, player.y, enemy_projectiles, enemies)
            
            # Contact calculation check (Body Collision)
            dx = enemy.x - player.x
            dy = enemy.y - player.y
            dist = math.sqrt(dx**2 + dy**2)
            if dist < (player.radius + enemy.radius):
                player.hp -= enemy.damage
                # Drop items
                if random.random() < 0.1:  # 10% chance for heal
                    heal_items.append(HealItem(enemy.x, enemy.y))
                else:  # Always drop XP
                    drop_xp_for_enemy(enemy, xp_items)
                drop_gold_for_enemy(enemy, gold_items)
                enemies.remove(enemy) 

        # Update projectile trajectory systems
        for proj in enemy_projectiles[:]:
            proj.update()
            
            # Hit check calculations
            dx = proj.x - player.x
            dy = proj.y - player.y
            dist = math.sqrt(dx**2 + dy**2)
            if dist < (player.radius + proj.radius):
                player.hp -= getattr(proj, "damage", 5)
                enemy_projectiles.remove(proj)
            elif math.sqrt((proj.x - player.x)**2 + (proj.y - player.y)**2) > 1500:
                enemy_projectiles.remove(proj)
        for arrow in player_arrows[:]:
            arrow.update()

            for enemy in enemies[:]:
                dx = arrow.x - enemy.x
                dy = arrow.y - enemy.y
                dist = math.sqrt(dx**2 + dy**2)

                if dist < arrow.radius + enemy.radius:
                    enemy.hp -= arrow.damage
                    arrow.is_active = False

                    if enemy.hp <= 0:
                        if random.random() < 0.1:
                            heal_items.append(HealItem(enemy.x, enemy.y))
                        else:
                            drop_xp_for_enemy(enemy, xp_items)
                        drop_gold_for_enemy(enemy, gold_items)
                        enemies.remove(enemy)
                    break

            if not arrow.is_active:
                player_arrows.remove(arrow)
            elif math.sqrt((arrow.x - player.x) ** 2 + (arrow.y - player.y) ** 2) > 1500:
                player_arrows.remove(arrow)
        # Collect heal items
        for heal_item in heal_items[:]:
            if heal_item.is_collected(player.x, player.y, player.radius):
                player.hp = min(player.get_max_hp(), player.hp + heal_item.heal_amount)
                heal_items.remove(heal_item)

        # Move XP items toward player when nearby
        for xp_item in xp_items:
            xp_item.update(player.x, player.y)

        # Move gold items toward player when nearby
        for gold_item in gold_items:
            gold_item.update(player.x, player.y)

        # Avoid item overlap by gently pushing collectibles apart
        repel_item_groups(heal_items, xp_items, gold_items)

        # Regenerate HP every second
        current_time = pygame.time.get_ticks()
        if current_time - player.last_regen_time >= 1000:
            player.last_regen_time += 1000
            player.hp = min(player.get_max_hp(), player.hp + player.get_health_regen())

        # Collect XP items
        for xp_item in xp_items[:]:
            if xp_item.is_collected(player.x, player.y, player.radius) or (xp_item.magnetized and pygame.time.get_ticks() - xp_item.magnet_start_time >= 1000):
                player.experience += xp_item.xp_amount
                while player.experience >= player.max_experience:
                    player.experience -= player.max_experience
                    player.stat_points += 1
                    player.total_stat_points += 1
                    player.max_experience = math.ceil(player.max_experience * player.xp_growth_multiplier)
                    player.xp_growth_multiplier = 1.0 + (player.xp_growth_multiplier - 1.0) * player.xp_growth_decay
                xp_items.remove(xp_item)

        # Collect gold itemsD
        for gold_item in gold_items[:]:
            if gold_item.is_collected(player.x, player.y, player.radius) or (gold_item.magnetized and pygame.time.get_ticks() - gold_item.magnet_start_time >= 1000):
                player.gold += gold_item.gold_amount
                gold_items.remove(gold_item)

        # Monitor lifecycle conditions
        if player.hp <= 0:
            player.hp = 0
            game_state = "GAME_OVER"
            try:
                if music_loaded:
                    pygame.mixer.music.pause()
            except Exception:
                pass

    # 3. GRAPHICS CANVAS RENDERING
    screen.fill((34, 34, 34)) 

    # Dynamic camera offset coordinate tracking math
    camera_x = SCREEN_WIDTH // 2 - player.x
    camera_y = SCREEN_HEIGHT // 2 - player.y

    # Calculate repeating infinite grid positions
    grid_size = 100
    start_x = int((-camera_x // grid_size) * grid_size)
    end_x = start_x + SCREEN_WIDTH + grid_size
    start_y = int((-camera_y // grid_size) * grid_size)
    end_y = start_y + SCREEN_HEIGHT + grid_size

    for x in range(start_x, end_x, grid_size):
        pygame.draw.line(screen, (50, 50, 50), (x + camera_x, 0), (x + camera_x, SCREEN_HEIGHT))
    for y in range(start_y, end_y, grid_size):
        pygame.draw.line(screen, (50, 50, 50), (0, y + camera_y), (SCREEN_WIDTH, y + camera_y))

    # Project engine coordinate items via camera spaces
    for proj in enemy_projectiles:
        pygame.draw.circle(screen, proj.color, (int(proj.x + camera_x), int(proj.y + camera_y)), proj.radius)

    # Draw shockwaves
    for shockwave in shockwaves:
        surface = pygame.Surface((shockwave.current_radius * 2, shockwave.current_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(surface, (*shockwave.color, shockwave.alpha), (shockwave.current_radius, shockwave.current_radius), shockwave.current_radius, 3)
        screen.blit(surface, (int(shockwave.x + camera_x - shockwave.current_radius), int(shockwave.y + camera_y - shockwave.current_radius)))

    # Draw slashes
    for slash in slashes:
        alpha = slash.get_alpha()
        if alpha > 0:
            # Draw a fan/arc shape for the slash
            slash_pos_x = int(slash.player.x + camera_x)
            slash_pos_y = int(slash.player.y + camera_y)
            
            # Calculate the two edge angles of the slash arc
            facing_angle = math.atan2(slash.facing_y, slash.facing_x)
            half_arc = math.radians(slash.arc_angle / 2)
            
            start_angle = facing_angle - half_arc
            end_angle = facing_angle + half_arc
            
            # Draw multiple lines to create a fan effect
            points = []
            for i in range(int(slash.arc_angle) + 1):
                angle = start_angle + (i / slash.arc_angle) * (end_angle - start_angle)
                x = slash_pos_x + math.cos(angle) * slash.range
                y = slash_pos_y + math.sin(angle) * slash.range
                points.append((x, y))
            
            # Draw the fan shape using thicker lines
            for i in range(len(points) - 1):
                pygame.draw.line(screen, (*slash.color, alpha), points[i], points[i + 1], 8)

    # Draw heal items
    for heal_item in heal_items:
        pygame.draw.circle(screen, heal_item.color, (int(heal_item.x + camera_x), int(heal_item.y + camera_y)), heal_item.radius)

    # Draw XP items
    for xp_item in xp_items:
        pygame.draw.circle(screen, xp_item.color, (int(xp_item.x + camera_x), int(xp_item.y + camera_y)), xp_item.radius)

    # Draw Arrows
    for arrow in player_arrows:
        pygame.draw.circle(
            screen,
            arrow.color,
            (int(arrow.x + camera_x), int(arrow.y + camera_y)),
            arrow.radius
        )
    for trail in sniper_trails:
        age = pygame.time.get_ticks() - trail["spawn_time"]
        alpha = max(0, 255 - int(255 * (age / trail["duration"])))

        trail_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        start_pos = (
            int(trail["start_x"] + camera_x),
            int(trail["start_y"] + camera_y)
        )
        end_pos = (
            int(trail["end_x"] + camera_x),
            int(trail["end_y"] + camera_y)
        )

        pygame.draw.line(trail_surface, (255, 245, 150, alpha), start_pos, end_pos, 4)
        pygame.draw.line(trail_surface, (255, 255, 255, alpha), start_pos, end_pos, 1)

        screen.blit(trail_surface, (0, 0))
    # Draw gold items
    for gold_item in gold_items:
        pygame.draw.circle(screen, gold_item.color, (int(gold_item.x + camera_x), int(gold_item.y + camera_y)), gold_item.radius)
        gold_text = small_font.render(str(gold_item.gold_amount), True, (255, 255, 255))
        gold_text_rect = gold_text.get_rect(center=(int(gold_item.x + camera_x), int(gold_item.y + camera_y)))
        screen.blit(gold_text, gold_text_rect)

    # Draw charges as curved walls (fan segment with inner radius)
    for charge in charges:
        alpha = max(0, min(255, int(charge.alpha)))
        cx = charge.x + camera_x
        cy = charge.y + camera_y
        facing_angle = math.atan2(charge.facing_y, charge.facing_x)
        half_arc = math.radians(charge.arc_angle / 2)
        start_angle = facing_angle - half_arc
        end_angle = facing_angle + half_arc
        segments = max(6, int(charge.arc_angle))

        outer_pts = []
        inner_pts = []
        for i in range(segments + 1):
            t = i / segments
            angle = start_angle + t * (end_angle - start_angle)
            ox = cx + math.cos(angle) * charge.range
            oy = cy + math.sin(angle) * charge.range
            ix = cx + math.cos(angle) * charge.inner_radius
            iy = cy + math.sin(angle) * charge.inner_radius
            outer_pts.append((ox, oy))
            inner_pts.append((ix, iy))

        polygon = outer_pts + inner_pts[::-1]
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(s, (*charge.color, alpha), polygon)
        screen.blit(s, (0, 0))

    for enemy in enemies:
        enemy_pos = (int(enemy.x + camera_x), int(enemy.y + camera_y))
        pygame.draw.circle(screen, enemy.color, enemy_pos, enemy.radius)
        hp_display = max(0.0, enemy.hp)
        hp_text = small_font.render(f"{hp_display:.1f}", True, (255, 255, 255))
        hp_rect = hp_text.get_rect(center=enemy_pos)
        screen.blit(hp_text, hp_rect)

    # Output static centered display anchor for player circle
    pygame.draw.circle(screen, player.color, (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), player.radius)
    eye_offset = 7
    eye_radius = 3
    eye_spread = 5

    facing_angle = math.atan2(player.facing_y, player.facing_x)
    side_x = math.cos(facing_angle + math.pi / 2)
    side_y = math.sin(facing_angle + math.pi / 2)

    eye_center_x = SCREEN_WIDTH // 2 + player.facing_x * eye_offset
    eye_center_y = SCREEN_HEIGHT // 2 + player.facing_y * eye_offset

    left_eye = (
        int(eye_center_x + side_x * eye_spread),
        int(eye_center_y + side_y * eye_spread)
    )
    right_eye = (
        int(eye_center_x - side_x * eye_spread),
        int(eye_center_y - side_y * eye_spread)
    )

    pygame.draw.circle(screen, (10, 20, 20), left_eye, eye_radius)
    pygame.draw.circle(screen, (10, 20, 20), right_eye, eye_radius)
        # --- CANVAS OVERLAY UI ENGINE ---
    if game_state == "PLAYING":
        # HP Bar
        bar_width = 400
        bar_height = 25
        bar_x = (SCREEN_WIDTH - bar_width) // 2
        bar_y = SCREEN_HEIGHT - 50        
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height))
        hp_percent = max(0, player.hp / player.get_max_hp())
        fill_width = int(bar_width * hp_percent)
        pygame.draw.rect(screen, (255, 75, 75), (bar_x, bar_y, fill_width, bar_height))
        pygame.draw.rect(screen, (255, 255, 255), (bar_x, bar_y, bar_width, bar_height), 2)
        
        # XP Bar
        xp_bar_width = 400
        xp_bar_height = 15
        xp_bar_x = (SCREEN_WIDTH - xp_bar_width) // 2
        xp_bar_y = SCREEN_HEIGHT - 75
        
        pygame.draw.rect(screen, (40, 40, 40), (xp_bar_x, xp_bar_y, xp_bar_width, xp_bar_height))
        xp_percent = max(0, player.experience / player.max_experience)
        xp_fill_width = int(xp_bar_width * xp_percent)
        pygame.draw.rect(screen, (0, 100, 255), (xp_bar_x, xp_bar_y, xp_fill_width, xp_bar_height))
        pygame.draw.rect(screen, (100, 150, 255), (xp_bar_x, xp_bar_y, xp_bar_width, xp_bar_height), 1)

        # Stat upgrade button layout
        stat_panel_x = 20
        button_width = 220
        button_height = 24
        button_x = stat_panel_x + 10
        button_start_y = SCREEN_HEIGHT - 194

        stat_text = font.render(f"Stat Points: {player.stat_points}", True, (255, 255, 255))
        screen.blit(stat_text, (button_x, button_start_y - 34))
        gold_text = font.render(f"Gold: {player.gold}", True, (255, 215, 0))
        gold_text_x = SCREEN_WIDTH - 20 - gold_text.get_width()
        gold_text_y = shop_start_y - 24
        screen.blit(gold_text, (gold_text_x, gold_text_y))

        speed_upgrade_rect = pygame.Rect(button_x, button_start_y, button_width, button_height)
        damage_upgrade_rect = pygame.Rect(button_x, button_start_y + 30, button_width, button_height)
        health_upgrade_rect = pygame.Rect(button_x, button_start_y + 60, button_width, button_height)
        regen_upgrade_rect = pygame.Rect(button_x, button_start_y + 90, button_width, button_height)
        attack_size_upgrade_rect = pygame.Rect(button_x, button_start_y + 120, button_width, button_height)
        attack_speed_upgrade_rect = pygame.Rect(button_x, button_start_y + 150, button_width, button_height)
        speed_ready = player.can_upgrade() and player.speed_level < player.get_stat_max("speed")
        damage_ready = player.can_upgrade() and player.damage_level < player.get_stat_max("damage")
        health_ready = player.can_upgrade() and player.health_level < player.get_stat_max("health")
        regen_ready = player.can_upgrade() and player.regen_level < player.get_stat_max("regen")
        attack_size_ready = player.can_upgrade() and player.attack_size_level < player.get_stat_max("attack_size")
        attack_speed_ready = player.can_upgrade() and player.attack_speed_level < player.get_stat_max("attack_speed")
        attack_speed_button_color = (100, 180, 255) if attack_speed_ready else (70, 70, 100)

        speed_button_color = (100, 180, 255) if speed_ready else (70, 70, 100)
        damage_button_color = (100, 180, 255) if damage_ready else (70, 70, 100)
        health_button_color = (100, 180, 255) if health_ready else (70, 70, 100)
        regen_button_color = (100, 180, 255) if regen_ready else (70, 70, 100)
        attack_size_button_color = (100, 180, 255) if attack_size_ready else (70, 70, 100)

        pygame.draw.rect(screen, speed_button_color, speed_upgrade_rect)
        pygame.draw.rect(screen, damage_button_color, damage_upgrade_rect)
        pygame.draw.rect(screen, health_button_color, health_upgrade_rect)
        pygame.draw.rect(screen, regen_button_color, regen_upgrade_rect)
        pygame.draw.rect(screen, attack_size_button_color, attack_size_upgrade_rect)
        pygame.draw.rect(screen, attack_speed_button_color, attack_speed_upgrade_rect)


        pygame.draw.rect(screen, (255, 255, 255), speed_upgrade_rect, 1)
        pygame.draw.rect(screen, (255, 255, 255), damage_upgrade_rect, 1)
        pygame.draw.rect(screen, (255, 255, 255), health_upgrade_rect, 1)
        pygame.draw.rect(screen, (255, 255, 255), regen_upgrade_rect, 1)
        pygame.draw.rect(screen, (255, 255, 255), attack_size_upgrade_rect, 1)
        pygame.draw.rect(screen, (255, 255, 255), attack_speed_upgrade_rect, 1)

        # Gold Increase Max Stat boxes
        stat_max_buttons = [
            (speed_max_rect, "speed"),
            (damage_max_rect, "damage"),
            (health_max_rect, "health"),
            (regen_max_rect, "regen"),
            (attack_size_max_rect, "attack_size"),
            (attack_speed_max_rect, "attack_speed"),
        ]
        
        for rect, stat_name in stat_max_buttons:
            color = (180, 145, 40) if player.can_buy_stat_max_upgrade(stat_name) else (90, 75, 35)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (255, 235, 150), rect, 1)
            label = small_font.render("+5", True, (255, 255, 255))
            screen.blit(label, label.get_rect(center=rect.center))

        # Draw swords
        for sword in spinning_swords:
            angle = sword.get_angle()
            length = sword.get_length()

            base_x = player.x + math.cos(angle) * sword.orbit_radius
            base_y = player.y + math.sin(angle) * sword.orbit_radius
            tip_x = player.x + math.cos(angle) * (sword.orbit_radius + length)
            tip_y = player.y + math.sin(angle) * (sword.orbit_radius + length)

            base_screen = (int(base_x + camera_x), int(base_y + camera_y))
            tip_screen = (int(tip_x + camera_x), int(tip_y + camera_y))

            pygame.draw.line(screen, (225, 225, 240), base_screen, tip_screen, sword.width)
            pygame.draw.line(screen, (255, 255, 255), base_screen, tip_screen, 2)

            guard_angle = angle + math.pi / 2
            guard_half = 9
            guard_a = (
                int(base_x + math.cos(guard_angle) * guard_half + camera_x),
                int(base_y + math.sin(guard_angle) * guard_half + camera_y)
            )
            guard_b = (
                int(base_x - math.cos(guard_angle) * guard_half + camera_x),
                int(base_y - math.sin(guard_angle) * guard_half + camera_y)
            )
            pygame.draw.line(screen, (170, 150, 95), guard_a, guard_b, 4)
        # Draw sword shop UI
        if player.blade_level == 0:
            sword_label_text = "Orbit Swords"
            sword_price_text = f"{SPINNY_SWORD_COST}g"
        elif player.blade_level == 1:
            sword_label_text = "Double Swords"
            sword_price_text = f"{DOUBLE_BLADE_COST}g"
        elif player.blade_level == 2:
            sword_label_text = "Quad Swords"
            sword_price_text = f"{QUAD_BLADE_COST}g"
        else:
            sword_label_text = "Quad"
            sword_price_text = "Owned"

        sword_color = (80, 180, 120) if player.blade_level == 3 else (120, 120, 120)
        pygame.draw.rect(screen, sword_color, sword_box_rect)
        pygame.draw.rect(screen, (255, 255, 255), sword_box_rect, 1)

        sword_label = small_font.render(sword_label_text, True, (255, 255, 255))
        screen.blit(sword_label, sword_label.get_rect(center=sword_box_rect.center))

        sword_price = small_font.render(
            sword_price_text,
            True,
            (255, 215, 0) if player.blade_level < 3 else (180, 255, 180)
        )
        screen.blit(
            sword_price,
            (
                sword_box_rect.x + sword_box_rect.width // 2 - sword_price.get_width() // 2,
                sword_box_rect.y + sword_box_rect.height + 4
            )
        )
        # Draw shop purchase boxes

        # ESP
        esp_color = (120, 120, 120) if not player.shockwave_unlocked else (80, 180, 120)
        pygame.draw.rect(screen, esp_color, esp_box_rect)
        pygame.draw.rect(screen, (255, 255, 255), esp_box_rect, 1)

        esp_label = small_font.render("ESP", True, (255, 255, 255))
        screen.blit(esp_label, esp_label.get_rect(center=esp_box_rect.center))

        esp_price = small_font.render(f"{ESP_COST}g", True, (255, 215, 0))
        if player.shockwave_unlocked:
            esp_price = small_font.render("Owned", True, (180, 255, 180))

        screen.blit(
            esp_price,
            (
                esp_box_rect.x + esp_box_rect.width // 2 - esp_price.get_width() // 2,
                esp_box_rect.y + esp_box_rect.height + 4
            )
        )

        # Wall
        if player.wall_level == 0:
            wall_label_text = "Wall"
            wall_price_text = f"{WALL_COST}g"
        elif player.wall_level == 1:
            wall_label_text = "Wall II"
            wall_price_text = f"{WALL_UPGRADE_1_COST}g"
        elif player.wall_level == 2:
            wall_label_text = "Wall III"
            wall_price_text = f"{WALL_UPGRADE_2_COST}g"
        else:
            wall_label_text = "Wall III"
            wall_price_text = "Owned"

        wall_color = (80, 180, 120) if player.wall_level == 3 else (120, 120, 120)
        pygame.draw.rect(screen, wall_color, wall_box_rect)
        pygame.draw.rect(screen, (255, 255, 255), wall_box_rect, 1)

        wall_label = small_font.render(wall_label_text, True, (255, 255, 255))
        screen.blit(wall_label, wall_label.get_rect(center=wall_box_rect.center))

        wall_price = small_font.render(
            wall_price_text,
            True,
            (255, 215, 0) if player.wall_level < 3 else (180, 255, 180)
        )
        screen.blit(
            wall_price,
            (
                wall_box_rect.x + wall_box_rect.width // 2 - wall_price.get_width() // 2,
                wall_box_rect.y + wall_box_rect.height + 4
            )
        )

        speed_label = small_font.render(f"1 Speed {player.speed_level}/{player.get_stat_max('speed')}", True, (255, 255, 255))
        screen.blit(speed_label, (speed_upgrade_rect.x + 8, speed_upgrade_rect.y + 3))
        damage_label = small_font.render(f"2 Damage {player.damage_level}/{player.get_stat_max('damage')}", True, (255, 255, 255))
        screen.blit(damage_label, (damage_upgrade_rect.x + 8, damage_upgrade_rect.y + 3))
        health_label = small_font.render(f"3 Health {player.health_level}/{player.get_stat_max('health')}", True, (255, 255, 255))
        screen.blit(health_label, (health_upgrade_rect.x + 8, health_upgrade_rect.y + 3))
        regen_label = small_font.render(f"4 Regen {player.regen_level}/{player.get_stat_max('regen')}", True, (255, 255, 255))
        screen.blit(regen_label, (regen_upgrade_rect.x + 8, regen_upgrade_rect.y + 3))
        attack_size_label = small_font.render(f"5 Atk Size {player.attack_size_level}/{player.get_stat_max('attack_size')}", True, (255, 255, 255))
        screen.blit(attack_size_label, (attack_size_upgrade_rect.x + 8, attack_size_upgrade_rect.y + 3))
        attack_speed_label = small_font.render(f"6 Atk Speed {player.attack_speed_level}/{player.get_stat_max('attack_speed')}", True, (255, 255, 255))
        screen.blit(attack_speed_label, (attack_speed_upgrade_rect.x + 8, attack_speed_upgrade_rect.y + 3))
        
        if player.arrow_level == 0:
            arrow_label_text = "Arrows"
            arrow_price_text = f"{ARROWS_COST}g"
        elif player.arrow_level == 1:
            arrow_label_text = "Marksman"
            arrow_price_text = f"{MARKSMAN_COST}g"
        elif player.arrow_level == 2:
            arrow_label_text = "Sniper"
            arrow_price_text = f"{SNIPER_COST}g"
        else:
            arrow_label_text = "Sniper"
            arrow_price_text = "Owned"

        arrow_color = (80, 180, 120) if player.arrow_level == 3 else (120, 120, 120)
        pygame.draw.rect(screen, arrow_color, arrow_box_rect)
        pygame.draw.rect(screen, (255, 255, 255), arrow_box_rect, 1)

        arrow_label = small_font.render(arrow_label_text, True, (255, 255, 255))
        screen.blit(arrow_label, arrow_label.get_rect(center=arrow_box_rect.center))

        arrow_price = small_font.render(arrow_price_text, True, (255, 215, 0) if player.arrow_level < 3 else (180, 255, 180))
        screen.blit(
            arrow_price,
            (
                arrow_box_rect.x + arrow_box_rect.width // 2 - arrow_price.get_width() // 2,
                arrow_box_rect.y + arrow_box_rect.height + 4
            )
        )
        if player.magnet_level == 0:
            magnet_label_text = "Magnet"
            magnet_price_text = f"{MAGNET_COST}g"
        elif player.magnet_level == 1:
            magnet_label_text = "Magnet II"
            magnet_price_text = f"{MAGNET_UPGRADE_COST}g"
        else:
            magnet_label_text = "Magnet II"
            magnet_price_text = "Owned"

        magnet_color = (80, 180, 120) if player.magnet_level == 2 else (120, 120, 120)
        pygame.draw.rect(screen, magnet_color, magnet_box_rect)
        pygame.draw.rect(screen, (255, 255, 255), magnet_box_rect, 1)

        magnet_label = small_font.render(magnet_label_text, True, (255, 255, 255))
        screen.blit(magnet_label, magnet_label.get_rect(center=magnet_box_rect.center))

        magnet_price = small_font.render(
            magnet_price_text,
            True,
            (255, 215, 0) if player.magnet_level < 2 else (180, 255, 180)
        )
        screen.blit(
            magnet_price,
            (
                magnet_box_rect.x + magnet_box_rect.width // 2 - magnet_price.get_width() // 2,
                magnet_box_rect.y + magnet_box_rect.height + 4
            )
        )
        # Draw ability cooldown indicators
        cooldown_box_size = 40
        cooldown_spacing = 50
        cooldown_start_x = 20
        cooldown_start_y = 20
        
        # Shockwave (E) cooldown
        shockwave_ready = player.can_use_shockwave()
        shockwave_color = (100, 200, 255) if shockwave_ready else (60, 100, 150)
        pygame.draw.rect(screen, shockwave_color, (cooldown_start_x, cooldown_start_y, cooldown_box_size, cooldown_box_size))
        pygame.draw.rect(screen, (255, 255, 255), (cooldown_start_x, cooldown_start_y, cooldown_box_size, cooldown_box_size), 2)
        
        # Draw cooldown overlay
        if not shockwave_ready:
            cooldown_percent = player.get_shockwave_cooldown_percent()
            overlay_height = int(cooldown_box_size * (1 - cooldown_percent))
            pygame.draw.rect(screen, (20, 20, 20), (cooldown_start_x, cooldown_start_y, cooldown_box_size, overlay_height))
        
        e_text = font.render("E", True, (255, 255, 255))
        e_text_rect = e_text.get_rect(center=(cooldown_start_x + cooldown_box_size // 2, cooldown_start_y + cooldown_box_size // 2))
        screen.blit(e_text, e_text_rect)
        
        # Slash (Space) cooldown
        slash_ready = player.can_use_slash()
        slash_color = (255, 200, 100) if slash_ready else (150, 100, 60)
        pygame.draw.rect(screen, slash_color, (cooldown_start_x + cooldown_spacing, cooldown_start_y, cooldown_box_size, cooldown_box_size))
        pygame.draw.rect(screen, (255, 255, 255), (cooldown_start_x + cooldown_spacing, cooldown_start_y, cooldown_box_size, cooldown_box_size), 2)
        
        # Draw cooldown overlay
        if not slash_ready:
            cooldown_percent = player.get_slash_cooldown_percent()
            overlay_height = int(cooldown_box_size * (1 - cooldown_percent))
            pygame.draw.rect(screen, (20, 20, 20), (cooldown_start_x + cooldown_spacing, cooldown_start_y, cooldown_box_size, overlay_height))
        
        space_text = font.render("_", True, (255, 255, 255))
        space_text_rect = space_text.get_rect(center=(cooldown_start_x + cooldown_spacing + cooldown_box_size // 2, cooldown_start_y + cooldown_box_size // 2))
        screen.blit(space_text, space_text_rect)
        
        # Boomerang (Q) cooldown
        q_ready = player.can_use_q_attack()
        q_color = (150, 100, 255) if q_ready else (90, 60, 150)
        pygame.draw.rect(screen, q_color, (cooldown_start_x + cooldown_spacing * 2, cooldown_start_y, cooldown_box_size, cooldown_box_size))
        pygame.draw.rect(screen, (255, 255, 255), (cooldown_start_x + cooldown_spacing * 2, cooldown_start_y, cooldown_box_size, cooldown_box_size), 2)
        
        # Draw cooldown overlay
        if not q_ready:
            cooldown_percent = player.get_q_attack_cooldown_percent()
            overlay_height = int(cooldown_box_size * (1 - cooldown_percent))
            pygame.draw.rect(screen, (20, 20, 20), (cooldown_start_x + cooldown_spacing * 2, cooldown_start_y, cooldown_box_size, overlay_height))
        
        q_text = font.render("Q", True, (255, 255, 255))
        q_text_rect = q_text.get_rect(center=(cooldown_start_x + cooldown_spacing * 2 + cooldown_box_size // 2, cooldown_start_y + cooldown_box_size // 2))
        screen.blit(q_text, q_text_rect)
        # Magnet (R) cooldown
        if player.magnet_level > 0:
            magnet_x = cooldown_start_x + cooldown_spacing * 3

            magnet_ready = player.can_use_magnet()
            magnet_color = (255, 215, 80) if magnet_ready else (130, 100, 50)

            pygame.draw.rect(screen, magnet_color, (magnet_x, cooldown_start_y, cooldown_box_size, cooldown_box_size))
            pygame.draw.rect(screen, (255, 255, 255), (magnet_x, cooldown_start_y, cooldown_box_size, cooldown_box_size), 2)

            if not magnet_ready:
                current_time = pygame.time.get_ticks()
                elapsed = current_time - player.last_magnet_time
                cooldown_percent = min(1.0, elapsed / (player.magnet_cooldown * player.get_cooldown_multiplier()))
                overlay_height = int(cooldown_box_size * (1 - cooldown_percent))
                pygame.draw.rect(screen, (20, 20, 20), (magnet_x, cooldown_start_y, cooldown_box_size, overlay_height))

            r_text = font.render("R", True, (255, 255, 255))
            r_text_rect = r_text.get_rect(center=(magnet_x + cooldown_box_size // 2, cooldown_start_y + cooldown_box_size // 2))
            screen.blit(r_text, r_text_rect)

    elif game_state == "GAME_OVER":
        dim_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        dim_overlay.set_alpha(150)
        dim_overlay.fill((0, 0, 0))
        screen.blit(dim_overlay, (0, 0))
        
        death_text = large_font.render("YOU DIED", True, (255, 50, 50))
        text_rect = death_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
        screen.blit(death_text, text_rect)
        
        restart_btn = pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 20, 200, 50)
        btn_color = (100, 100, 100) if restart_btn.collidepoint(mouse_pos) else (70, 70, 70)
        pygame.draw.rect(screen, btn_color, restart_btn)
        pygame.draw.rect(screen, (255, 255, 255), restart_btn, 2)
        
        btn_text = font.render("Restart", True, (255, 255, 255))
        btn_text_rect = btn_text.get_rect(center=restart_btn.center)
        screen.blit(btn_text, btn_text_rect)

    if current_song_name:
        elapsed = pygame.time.get_ticks() - song_text_start_time

        slide_in_duration = 1200
        hold_duration = 3500
        slide_out_duration = 900
        total_duration = slide_in_duration + hold_duration + slide_out_duration

        if elapsed < total_duration:
            song_surface = font.render(current_song_name, True, (255, 255, 255))

            target_x = SCREEN_WIDTH - song_surface.get_width() - 50
            offscreen_x = SCREEN_WIDTH + 20
            y = SCREEN_HEIGHT - 110

            if elapsed < slide_in_duration:
                t = elapsed / slide_in_duration
                eased_t = math.sin(t * math.pi / 2)
                x = offscreen_x + (target_x - offscreen_x) * eased_t

            elif elapsed < slide_in_duration + hold_duration:
                x = target_x

            else:
                t = (elapsed - slide_in_duration - hold_duration) / slide_out_duration
                eased_t = 1 - math.cos(t * math.pi / 2)
                x = target_x + (offscreen_x - target_x) * eased_t

            screen.blit(song_surface, (int(x), int(y)))

    pygame.display.flip()

pygame.quit()