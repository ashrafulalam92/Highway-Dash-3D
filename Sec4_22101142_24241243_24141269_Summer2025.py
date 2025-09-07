from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import time
import random

# ===== HIGHWAY DASH 3D - Fixed Game Configuration =====
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800

# Game States
MENU = 0
RACING = 1
PAUSED = 2
FINISHED = 3
GAME_COMPLETE = 5
CUSTOM_RACE_MENU = 6

# Global variables
game_state = MENU
race_start_time = 0
last_time = time.time()

# Night mode only
is_night_mode = False

# Custom race settings
custom_laps = 1
custom_difficulty = 1  # 1=Easy, 2=Medium, 3=Hard

# Game features
coins_collected = 0
current_level = 1
max_level = 5
first_person_view = False
races_won = 0
current_lap = 1
total_laps = 1

# Track Configuration
ROAD_WIDTH = 400
ROAD_LENGTH = 3000 + (current_level * 2000)
FINISH_LINE_POSITION = ROAD_LENGTH - 200

# Physics Constants
FRICTION = 0.95
AIR_RESISTANCE = 0.98
MAX_SPEED_LIMIT = 40

# Camera settings
camera_distance = 200
camera_height = 100

# Coin positions on road
coin_positions = []

# Auto restart settings
AUTO_RESTART_SECONDS = 3.0
game_complete_time = None

def generate_collectibles():
    """Generate coins on the road"""
    global coin_positions
    coin_positions = []
    
    y_pos = 200
    while y_pos < ROAD_LENGTH - 500:
        x_pos = random.uniform(-ROAD_WIDTH/3, ROAD_WIDTH/3)
        coin_positions.append([x_pos, y_pos, 10, True])
        y_pos += random.uniform(200, 500)

def detect_car_collision(car1, car2):
    """Detect collision between two cars"""
    dx = car1.x - car2.x
    dy = car1.y - car2.y
    distance = math.sqrt(dx**2 + dy**2)
    collision_distance = 40
    return distance < collision_distance

class Car:
    def __init__(self, position, color, is_player=False):
        self.x, self.y, self.z = position
        self.velocity_x = 0
        self.velocity_y = 0
        self.rotation = 0
        self.speed = 0
        self.max_speed = 18 if is_player else 15
        self.acceleration_power = 1.2
        self.braking_power = 2.0
        self.steering_power = 3.0
        self.color = color
        self.is_player = is_player
        self.finished = False
        self.lap_time = 0
        self.race_time = 0
        self.crashed = False
        self.laps_completed = 0
        
    def update(self, dt):
        global coins_collected, current_lap
        
        if self.crashed:
            return
        
        # Regular physics only
        self.velocity_x *= AIR_RESISTANCE
        self.velocity_y *= AIR_RESISTANCE
        
        # Update position
        self.x += self.velocity_x * dt * 60
        self.y += self.velocity_y * dt * 60
        
        # Calculate current speed
        self.speed = math.sqrt(self.velocity_x**2 + self.velocity_y**2)
        
        # Coin collection for player
        if self.is_player:
            self.collect_coins()
        
        # Keep car on road (boundary collision)
        if abs(self.x) > ROAD_WIDTH / 2 - 20:
            self.velocity_x *= -0.3
            self.speed *= 0.5
            if self.x > 0:
                self.x = ROAD_WIDTH / 2 - 20
            else:
                self.x = -ROAD_WIDTH / 2 + 20
        
        # Check finish line and lap completion for ALL cars
        if self.y >= FINISH_LINE_POSITION and not self.finished:
            self.laps_completed += 1
            
            if self.laps_completed >= total_laps:
                self.finished = True
                self.race_time = time.time() - race_start_time
            else:
                # Reset position for next lap
                if self.is_player:
                    self.y = 50
                    current_lap = self.laps_completed + 1
                else:
                    # AI cars also reset for multiple laps
                    self.y = random.uniform(50, 150)
    
    def collect_coins(self):
        global coins_collected
        
        for coin in coin_positions:
            if coin[3]:
                distance = math.sqrt((self.x - coin[0])**2 + (self.y - coin[1])**2)
                if distance < 30:
                    coin[3] = False
                    coins_collected += 1
    
    def accelerate(self):
        if not self.crashed and self.speed < self.max_speed:
            self.velocity_y += self.acceleration_power
    
    def brake(self):
        if not self.crashed and self.speed > 0.1:
            self.velocity_x *= 0.8
            self.velocity_y *= 0.8
    
    def steer_left(self):
        if not self.crashed and self.speed > 1:
            self.velocity_x -= self.steering_power * 0.3
            self.rotation = max(-15, self.rotation - 2)
    
    def steer_right(self):
        if not self.crashed and self.speed > 1:
            self.velocity_x += self.steering_power * 0.3
            self.rotation = min(15, self.rotation + 2)
    
    def center_rotation(self):
        if self.rotation > 0:
            self.rotation = max(0, self.rotation - 1)
        elif self.rotation < 0:
            self.rotation = min(0, self.rotation + 1)

# Game Objects
player_car = Car((0, 0, 5), (1, 0, 0), True)
ai_cars = [
    Car((-40, 50, 5), (0, 1, 0)),
    Car((40, 100, 5), (0, 0, 1)),
    Car((-20, 150, 5), (1, 1, 0))
]
all_cars = [player_car] + ai_cars

# Input handling
keys = {
    b'w': False, b's': False, b'a': False, b'd': False,
    b' ': False, b'r': False, b'p': False, b'c': False,
    b'n': False
}

def draw_text_2d(x, y, text, size=18):
    """FIXED - Draw 2D text on screen overlay with better error handling"""
    # Save current OpenGL state
    glPushAttrib(GL_ALL_ATTRIB_BITS)
    
    # Disable depth testing and lighting for text overlay
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    
    # Save current matrices
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    
    # Set orthographic projection
    gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT)
    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    # Set text color explicitly - BRIGHT WHITE for maximum visibility
    glColor3f(1.0, 1.0, 1.0)
    
    # Position text
    glRasterPos2f(x, y)
    
    # Select font
    try:
        font = GLUT_BITMAP_HELVETICA_18 if size == 18 else GLUT_BITMAP_HELVETICA_12
        
        # Draw each character
        for char in text:
            glutBitmapCharacter(font, ord(char))
    except:
        # Fallback font if there's an issue
        for char in text:
            glutBitmapCharacter(GLUT_BITMAP_9_BY_15, ord(char))
    
    # Restore matrices
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    
    # Restore OpenGL state
    glPopAttrib()

def draw_coins():
    """Draw collectible coins on the road"""
    for coin in coin_positions:
        if coin[3]:
            glPushMatrix()
            glTranslatef(coin[0], coin[1], coin[2])
            glRotatef(time.time() * 180, 0, 0, 1)
            
            # Coins glow at night
            if is_night_mode:
                glColor3f(1.2, 1.2, 0.5)  # Brighter gold at night
            else:
                glColor3f(1, 1, 0)  # Regular gold
                
            gluCylinder(gluNewQuadric(), 8, 8, 3, 8, 1)
            glTranslatef(0, 0, 1.5)
            
            if is_night_mode:
                glColor3f(1.0, 0.8, 0.2)
            else:
                glColor3f(0.8, 0.6, 0)
                
            glutSolidSphere(6, 8, 6)
            glPopMatrix()

def draw_highway_road():
    """Draw the highway road"""
    # Road surface color based on night mode only
    if is_night_mode:
        glColor3f(0.3, 0.3, 0.35)   # Dark road at night
    else:
        glColor3f(0.4, 0.4, 0.4)    # Regular road
    
    glBegin(GL_QUADS)
    glVertex3f(-ROAD_WIDTH/2, 0, 0)
    glVertex3f(ROAD_WIDTH/2, 0, 0)
    glVertex3f(ROAD_WIDTH/2, ROAD_LENGTH, 0)
    glVertex3f(-ROAD_WIDTH/2, ROAD_LENGTH, 0)
    glEnd()
    
    # Highway boundaries - brighter at night
    if is_night_mode:
        glColor3f(1.2, 1.2, 1.2)  # Bright white at night
    else:
        glColor3f(1, 1, 1)  # Regular white
        
    glLineWidth(5)
    glBegin(GL_LINES)
    glVertex3f(-ROAD_WIDTH/2, 0, 1)
    glVertex3f(-ROAD_WIDTH/2, ROAD_LENGTH, 1)
    glVertex3f(ROAD_WIDTH/2, 0, 1)
    glVertex3f(ROAD_WIDTH/2, ROAD_LENGTH, 1)
    glEnd()
    
    # Center dividing line - glows at night
    if is_night_mode:
        glColor3f(1.5, 1.5, 0.5)  # Bright yellow at night
    else:
        glColor3f(1, 1, 0)  # Regular yellow
        
    glLineWidth(3)
    dash_length = 50
    gap_length = 30
    y_pos = 0
    while y_pos < ROAD_LENGTH:
        glBegin(GL_LINES)
        glVertex3f(0, y_pos, 1)
        glVertex3f(0, min(y_pos + dash_length, ROAD_LENGTH), 1)
        glEnd()
        y_pos += dash_length + gap_length
    
    # Start line
    glColor3f(0.5, 1, 0.5) if is_night_mode else glColor3f(0, 1, 0)
    glLineWidth(8)
    glBegin(GL_LINES)
    glVertex3f(-ROAD_WIDTH/2, 50, 2)
    glVertex3f(ROAD_WIDTH/2, 50, 2)
    glEnd()
    
    draw_coins()
    draw_finish_line()

def draw_finish_line():
    """Draw finish line with night effects"""
    finish_y = FINISH_LINE_POSITION
    
    # Red base line - brighter at night
    if is_night_mode:
        glColor3f(1.5, 0.3, 0.3)
    else:
        glColor3f(1, 0, 0)
        
    glLineWidth(10)
    glBegin(GL_LINES)
    glVertex3f(-ROAD_WIDTH/2, finish_y, 2)
    glVertex3f(ROAD_WIDTH/2, finish_y, 2)
    glEnd()
    
    # Checkered pattern
    glColor3f(0.1, 0.1, 0.1) if is_night_mode else glColor3f(0, 0, 0)
    segment_width = ROAD_WIDTH / 12
    for i in range(0, 12, 2):
        x1 = -ROAD_WIDTH/2 + i * segment_width
        x2 = -ROAD_WIDTH/2 + (i + 1) * segment_width
        glLineWidth(8)
        glBegin(GL_LINES)
        glVertex3f(x1, finish_y, 3)
        glVertex3f(x2, finish_y, 3)
        glEnd()

def draw_highway_environment():
    """Draw environment with night/day effects"""
    # Grass color changes for night
    if is_night_mode:
        glColor3f(0.1, 0.3, 0.1)  # Dark grass at night
    else:
        glColor3f(0.2, 0.7, 0.2)  # Regular grass
    
    # Left side
    glBegin(GL_QUADS)
    glVertex3f(-1000, 0, 0)
    glVertex3f(-ROAD_WIDTH/2, 0, 0)
    glVertex3f(-ROAD_WIDTH/2, ROAD_LENGTH, 0)
    glVertex3f(-1000, ROAD_LENGTH, 0)
    glEnd()
    
    # Right side
    glBegin(GL_QUADS)
    glVertex3f(ROAD_WIDTH/2, 0, 0)
    glVertex3f(1000, 0, 0)
    glVertex3f(1000, ROAD_LENGTH, 0)
    glVertex3f(ROAD_WIDTH/2, ROAD_LENGTH, 0)
    glEnd()
    
    # Trees with night effects
    tree_positions = [
        (-250, 300), (280, 500), (-300, 800), (320, 1200),
        (-280, 1600), (300, 2000), (-320, 2400), (290, 2800)
    ]
    
    for x, y in tree_positions:
        if y < ROAD_LENGTH:
            glPushMatrix()
            glTranslatef(x, y, 0)
            
            # Tree trunk - darker at night
            if is_night_mode:
                glColor3f(0.2, 0.1, 0)
            else:
                glColor3f(0.4, 0.2, 0)
            gluCylinder(gluNewQuadric(), 12, 8, 50, 8, 1)
            
            # Tree top - darker at night
            glTranslatef(0, 0, 45)
            if is_night_mode:
                glColor3f(0.05, 0.3, 0.05)
            else:
                glColor3f(0.1, 0.6, 0.1)
            glutSolidSphere(30, 10, 8)
            
            glPopMatrix()

def draw_racing_car(car):
    """Draw cars with headlights at night"""
    glPushMatrix()
    glTranslatef(car.x, car.y, car.z)
    glRotatef(car.rotation, 0, 0, 1)
    
    # Car body
    if car.crashed:
        glColor3f(0.5, 0.5, 0.5)
    else:
        if is_night_mode:
            # Slightly brighter colors at night
            glColor3f(car.color[0] * 1.1, car.color[1] * 1.1, car.color[2] * 1.1)
        else:
            glColor3f(*car.color)
    
    glPushMatrix()
    glScalef(35, 20, 10)
    glutSolidCube(1)
    glPopMatrix()
    
    # Car roof
    if car.crashed:
        glColor3f(0.3, 0.3, 0.3)
    else:
        roof_brightness = 1.1 if is_night_mode else 0.7
        glColor3f(car.color[0] * roof_brightness, car.color[1] * roof_brightness, car.color[2] * roof_brightness)
    
    glPushMatrix()
    glTranslatef(0, 0, 8)
    glScalef(25, 15, 8)
    glutSolidCube(1)
    glPopMatrix()
    
    # Wheels
    glColor3f(0.1, 0.1, 0.1)
    wheel_positions = [(-15, 12, -3), (15, 12, -3), (-15, -12, -3), (15, -12, -3)]
    for wx, wy, wz in wheel_positions:
        glPushMatrix()
        glTranslatef(wx, wy, wz)
        glRotatef(90, 1, 0, 0)
        gluCylinder(gluNewQuadric(), 5, 5, 4, 10, 1)
        glPopMatrix()
    
    # Headlights - much brighter at night
    if car.crashed:
        glColor3f(0.5, 0.5, 0.4)
    else:
        if is_night_mode:
            glColor3f(1.5, 1.5, 1.0)  # Bright headlights at night
        else:
            glColor3f(1, 1, 0.8)  # Regular headlights
    
    for hx in [-12, 12]:
        glPushMatrix()
        glTranslatef(hx, 18, 3)
        if is_night_mode:
            glutSolidSphere(4, 10, 8)  # Bigger headlights at night
        else:
            glutSolidSphere(3, 8, 6)
        glPopMatrix()
    
    glPopMatrix()

def update_ai_racers(dt):
    """AI with difficulty adjustments and ALL cars update"""
    for i, car in enumerate(ai_cars):
        if car.finished or car.crashed:
            continue
        
        # AI speed based on custom difficulty
        difficulty_multiplier = 0.15 + (custom_difficulty * 0.01)
        ai_speed_multiplier = difficulty_multiplier + (current_level * 0.01)
        
        # Ensure each AI car gets proper acceleration
        car.velocity_y += car.acceleration_power * ai_speed_multiplier
        
        # AI steering logic
        current_time = time.time()
        if int(current_time * 2 + i) % 10 == 0:  # Different timing for each AI
            if abs(car.x) < ROAD_WIDTH/3:
                steer_direction = 1 if car.x < 0 else -1
                car.velocity_x += steer_direction * 0.2
        
        if abs(car.x) > ROAD_WIDTH/3:
            car.velocity_x -= car.x * 0.1
        
        # Make sure each AI car updates
        car.update(dt)

def update_highway_camera():
    """Camera system"""
    if game_state == RACING:
        if first_person_view:
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluPerspective(70, WINDOW_WIDTH/WINDOW_HEIGHT, 1, 5000)
            
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            forward_x = math.sin(math.radians(player_car.rotation))
            forward_y = math.cos(math.radians(player_car.rotation))
            
            gluLookAt(player_car.x, player_car.y, player_car.z + 20,
                      player_car.x + forward_x * 100, player_car.y + forward_y * 100, player_car.z + 15,
                      0, 0, 1)
        else:
            target_x = player_car.x
            target_y = player_car.y - camera_distance
            target_z = player_car.z + camera_height
            
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluPerspective(60, WINDOW_WIDTH/WINDOW_HEIGHT, 1, 5000)
            
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            gluLookAt(target_x, target_y, target_z,
                      player_car.x, player_car.y + 100, player_car.z + 20,
                      0, 0, 1)

def draw_dashboard_hud():
    """Enhanced HUD"""
    if game_state != RACING and game_state != PAUSED:
        return
    
    if player_car.crashed:
        draw_text_2d(WINDOW_WIDTH//2 - 50, WINDOW_HEIGHT//2, "CRASHED!")
        return
    
    # Speed display
    speed_mph = int(player_car.speed * 15)
    draw_text_2d(20, WINDOW_HEIGHT - 40, f"Speed: {speed_mph} MPH")
    
    # Lap counter
    draw_text_2d(20, WINDOW_HEIGHT - 70, f"Lap: {current_lap}/{total_laps}")
    
    draw_text_2d(20, WINDOW_HEIGHT - 100, f"Coins: {coins_collected}")
    draw_text_2d(20, WINDOW_HEIGHT - 130, f"Level: {current_level}/{max_level}")
    
    # Weather status
    weather_text = "Night" if is_night_mode else "Day"
    draw_text_2d(20, WINDOW_HEIGHT - 160, f"Time: {weather_text}")
    
    distance_remaining = max(0, FINISH_LINE_POSITION - player_car.y)
    draw_text_2d(20, WINDOW_HEIGHT - 190, f"Distance: {int(distance_remaining)}m")
    
    if race_start_time > 0:
        current_race_time = time.time() - race_start_time
        draw_text_2d(20, WINDOW_HEIGHT - 220, f"Time: {current_race_time:.1f}s")
    
    # Position
    position = 1
    for car in ai_cars:
        if car.y > player_car.y and not car.crashed:
            position += 1
    
    draw_text_2d(20, WINDOW_HEIGHT - 250, f"Position: {position}/4")
    
    # Show AI car count for debugging
    active_ai = len([car for car in ai_cars if not car.crashed])
    draw_text_2d(20, WINDOW_HEIGHT - 280, f"AI Cars Active: {active_ai}/3")
    
    # Game title
    draw_text_2d(WINDOW_WIDTH - 200, WINDOW_HEIGHT - 30, "HIGHWAY DASH 3D")
    
    # Controls
    draw_text_2d(WINDOW_WIDTH - 300, WINDOW_HEIGHT - 60, "W/S: Gas/Brake")
    draw_text_2d(WINDOW_WIDTH - 300, WINDOW_HEIGHT - 80, "A/D: Steer")
    draw_text_2d(WINDOW_WIDTH - 300, WINDOW_HEIGHT - 100, "N: Toggle Night")
    draw_text_2d(WINDOW_WIDTH - 300, WINDOW_HEIGHT - 120, "C: Camera View")

def draw_main_menu():
    """Main menu"""
    if is_night_mode:
        glClearColor(0.05, 0.05, 0.15, 1)  # Dark blue night
    else:
        glClearColor(0.1, 0.1, 0.3, 1)     # Regular blue
    
    draw_text_2d(WINDOW_WIDTH//2 - 90, WINDOW_HEIGHT//2 + 200, "HIGHWAY DASH 3D")
    draw_text_2d(WINDOW_WIDTH//2 - 150, WINDOW_HEIGHT//2 + 170, "==========================")
    draw_text_2d(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 + 120, "Ultimate Highway Racing")
    
    # Weather status
    weather_status = f"Time: {'Night' if is_night_mode else 'Day'}"
    draw_text_2d(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 + 80, weather_status)
    
    draw_text_2d(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 + 50, f"Current Level: {current_level}/{max_level}")
    draw_text_2d(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 + 30, f"Total Coins: {coins_collected}")
    
    # Menu options
    draw_text_2d(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 - 10, "Press SPACE to Start Race")
    draw_text_2d(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 - 40, "Press M for Custom Race")
    draw_text_2d(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 - 70, "ESC to Exit")
    
    # Controls
    draw_text_2d(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 - 110, "Press N to Toggle Night")

def draw_custom_race_menu():
    """Custom race settings menu"""
    if is_night_mode:
        glClearColor(0.05, 0.15, 0.05, 1)
    else:
        glClearColor(0.1, 0.3, 0.1, 1)
    
    draw_text_2d(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 + 150, "CUSTOM RACE SETTINGS")
    draw_text_2d(WINDOW_WIDTH//2 - 130, WINDOW_HEIGHT//2 + 120, "==========================")
    
    # Laps setting
    draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 + 60, f"Laps: {custom_laps}")
    draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 + 40, "Press 1/2/3 for 1/3/5 laps")
    
    # Difficulty setting
    difficulties = ["Easy", "Medium", "Hard"]
    draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2, f"Difficulty: {difficulties[custom_difficulty-1]}")
    draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 - 20, "Press Q/W/E for Easy/Med/Hard")
    
    # Time display
    time_status = f"Time: {'Night' if is_night_mode else 'Day'}"
    draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 - 80, time_status)
    draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 - 100, "Press N to toggle Night")
    
    # Controls
    draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 - 140, "Press SPACE to Start")
    draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 - 160, "Press ESC to go back")

def draw_game_complete():
    """FIXED - Game completion screen with working text display"""
    # Set background color
    if is_night_mode:
        glClearColor(0.1, 0.4, 0.1, 1)
    else:
        glClearColor(0.2, 0.8, 0.2, 1)
    
    # Calculate center positions for better text positioning
    center_x = WINDOW_WIDTH // 2
    center_y = WINDOW_HEIGHT // 2
    
    # FIXED - Draw completion messages with working positioning
    draw_text_2d(center_x - 120, center_y + 150, "CONGRATULATIONS!", 18)
    draw_text_2d(center_x - 90, center_y + 120, "GAME FINISHED!", 18)
    draw_text_2d(center_x - 150, center_y + 90, "YOU COMPLETED ALL 5 LEVELS!", 18)
    
    # Add "Compete, Win!" message
    draw_text_2d(center_x - 80, center_y + 50, "Compete, Win!", 18)
    
    # Game stats
    draw_text_2d(center_x - 120, center_y + 10, f"Total Coins Collected: {coins_collected}", 18)
    draw_text_2d(center_x - 100, center_y - 20, f"Total Races Won: {races_won}", 18)
    
    # Auto-restart notice
    if game_complete_time is not None:
        remaining_time = max(0, AUTO_RESTART_SECONDS - (time.time() - game_complete_time))
        draw_text_2d(center_x - 140, center_y - 60, f"Restarting to Level 1 in {remaining_time:.1f} seconds...", 18)
    else:
        draw_text_2d(center_x - 100, center_y - 60, "Thanks for Playing!", 18)
        draw_text_2d(center_x - 130, center_y - 90, "Press ESC to return to menu", 18)

def handle_highway_controls(dt):
    """Control system"""
    global first_person_view
    
    if game_state != RACING:
        return
        
    if keys[b'w']:
        player_car.accelerate()
    if keys[b's']:
        player_car.brake()
    if keys[b'a']:
        player_car.steer_left()
    if keys[b'd']:
        player_car.steer_right()
    
    if not keys[b'a'] and not keys[b'd']:
        player_car.center_rotation()

def initialize_race_cars():
    """Initialize all 4 cars (player + 3 AI) for racing"""
    # Reset player car
    player_car.x, player_car.y, player_car.z = 0, 0, 5
    player_car.velocity_x = player_car.velocity_y = 0
    player_car.rotation = 0
    player_car.finished = False
    player_car.crashed = False
    player_car.laps_completed = 0
    player_car.speed = 0
    
    # Reset all 3 AI cars with proper starting positions
    ai_starting_positions = [(-40, 50, 5), (40, 100, 5), (-20, 150, 5)]
    
    for i, car in enumerate(ai_cars):
        if i < len(ai_starting_positions):
            car.x, car.y, car.z = ai_starting_positions[i]
        else:
            car.x, car.y, car.z = random.uniform(-50, 50), random.uniform(50, 200), 5
        
        car.velocity_x = car.velocity_y = 0
        car.rotation = 0
        car.finished = False
        car.crashed = False
        car.laps_completed = 0
        car.speed = 0

def keyboard_down(key, x, y):
    """Enhanced input handler"""
    global game_state, race_start_time, first_person_view, current_level, ROAD_LENGTH, FINISH_LINE_POSITION
    global is_night_mode, custom_laps, custom_difficulty, total_laps, current_lap
    
    # Night mode toggle (work in any state)
    if key == b'n':
        is_night_mode = not is_night_mode
        print(f"Night mode {'ON' if is_night_mode else 'OFF'}")
    
    if game_state == GAME_COMPLETE:
        game_state = MENU
        return
    
    # Custom Race Menu controls
    elif game_state == CUSTOM_RACE_MENU:
        if key == b'1':
            custom_laps = 1
        elif key == b'2':
            custom_laps = 3
        elif key == b'3':
            custom_laps = 5
        elif key == b'q':
            custom_difficulty = 1
        elif key == b'w':
            custom_difficulty = 2
        elif key == b'e':
            custom_difficulty = 3
        elif key == b' ':
            # Start custom race with all cars properly initialized
            print("Starting custom race...")
            total_laps = custom_laps
            current_lap = 1
            game_state = RACING
            race_start_time = time.time()
            ROAD_LENGTH = 3000 + (current_level * 2000)
            FINISH_LINE_POSITION = ROAD_LENGTH - 200
            generate_collectibles()
            
            # Use proper initialization function
            initialize_race_cars()
            
            print(f"Custom race started - {total_laps} laps, difficulty {custom_difficulty}")
        elif key == b'\x1b':
            game_state = MENU
    
    # Regular menu controls
    elif key == b' ':
        if game_state == MENU:
            # Regular race initialization
            print("Starting regular race...")
            total_laps = 1
            current_lap = 1
            game_state = RACING
            race_start_time = time.time()
            ROAD_LENGTH = 3000 + (current_level * 2000)
            FINISH_LINE_POSITION = ROAD_LENGTH - 200
            generate_collectibles()
            
            # Use proper initialization function
            initialize_race_cars()
            
            print("Regular race started")
    elif key == b'm' and game_state == MENU:
        game_state = CUSTOM_RACE_MENU
    elif key == b'p' and game_state == RACING:
        game_state = PAUSED
    elif key == b'p' and game_state == PAUSED:
        game_state = RACING
    elif key == b'c' and game_state == RACING:
        first_person_view = not first_person_view
    elif key == b'r':
        restart_highway_race()
    elif key == b'\x1b':
        if game_state == CUSTOM_RACE_MENU:
            game_state = MENU
        elif game_state == FINISHED:
            game_state = MENU
        elif game_state == GAME_COMPLETE:
            game_state = MENU
        elif game_state == MENU:
            try:
                glutLeaveMainLoop()
            except:
                import sys
                sys.exit(0)
        else:
            game_state = MENU
    
    if key in keys:
        keys[key] = True

def keyboard_up(key, x, y):
    """Key release handler"""
    if key in keys:
        keys[key] = False

def level_up():
    """Progress to next level with auto-restart"""
    global current_level, races_won, game_state, game_complete_time
    
    races_won += 1
    current_level += 1
    print(f"Level completed! Advanced to level {current_level}")
    
    # If we just finished level 5, go to GAME_COMPLETE and start auto-restart timer
    if current_level > max_level:
        print("All levels completed GAME_COMPLETE")
        game_state = GAME_COMPLETE
        game_complete_time = time.time()
        # Clamp level display at max
        current_level = max_level
        return

def restart_highway_race():
    """Restart race with all AI cars"""
    global game_state, race_start_time, coins_collected, current_lap
    
    print("Restarting race...")
    current_lap = 1
    
    # Use proper initialization function
    initialize_race_cars()
    
    generate_collectibles()
    
    game_state = RACING
    race_start_time = time.time()
    
    print("Race restarted with all cars")

def reset_to_new_game():
    """Reset to new game (Level 1)"""
    global current_level, races_won, coins_collected, game_state
    print("Resetting to new game (Level 1)")
    current_level = 1
    races_won = 0
    coins_collected = 0
    # Recompute track metrics for level 1
    global ROAD_LENGTH, FINISH_LINE_POSITION
    ROAD_LENGTH = 3000 + (current_level * 2000)
    FINISH_LINE_POSITION = ROAD_LENGTH - 200
    game_state = MENU

def update_highway_game(dt):
    """Main update loop"""
    global game_state
    
    if game_state == RACING:
        handle_highway_controls(dt)
        
        # Car collision detection
        for i, car1 in enumerate(all_cars):
            if car1.crashed:
                continue
            for j, car2 in enumerate(all_cars):
                if i >= j or car2.crashed:
                    continue
                if detect_car_collision(car1, car2):
                    car1.crashed = True
                    car2.crashed = True
                    if car1.is_player or car2.is_player:
                        game_state = FINISHED
                        return
        
        # Update player and ALL AI cars
        player_car.update(dt)
        update_ai_racers(dt)  # This updates all 3 AI cars
        
        if player_car.finished:
            player_won = True
            for car in ai_cars:
                if car.finished and not car.crashed and car.race_time < player_car.race_time:
                    player_won = False
                    break
            
            if player_won:
                print(f"Player won Current level: {current_level}")
                level_up()
                print(f"After level_up, game state: {game_state}")
            
            game_state = FINISHED

def display():
    """Main display function"""
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
    if game_state == MENU:
        draw_main_menu()
    elif game_state == CUSTOM_RACE_MENU:
        draw_custom_race_menu()
    elif game_state == GAME_COMPLETE:
        draw_game_complete()
    elif game_state == RACING or game_state == PAUSED:
        # Background color changes for night mode
        if is_night_mode:
            glClearColor(0.1, 0.1, 0.2, 1)  # Dark night sky
        else:
            glClearColor(0.6, 0.8, 1.0, 1)  # Bright day sky
        
        update_highway_camera()
        
        glEnable(GL_DEPTH_TEST)
        draw_highway_environment()
        draw_highway_road()
        
        if first_person_view:
            for car in ai_cars:
                draw_racing_car(car)
        else:
            # Draw all 4 cars (player + 3 AI)
            for car in all_cars:
                draw_racing_car(car)
        
        glDisable(GL_DEPTH_TEST)
        
        draw_dashboard_hud()
        
        if game_state == PAUSED:
            draw_text_2d(WINDOW_WIDTH//2 - 50, WINDOW_HEIGHT//2, "PAUSED")
    
    elif game_state == FINISHED:
        if player_car.crashed:
            draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 + 60, "RACE OVER - CRASHED!")
            draw_text_2d(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 + 30, "You collided with another car!")
        else:
            player_won = True
            for car in ai_cars:
                if car.finished and not car.crashed and car.race_time < player_car.race_time:
                    player_won = False
                    break
            
            if player_won:
                if current_level >= max_level:
                    draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 + 60, "GAME COMPLETE")
                    draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 + 30, "All levels finished")
                    draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 + 5, "Compete, Win")
                else:
                    draw_text_2d(WINDOW_WIDTH//2 - 60, WINDOW_HEIGHT//2 + 60, "LEVEL COMPLETED")
                    draw_text_2d(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 + 30, f"Advancing to Level {current_level}!")
                draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 - 20, f"Coins Earned: {len([c for c in coin_positions if not c[3]])}")
            else:
                draw_text_2d(WINDOW_WIDTH//2 - 60, WINDOW_HEIGHT//2 + 30, "RACE FINISHED")
        
        if player_car.finished:
            draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 - 50, f"Your Time: {player_car.race_time:.2f}s")
        
        draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 - 80, "Press R to restart")
        draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 - 110, "Press ESC for menu")
    
    glutSwapBuffers()

def idle():
    """Highway Dash 3D timing system with auto-restart"""
    global last_time, game_complete_time
    
    current_time = time.time()
    dt = min(current_time - last_time, 0.1)
    last_time = current_time
    
    # Handle auto-restart when in GAME_COMPLETE
    if game_state == GAME_COMPLETE and game_complete_time is not None:
        if (current_time - game_complete_time) >= AUTO_RESTART_SECONDS:
            reset_to_new_game()
    
    update_highway_game(dt)
    glutPostRedisplay()

def main():
    """Initialize Highway Dash 3D"""
    generate_collectibles()
    
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    glutCreateWindow(b"Highway Dash 3D")
    
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_POSITION, [100, 100, 200, 1])
    glEnable(GL_COLOR_MATERIAL)
    
    glutDisplayFunc(display)
    glutKeyboardFunc(keyboard_down)
    try:
        glutKeyboardUpFunc(keyboard_up)
    except:
        pass
    glutIdleFunc(idle)
    print("HIGHWAY DASH 3D")
    glutMainLoop()
if __name__ == "__main__":
    main()
