import pygame
import sys
import math
import random
import os
from pygame.locals import *
import threading

# Try to import pyttsx3 for voice announcements
try:
    import pyttsx3
    tts_available = True
except ImportError:
    print("pyttsx3 not available. Voice announcements will be disabled.")
    tts_available = False

# Import game objects
from ship import Ship
from asteroid import Asteroid
from laser import Laser
from particle import ExplosionSystem

# Initialize pygame
pygame.init()
pygame.mixer.init()  # Initialize sound system

# Game constants
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRID_COLOR = (20, 20, 80)
GRID_BRIGHT = (40, 40, 120)

# Game state constants
TITLE_SCREEN = 0
PLAYING = 1
GAME_OVER = 2
PAUSED = 3

# Text-to-speech setup
def speak_text(text, voice_id=None):
    """Speak the given text using pyttsx3 in a separate thread"""
    if not tts_available:
        return
        
    def speak_worker():
        try:
            engine = pyttsx3.init()
            
            # Set properties
            engine.setProperty('rate', 150)  # Speed of speech
            engine.setProperty('volume', 1.0)  # Increased volume from 0.9 to 1.0 (maximum)
            
            # Set voice (if specified)
            if voice_id:
                engine.setProperty('voice', voice_id)
            else:
                # Try to find a deep male voice (for Mortal Kombat style)
                voices = engine.getProperty('voices')
                for voice in voices:
                    if 'male' in voice.id.lower():
                        engine.setProperty('voice', voice.id)
                        break
            
            # Speak the text
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"Speech error: {e}")
    
    # Run in a separate thread to avoid blocking the game
    thread = threading.Thread(target=speak_worker)
    thread.daemon = True  # Thread will close when main program exits
    thread.start()

class FluidField:
    """Class to create a fluid-like field with particles that are affected by the ship"""
    def __init__(self, width, height, mode="grid"):
        self.width = width
        self.height = height
        self.particles = []
        self.num_particles = 650  # Increased from 600 to 650 for more density
        self.flow_speed = 0.9
        self.influence_radius = 150
        self.ship_influence = 4.0
        self.grid_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.mode = mode  # "grid" (gameplay) or "swirl" (splash screen)
        
        # Disruption tracking for lingering effects
        self.disruption_map = {}  # Stores disruption information by region
        self.disruption_decay = 180  # Approx 3 seconds at 60 FPS
        self.disruption_cell_size = 30  # Size of grid cells for disruption tracking
        self.disruption_strength = 1.0  # Initial strength of disruption
        
        # Create initial particles
        self.init_particles()
        
    def init_particles(self):
        """Initialize fluid particles based on the current mode"""
        self.particles = []
        
        # Calculate grid dimensions
        cols = int(math.sqrt(self.num_particles * self.width / self.height))
        rows = int(self.num_particles / cols)
        
        cell_width = self.width / cols
        cell_height = self.height / rows
        
        # Create particles with different initialization based on mode
        for i in range(cols):
            for j in range(rows):
                # Calculate base position (center of each grid cell)
                base_x = (i + 0.5) * cell_width
                base_y = (j + 0.5) * cell_height
                
                # Add small random offset for natural look
                if self.mode == "grid":
                    # Very small jitter for grid mode
                    x = base_x + random.uniform(-cell_width * 0.1, cell_width * 0.1)
                    y = base_y + random.uniform(-cell_height * 0.1, cell_height * 0.1)
                    # Nearly stationary initial velocity for grid mode
                    vx = random.uniform(-0.05, 0.05)
                    vy = random.uniform(-0.05, 0.05)
                else:  # "swirl" mode
                    # More random positioning for swirl mode
                    x = base_x + random.uniform(-cell_width * 0.3, cell_width * 0.3)
                    y = base_y + random.uniform(-cell_height * 0.3, cell_height * 0.3)
                    # More active initial velocity for swirl
                    vx = random.uniform(-0.5, 0.5)
                    vy = random.uniform(-0.5, 0.5)
                
                # Rest of particle properties
                lifetime = random.randint(300, 600)
                trail = [(x, y)]
                
                # Different colors based on mode - BRIGHTENED
                if self.mode == "grid":
                    color = (
                        random.randint(60, 140),     # Increased red
                        random.randint(130, 210),    # Increased green
                        random.randint(200, 255),    # Maximum blue
                        random.randint(100, 180)     # Higher alpha
                    )
                else:  # "swirl" mode - even brighter colors
                    color = (
                        random.randint(80, 160),     # Higher red
                        random.randint(150, 230),    # Higher green
                        random.randint(220, 255),    # Maximum blue
                        random.randint(120, 200)     # Higher alpha
                    )
                
                # Add the particle
                self.particles.append({
                    'x': x, 'y': y, 
                    'vx': vx, 'vy': vy, 
                    'lifetime': lifetime,
                    'trail': trail,
                    'max_trail': random.randint(12, 35) if self.mode == "swirl" else random.randint(8, 20),  # Longer trails
                    'color': color,
                    'base_x': base_x,  # Store original grid position
                    'base_y': base_y,
                    'disruption': 0,   # Disruption counter for lingering effects
                    'disrupted_vx': 0,  # Store disruption velocity
                    'disrupted_vy': 0
                })
        
        # Fill in any remaining particles if needed
        while len(self.particles) < self.num_particles:
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            
            if self.mode == "grid":
                vx = random.uniform(-0.05, 0.05)
                vy = random.uniform(-0.05, 0.05)
                color = (
                    random.randint(60, 140),
                    random.randint(130, 210),
                    random.randint(200, 255),
                    random.randint(100, 180)
                )
                max_trail = random.randint(8, 20)
            else:  # "swirl"
                vx = random.uniform(-0.5, 0.5)
                vy = random.uniform(-0.5, 0.5)
                color = (
                    random.randint(80, 160),
                    random.randint(150, 230),
                    random.randint(220, 255),
                    random.randint(120, 200)
                )
                max_trail = random.randint(12, 35)
            
            self.particles.append({
                'x': x, 'y': y, 
                'vx': vx, 'vy': vy, 
                'lifetime': random.randint(300, 600),
                'trail': [(x, y)],
                'max_trail': max_trail,
                'color': color,
                'base_x': x,  # Store position as base
                'base_y': y,
                'disruption': 0,
                'disrupted_vx': 0,
                'disrupted_vy': 0
            })
    
    def set_mode(self, mode):
        """Change the fluid field mode and reinitialize particles"""
        if mode != self.mode:
            self.mode = mode
            self.init_particles()
            self.disruption_map = {}  # Reset disruptions on mode change
    
    def get_cell_key(self, x, y):
        """Get a cell key for disruption map based on position"""
        cell_x = int(x / self.disruption_cell_size)
        cell_y = int(y / self.disruption_cell_size)
        return f"{cell_x}_{cell_y}"
    
    def update(self, ship=None):
        """Update the fluid field simulation, optionally affected by ship"""
        # Update disruption map - decay all existing disruptions
        keys_to_remove = []
        for key, disruption in self.disruption_map.items():
            disruption['strength'] -= 1.0 / self.disruption_decay
            if disruption['strength'] <= 0:
                keys_to_remove.append(key)
        
        # Remove expired disruptions
        for key in keys_to_remove:
            del self.disruption_map[key]
        
        # Track new disruptions if ship exists
        if ship and self.mode == "grid":
            # Create a disruption in cells near the ship
            radius = self.influence_radius / self.disruption_cell_size
            ship_x, ship_y = ship.rect.center
            
            # Calculate velocity of ship for disruption direction
            ship_speed = ship.velocity.length()
            if ship_speed > 0.1:  # Only add directional disruption if moving
                ship_angle = math.radians(ship.angle)
                ship_vx = -math.cos(ship_angle) * ship_speed * 0.3
                ship_vy = math.sin(ship_angle) * ship_speed * 0.3
                
                # Add disruption to cells near the ship's path
                for r in range(int(radius)):
                    # Add cells in the direction the ship is moving
                    trail_x = int((ship_x + ship_vx * r * 3) / self.disruption_cell_size)
                    trail_y = int((ship_y + ship_vy * r * 3) / self.disruption_cell_size)
                    key = f"{trail_x}_{trail_y}"
                    
                    if key not in self.disruption_map:
                        self.disruption_map[key] = {
                            'strength': self.disruption_strength,
                            'vx': ship_vx * 1.5,  # Exaggerate the effect
                            'vy': ship_vy * 1.5
                        }
                    else:
                        # Strengthen existing disruption
                        self.disruption_map[key]['strength'] = min(
                            1.0, 
                            self.disruption_map[key]['strength'] + 0.3
                        )
            
            # Add general disruption around ship
            center_x = int(ship_x / self.disruption_cell_size)
            center_y = int(ship_y / self.disruption_cell_size)
            
            for dx in range(-int(radius/2), int(radius/2) + 1):
                for dy in range(-int(radius/2), int(radius/2) + 1):
                    dist = math.sqrt(dx*dx + dy*dy)
                    if dist <= radius/2:
                        key = f"{center_x + dx}_{center_y + dy}"
                        if key not in self.disruption_map:
                            # Random turbulence effect
                            self.disruption_map[key] = {
                                'strength': self.disruption_strength * (1 - dist/(radius/2)),
                                'vx': random.uniform(-1.0, 1.0) * ship_speed * 0.2,
                                'vy': random.uniform(-1.0, 1.0) * ship_speed * 0.2
                            }
                        else:
                            # Strengthen existing disruption
                            self.disruption_map[key]['strength'] = min(
                                1.0, 
                                self.disruption_map[key]['strength'] + 0.2 * (1 - dist/(radius/2))
                            )
        
        # Update each particle
        for particle in self.particles:
            # Apply different flow behavior based on mode
            if self.mode == "swirl":
                # For splash screen: create swirling pattern
                cx, cy = self.width/2, self.height/2
                dx = particle['x'] - cx
                dy = particle['y'] - cy
                dist = math.sqrt(dx*dx + dy*dy)
                
                # Add circular motion - ensure center gets covered too
                if dist > 0:
                    angle = math.atan2(dy, dx)
                    # Create inward flow when far from center, outward when close
                    flow_factor = min(1.0, dist / (self.width * 0.3))
                    if dist > self.width * 0.2:  # Far from center
                        circular_vx = -math.sin(angle) * 0.2 * flow_factor - dx * 0.0005
                        circular_vy = math.cos(angle) * 0.2 * flow_factor - dy * 0.0005
                    else:  # Close to center - push slightly outward
                        circular_vx = -math.sin(angle) * 0.1 + dx * 0.001
                        circular_vy = math.cos(angle) * 0.1 + dy * 0.001
                else:
                    circular_vx, circular_vy = random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1)
                
                # Apply forces
                particle['vx'] = 0.95 * particle['vx'] + circular_vx + random.uniform(-0.15, 0.15)
                particle['vy'] = 0.95 * particle['vy'] + circular_vy + random.uniform(-0.15, 0.15)
            
            else:  # "grid" mode
                # Check for disruption effects
                cell_key = self.get_cell_key(particle['x'], particle['y'])
                
                if cell_key in self.disruption_map:
                    # Apply disruption from map
                    disruption = self.disruption_map[cell_key]
                    strength = disruption['strength']
                    
                    # Store disruption for lingering effects
                    particle['disruption'] = self.disruption_decay
                    particle['disrupted_vx'] = disruption['vx'] * strength
                    particle['disrupted_vy'] = disruption['vy'] * strength
                
                # For gameplay: maintain a relatively stable grid that reacts to the ship
                # Apply a small force to return particle toward its original grid position
                return_force = 0.02
                dx = particle['base_x'] - particle['x']
                dy = particle['base_y'] - particle['y']
                
                # Apply lingering disruption if active
                if particle['disruption'] > 0:
                    particle['disruption'] -= 1
                    decay_factor = particle['disruption'] / self.disruption_decay
                    
                    # Apply lingering effect with decay
                    disrupt_vx = particle['disrupted_vx'] * decay_factor
                    disrupt_vy = particle['disrupted_vy'] * decay_factor
                    
                    # Combine with normal movement
                    particle['vx'] = 0.9 * particle['vx'] + dx * return_force * (1 - decay_factor*0.8) + disrupt_vx
                    particle['vy'] = 0.9 * particle['vy'] + dy * return_force * (1 - decay_factor*0.8) + disrupt_vy
                else:
                    # Normal grid behavior
                    particle['vx'] = 0.9 * particle['vx'] + dx * return_force + random.uniform(-0.02, 0.02)
                    particle['vy'] = 0.9 * particle['vy'] + dy * return_force + random.uniform(-0.02, 0.02)
            
            # If ship exists, compute its direct influence on particles
            if ship:
                dx = particle['x'] - ship.rect.centerx
                dy = particle['y'] - ship.rect.centery
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance < self.influence_radius:
                    # Compute angle from ship to particle
                    angle = math.atan2(dy, dx)
                    
                    # Normalize influence by distance (stronger closer to ship)
                    influence = self.ship_influence * (1.0 - distance / self.influence_radius)
                    
                    # Calculate ship's velocity components
                    ship_speed = ship.velocity.length()
                    ship_angle = math.radians(ship.angle)
                    ship_vx = -math.cos(ship_angle) * ship_speed * 0.25
                    ship_vy = math.sin(ship_angle) * ship_speed * 0.25
                    
                    # Add ship's wake effect (push away from ship based on its movement)
                    particle['vx'] += math.cos(angle) * influence + ship_vx
                    particle['vy'] += math.sin(angle) * influence + ship_vy
                    
                    # Add extra turbulence for ship disturbance
                    if distance < self.influence_radius * 0.5:
                        particle['vx'] += random.uniform(-0.5, 0.5) * influence
                        particle['vy'] += random.uniform(-0.5, 0.5) * influence
            
            # Apply velocity to position (scaled based on mode)
            if self.mode == "grid":
                flow_mult = 0.8  # Slower movement in grid mode
            else:
                flow_mult = 1.0  # Full movement in swirl mode
                
            particle['x'] += particle['vx'] * self.flow_speed * flow_mult
            particle['y'] += particle['vy'] * self.flow_speed * flow_mult
            
            # Add current position to trail
            particle['trail'].append((particle['x'], particle['y']))
            
            # Limit trail length
            while len(particle['trail']) > particle['max_trail']:
                particle['trail'].pop(0)
            
            # Decrease lifetime
            particle['lifetime'] -= 1
            
            # Reset particle if it's off-screen or lifetime ended
            if (particle['lifetime'] <= 0 or 
                particle['x'] < -50 or particle['x'] > self.width + 50 or
                particle['y'] < -50 or particle['y'] > self.height + 50):
                self.reset_particle(particle)
    
    def reset_particle(self, particle):
        """Reset a particle to a new position"""
        if self.mode == "grid":
            # In grid mode, return to original grid position
            particle['x'] = particle['base_x'] + random.uniform(-5, 5)
            particle['y'] = particle['base_y'] + random.uniform(-5, 5)
            particle['vx'] = random.uniform(-0.05, 0.05)
            particle['vy'] = random.uniform(-0.05, 0.05)
        else:
            # In swirl mode, reset to a random edge
            edge = random.randint(0, 3)
            if edge == 0:  # Top
                particle['x'] = random.randint(0, self.width)
                particle['y'] = -10
                particle['vy'] = random.uniform(0.5, 2.5)
                particle['vx'] = random.uniform(-1.0, 1.0)
            elif edge == 1:  # Right
                particle['x'] = self.width + 10
                particle['y'] = random.randint(0, self.height)
                particle['vx'] = random.uniform(-2.5, -0.5)
                particle['vy'] = random.uniform(-1.0, 1.0)
            elif edge == 2:  # Bottom
                particle['x'] = random.randint(0, self.width)
                particle['y'] = self.height + 10
                particle['vy'] = random.uniform(-2.5, -0.5)
                particle['vx'] = random.uniform(-1.0, 1.0)
            else:  # Left
                particle['x'] = -10
                particle['y'] = random.randint(0, self.height)
                particle['vx'] = random.uniform(0.5, 2.5)
                particle['vy'] = random.uniform(-1.0, 1.0)
            
            # Update base position for grid return force
            particle['base_x'] = particle['x']
            particle['base_y'] = particle['y']
        
        # Reset other properties
        particle['lifetime'] = random.randint(300, 600)
        particle['trail'] = [(particle['x'], particle['y'])]
        particle['disruption'] = 0
        particle['disrupted_vx'] = 0
        particle['disrupted_vy'] = 0
        
        # Reset color based on mode - BRIGHTENED
        if self.mode == "grid":
            particle['max_trail'] = random.randint(8, 20)  # Longer trails for grid
            particle['color'] = (
                random.randint(60, 140),
                random.randint(130, 210),
                random.randint(200, 255),
                random.randint(100, 180)
            )
        else:  # "swirl"
            particle['max_trail'] = random.randint(12, 35)  # Longer trails for swirl
            particle['color'] = (
                random.randint(80, 160),
                random.randint(150, 230),
                random.randint(220, 255),
                random.randint(120, 200)
            )
    
    def draw(self, surface):
        """Draw the fluid field"""
        # Clear the drawing surface
        self.grid_surface.fill((0, 0, 0, 0))
        
        # Draw each particle's trail as a line
        for particle in self.particles:
            if len(particle['trail']) > 1:
                # Determine if this particle is disrupted
                is_disrupted = particle['disruption'] > 0
                disruption_factor = particle['disruption'] / self.disruption_decay if is_disrupted else 0
                
                # Draw with gradient transparency (more transparent at the start)
                for i in range(len(particle['trail']) - 1):
                    # Calculate alpha gradient
                    alpha_ratio = i / max(1, len(particle['trail']) - 1)
                    alpha = int(particle['color'][3] * alpha_ratio)
                    
                    # Create gradient color with slight glow effect
                    # Brighten disrupted particles
                    if is_disrupted:
                        # Increase brightness for disrupted particles
                        color = (
                            min(255, particle['color'][0] + int(50 * disruption_factor)),
                            min(255, particle['color'][1] + int(50 * disruption_factor)),
                            min(255, particle['color'][2] + int(30 * disruption_factor)),
                            alpha
                        )
                    else:
                        color = (
                            particle['color'][0],
                            particle['color'][1],
                            particle['color'][2],
                            alpha
                        )
                    
                    # Draw thicker lines based on disruption
                    line_thickness = 2
                    if is_disrupted and i > len(particle['trail']) * 0.5:
                        line_thickness = 2 + int(disruption_factor * 2)
                    elif i > len(particle['trail']) * 0.7:
                        line_thickness = 2
                    else:
                        line_thickness = 1
                    
                    # Draw line segment
                    pygame.draw.line(
                        self.grid_surface,
                        color,
                        particle['trail'][i],
                        particle['trail'][i + 1],
                        line_thickness
                    )
                    
                    # Add glow dots at the end of trails for emphasis
                    if i > len(particle['trail']) * 0.9:
                        glow_size = 1
                        if is_disrupted:
                            glow_size = 1 + int(disruption_factor * 2)
                            
                        glow_color = (
                            min(255, particle['color'][0] + 70),
                            min(255, particle['color'][1] + 70),
                            min(255, particle['color'][2] + 50),
                            alpha
                        )
                        pygame.draw.circle(
                            self.grid_surface,
                            glow_color,
                            particle['trail'][i],
                            glow_size
                        )
        
        # Blit the fluid field to the main surface
        surface.blit(self.grid_surface, (0, 0))

class AsteroidGame:
    def __init__(self):
        """Initialize the game"""
        # Set up the display
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Retro Asteroids")
        
        # Set up the clock
        self.clock = pygame.time.Clock()
        
        # Create fluid field background - swirl mode for title screen
        self.fluid_field = FluidField(SCREEN_WIDTH, SCREEN_HEIGHT, mode="swirl")
        
        # Create explosion system
        self.explosion_system = ExplosionSystem()
        
        # Game state
        self.state = TITLE_SCREEN
        
        # Game variables
        self.score = 0
        self.lives = 3
        self.level = 1
        
        # Game objects
        self.ship = None
        self.asteroids = pygame.sprite.Group()
        self.lasers = pygame.sprite.Group()
        
        # Font setup - use more retro-looking fonts if available
        try:
            self.title_font = pygame.font.Font(None, 60)
            self.info_font = pygame.font.Font(None, 30)
            self.small_font = pygame.font.Font(None, 20)  # Add smaller font for additional instructions
        except:
            # Fallback to system fonts
            self.title_font = pygame.font.SysFont('Arial', 60)
            self.info_font = pygame.font.SysFont('Arial', 30)
            self.small_font = pygame.font.SysFont('Arial', 20)  # Add smaller font for additional instructions
        
        # Sound setup
        self.sounds = {}
        self.load_sounds()
        
        # Voice announcement flag
        self.welcome_played = False
        
        # Set initial state
        self.reset_game()
        
        # Player name
        self.player_name = ""
        self.name_input_active = True
        self.name_input_cursor_visible = True
        self.name_input_cursor_time = 0
        
        # Jokes
        self.joke_timer = 0
        self.joke_interval = 20000  # 20 seconds between jokes
        self.joke_templates = [
            "Yo mama's so fat, when {name} plays Asteroids with her, she's the final boss!",
            "Yo mama's so slow, {name} could dodge asteroids faster blindfolded!",
            "Yo mama's so lazy, she makes {name} do all her asteroid shooting for her!",
            "Yo mama's so old, she taught {name} how to play the original Asteroids in the arcade!",
            "Yo mama's so confused, she thought {name}'s high score in Asteroids was her credit score!",
            "Yo mama's so uncoordinated, even {name} on their first try plays better than her!",
            "Yo mama's so bad at video games, {name} had to beat the tutorial level for her!",
            "Yo mama's so technologically challenged, she thinks {name}'s spaceship is an actual flying saucer!",
            "Yo mama's so distracted, {name} scored three levels while she was still reading the instructions!",
            "Yo mama's so competitive, she unplugs the game when {name} starts winning!"
        ]
        self.last_joke_index = -1
    
    def load_sounds(self):
        """Load sound effects and music or generate basic sounds if files don't exist"""
        try:
            # Create assets directory if it doesn't exist
            if not os.path.exists("assets"):
                os.makedirs("assets")
                print("Created assets directory")
            
            # Only generate music if it doesn't exist (changed from forcing regeneration)
            generate_music = False
            
            # Check if sound files exist
            sound_files_exist = (
                os.path.exists("assets/laser.wav") and
                os.path.exists("assets/explosion.wav") and
                os.path.exists("assets/thrust.wav") and
                os.path.exists("assets/game_over.wav") and
                os.path.exists("assets/level_up.wav")
            )
            
            # If sound files don't exist, generate basic sounds
            if not sound_files_exist:
                print("Sound files not found. Generating basic sounds...")
                self.generate_basic_sounds()
            
            # Try to load sound effects
            if os.path.exists("assets/laser.wav"):
                self.sounds["laser"] = pygame.mixer.Sound("assets/laser.wav")
                self.sounds["laser"].set_volume(0.2)  # Reduced from 0.3 to 0.2
            
            if os.path.exists("assets/explosion.wav"):
                self.sounds["explosion"] = pygame.mixer.Sound("assets/explosion.wav")
                self.sounds["explosion"].set_volume(0.4)
            
            if os.path.exists("assets/thrust.wav"):
                self.sounds["thrust"] = pygame.mixer.Sound("assets/thrust.wav")
                self.sounds["thrust"].set_volume(0.15)  # Reduced from 0.2 to 0.15
            
            if os.path.exists("assets/game_over.wav"):
                self.sounds["game_over"] = pygame.mixer.Sound("assets/game_over.wav")
                self.sounds["game_over"].set_volume(0.5)
            
            if os.path.exists("assets/level_up.wav"):
                self.sounds["level_up"] = pygame.mixer.Sound("assets/level_up.wav")
                self.sounds["level_up"].set_volume(0.5)
            
            if os.path.exists("assets/asteroid_hit.wav"):
                self.sounds["asteroid_hit"] = pygame.mixer.Sound("assets/asteroid_hit.wav")
                self.sounds["asteroid_hit"].set_volume(0.3)
            
            # Check for music file - only generate if it doesn't exist
            if not os.path.exists("assets/lofi_soundtrack.wav"):
                print("Background music not found. Generating new soundtrack...")
                self.generate_simple_music()
            else:
                print("Loading existing background music...")
                # Load and play existing background music
                pygame.mixer.music.load("assets/lofi_soundtrack.wav")
                pygame.mixer.music.set_volume(0.5)  # Increased from 0.3 to 0.5
                pygame.mixer.music.play(-1)  # Loop indefinitely
            
        except Exception as e:
            print(f"Error loading sounds: {e}")
            print("Game will continue without sound.")
    
    def generate_basic_sounds(self):
        """Generate cool retro sound effects for the game"""
        print("Creating awesome retro arcade sounds...")
        
        # Create laser sound - more like the classic arcade version
        self.generate_sound(
            "assets/laser.wav", 
            frequency=780,  # Lower base frequency for more classic sound
            duration=250,   # Shorter duration
            volume=0.5, 
            sweep_end=2000, # Much higher sweep range for that classic rising pew
            wave_type="square",  # Square wave for more classic arcade sound
            filter_freq=0,  # No filter for sharper sound
            pulse_freq=0,   # No pulse
            modulation_depth=0,  # No vibrato
            envelope=[0.0, 1.0, 0.0, 0.0],  # Quick attack and decay with no sustain
            echo=False      # No echo for cleaner sound
        )
        
        # Create more complex explosion sound with multi-layered components
        # First, generate the main explosion
        self.generate_sound(
            "assets/explosion_main.wav", 
            frequency=90,  # Lower base frequency for rumble
            duration=950, 
            volume=0.8, 
            noise=True,
            noise_mix=0.85,  # More noise than tone
            filter_freq=700,  # Low-pass filter for rumble
            envelope=[0.0, 1.0, 0.2, 0.0],  # Fast attack, rapid decay
            echo=True  # Add echo for room ambience
        )
        
        # Then create debris/shrapnel sounds
        self.generate_sound(
            "assets/explosion_debris.wav", 
            frequency=350, 
            duration=850, 
            volume=0.5, 
            noise=True,
            noise_mix=0.7,
            filter_freq=1200,
            envelope=[0.2, 0.8, 0.6, 0.0],  # Delayed attack
            echo=True,
            pulse_freq=4  # Pulsing for scattered debris sounds
        )
        
        # Mix the two explosion components
        self.mix_sounds(
            ["assets/explosion_main.wav", "assets/explosion_debris.wav"],
            "assets/explosion.wav",
            volumes=[1.0, 0.7],  # Main explosion louder than debris
            delays=[0, 100]  # Debris starts 100ms after main explosion
        )
        
        # Create thrust sound - complex engine rumble with harmonic richness
        self.generate_sound(
            "assets/thrust.wav", 
            frequency=90,  # Low frequency
            duration=1200, 
            volume=0.5, 
            noise=True,
            noise_mix=0.6,  # Mix of noise and tone
            filter_freq=250,  # Heavy low-pass for rumble
            pulse_freq=12,  # Fast pulsing for engine cycling
            wave_type="square",  # Square wave for more harmonics
            modulation_depth=10  # Add some frequency modulation for texture
        )
        
        # Create game over sound - dramatic synth chord with descending pitch
        self.generate_arpeggio(
            "assets/game_over.wav",
            notes=[
                440, 349.23, 261.63,  # A4, F4, C4
                220, 174.61, 130.81   # A3, F3, C3 (one octave lower)
            ],
            durations=[300, 300, 300, 400, 400, 500],  # Gradually longer notes
            volume=0.6,
            wave_type="triangle",
            echo=True
        )
        
        # Create level up sound - ascending pattern with flourish
        self.generate_arpeggio(
            "assets/level_up_base.wav",
            notes=[392.00, 493.88, 587.33, 698.46, 880.00],  # G4, B4, D5, F5, A5 (G major)
            durations=[90, 90, 90, 90, 350],  # Quick arpeggio with sustained final note
            volume=0.5,
            wave_type="sine"
        )
        
        # Add a synth flourish at the end for celebration
        self.generate_sound(
            "assets/level_up_flourish.wav", 
            frequency=880, 
            duration=500, 
            volume=0.4, 
            wave_type="triangle",
            modulation_depth=40,  # Heavy vibrato
            pulse_freq=8,
            envelope=[0.1, 1.0, 0.7, 0.0],  # Delayed attack for layering
            filter_freq=5000  # High-pass to keep it bright
        )
        
        # Mix base level up with flourish
        self.mix_sounds(
            ["assets/level_up_base.wav", "assets/level_up_flourish.wav"],
            "assets/level_up.wav", 
            volumes=[1.0, 0.8],
            delays=[0, 400]  # Flourish comes in after the arpeggio
        )
        
        # Create a special asteroid hit sound
        self.generate_sound(
            "assets/asteroid_hit.wav",
            frequency=240,
            duration=350,
            volume=0.5,
            noise=True,
            noise_mix=0.6,
            filter_freq=600,
            envelope=[0.0, 1.0, 0.3, 0.0],  # Fast attack
            echo=False
        )
        
        print("All sounds created successfully! Enjoy the awesome retro audio!")
    
    def mix_sounds(self, input_files, output_file, volumes=None, delays=None):
        """Mix multiple sound files together with optional volume scaling and delays"""
        if volumes is None:
            volumes = [1.0] * len(input_files)
        if delays is None:
            delays = [0] * len(input_files)
        
        # Load all input files
        waves = []
        max_length = 0
        sample_rate = 44100
        
        for i, file in enumerate(input_files):
            try:
                import wave
                with wave.open(file, 'rb') as wf:
                    frames = wf.getnframes()
                    buffer = wf.readframes(frames)
                    # Calculate actual length including delay
                    length = frames + int(delays[i] * (sample_rate / 1000.0))
                    max_length = max(max_length, length)
                    rate = wf.getframerate()
                    if rate != sample_rate:
                        print(f"Warning: {file} has sample rate {rate}, expected {sample_rate}")
                    waves.append((buffer, frames, delays[i]))
            except Exception as e:
                print(f"Error loading {file}: {e}")
                return
        
        # Create output buffer
        output_buffer = bytearray(max_length)
        for i in range(max_length):
            output_buffer[i] = 128  # Initialize to silence (8-bit wav)
        
        # Mix all sounds
        for i, (buffer, frames, delay) in enumerate(waves):
            delay_samples = int(delay * (sample_rate / 1000.0))
            volume = volumes[i]
            
            for j in range(frames):
                if j + delay_samples < max_length:
                    # Mix 8-bit samples with volume scaling
                    sample = buffer[j]
                    # Convert 8-bit (0-255) to signed (-128 to 127)
                    signed_sample = sample - 128
                    # Apply volume
                    scaled_sample = int(signed_sample * volume)
                    
                    # Add to existing output (mixing)
                    current = output_buffer[j + delay_samples] - 128
                    mixed = current + scaled_sample
                    # Clamp to valid range
                    mixed = max(-128, min(127, mixed))
                    # Convert back to 8-bit
                    output_buffer[j + delay_samples] = mixed + 128
        
        # Save mixed file
        try:
            import wave
            with wave.open(output_file, 'wb') as wf:
                wf.setnchannels(1)  # Mono
                wf.setsampwidth(1)  # 8-bit
                wf.setframerate(sample_rate)
                wf.writeframes(output_buffer)
            print(f"Created mixed sound: {output_file}")
        except Exception as e:
            print(f"Error saving mixed sound {output_file}: {e}")

    def generate_sound(self, filename, frequency=440, duration=500, volume=0.5, 
                      sweep_end=None, noise=False, noise_mix=1.0, wave_type="sine",
                      filter_freq=None, envelope=None, echo=False, modulation_depth=0,
                      pulse_freq=0):
        """Generate a custom sound file with various effects"""
        sample_rate = 44100
        bits = 16
        
        num_samples = int(duration * (sample_rate / 1000.0))
        raw_buffer = []
        
        # Default envelope (ADSR: Attack, Decay, Sustain, Release)
        if envelope is None:
            envelope = [0.0, 1.0, 0.8, 0.0]  # Default [attack_level, peak_level, sustain_level, release_level]
        
        attack_point = int(num_samples * 0.1)  # 10% attack
        decay_point = int(num_samples * 0.2)   # 20% decay
        sustain_point = int(num_samples * 0.6)  # 60% sustain
        # Rest is release
        
        # Generate the waveform
        for i in range(num_samples):
            # Apply envelope
            if i < attack_point:
                env_amplitude = envelope[0] + (envelope[1] - envelope[0]) * (i / attack_point)
            elif i < decay_point:
                env_amplitude = envelope[1] - (envelope[1] - envelope[2]) * ((i - attack_point) / (decay_point - attack_point))
            elif i < sustain_point:
                env_amplitude = envelope[2]
            else:
                env_amplitude = envelope[2] - (envelope[2] - envelope[3]) * ((i - sustain_point) / (num_samples - sustain_point))
            
            # Calculate the frequency with sweep if specified
            if sweep_end:
                freq = frequency + (sweep_end - frequency) * (i / num_samples)
            else:
                freq = frequency
            
            # Add vibrato if modulation_depth > 0
            if modulation_depth > 0:
                vibrato = math.sin(2 * math.pi * 5 * i / sample_rate) * modulation_depth  # 5 Hz vibrato
                freq += vibrato
            
            # Apply pulse amplitude modulation if needed
            pulse_mod = 1.0
            if pulse_freq > 0:
                pulse_mod = 0.7 + 0.3 * math.sin(2 * math.pi * pulse_freq * i / sample_rate)
            
            # Generate base waveform
            period = sample_rate / max(20, freq)  # Avoid division by zero or negative values
            phase = (i % period) / period
            
            # Generate different waveforms
            if wave_type == "sine":
                tone_value = math.sin(2 * math.pi * phase)
            elif wave_type == "square":
                tone_value = 1.0 if phase < 0.5 else -1.0
            elif wave_type == "sawtooth":
                tone_value = 2.0 * phase - 1.0
            elif wave_type == "triangle":
                tone_value = 4.0 * abs(phase - 0.5) - 1.0
            else:  # Default to sine
                tone_value = math.sin(2 * math.pi * phase)
            
            # Generate noise if needed
            if noise:
                noise_value = random.uniform(-1.0, 1.0)
                # Mix tone and noise according to noise_mix ratio
                value = (noise_value * noise_mix + tone_value * (1 - noise_mix))
            else:
                value = tone_value
            
            # Apply filter if specified (simple low-pass)
            if filter_freq and i > 0:
                cutoff = min(1.0, filter_freq / (sample_rate / 2))
                alpha = 0.95 * cutoff
                value = alpha * value + (1 - alpha) * raw_buffer[-1]
            
            # Apply envelope and volume
            value = int(32767 * value * env_amplitude * volume * pulse_mod)
            
            # Clamp value to 16-bit range
            value = max(-32767, min(32767, value))
            raw_buffer.append(value)
        
        # Apply echo effect if specified
        if echo:
            echo_buffer = list(raw_buffer)
            delay_samples = int(sample_rate * 0.1)  # 100ms delay
            decay = 0.5  # Echo volume
            
            for i in range(delay_samples, num_samples):
                echo_buffer[i] += int(raw_buffer[i - delay_samples] * decay)
                # Clamp again
                echo_buffer[i] = max(-32767, min(32767, echo_buffer[i]))
            
            raw_buffer = echo_buffer
        
        # Convert to 8-bit unsigned format
        buf = bytearray(num_samples)
        for i in range(num_samples):
            buf[i] = ((raw_buffer[i] + 32767) >> 8) & 0xFF
        
        # Save as WAV file
        try:
            import wave
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(1)  # Mono
                wf.setsampwidth(1)  # 8-bit
                wf.setframerate(sample_rate)
                wf.writeframes(buf)
            print(f"Created awesome sound: {filename}")
        except Exception as e:
            print(f"Error generating sound {filename}: {e}")

    def generate_arpeggio(self, filename, notes, durations=None, volume=0.5, wave_type="sine", sparkle=False, echo=False):
        """Generate an arpeggio/melody from a sequence of notes"""
        sample_rate = 44100
        
        if durations is None:
            durations = [150] * len(notes)  # Default 150ms per note
        
        # Calculate total samples
        total_duration = sum(durations)
        num_samples = int(total_duration * (sample_rate / 1000.0))
        raw_buffer = []
        
        # Track current position in the sample buffer
        pos = 0
        
        # Generate each note
        for i, (note, duration) in enumerate(zip(notes, durations)):
            note_samples = int(duration * (sample_rate / 1000.0))
            
            # Apply envelope for each note
            attack = int(note_samples * 0.2)
            decay = int(note_samples * 0.1)
            sustain = int(note_samples * 0.5)
            release = note_samples - attack - decay - sustain
            
            for j in range(note_samples):
                # Envelope
                if j < attack:
                    env = j / attack
                elif j < attack + decay:
                    env = 1.0 - 0.2 * (j - attack) / decay
                elif j < attack + decay + sustain:
                    env = 0.8
                else:
                    env = 0.8 * (1 - (j - attack - decay - sustain) / release)
                
                # Generate waveform
                period = sample_rate / note
                phase = ((pos + j) % period) / period
                
                if wave_type == "sine":
                    value = math.sin(2 * math.pi * phase)
                elif wave_type == "square":
                    value = 1.0 if phase < 0.5 else -1.0
                elif wave_type == "sawtooth":
                    value = 2.0 * phase - 1.0
                elif wave_type == "triangle":
                    value = 4.0 * abs(phase - 0.5) - 1.0
                else:
                    value = math.sin(2 * math.pi * phase)
                
                # Add sparkle effect (high frequency sine beeps) if enabled
                if sparkle and random.random() < 0.05:  # 5% chance per sample
                    sparkle_freq = random.randint(2000, 8000)
                    sparkle_phase = ((pos + j) % (sample_rate / sparkle_freq)) / (sample_rate / sparkle_freq)
                    sparkle_value = math.sin(2 * math.pi * sparkle_phase) * 0.3  # 30% volume
                    value = value * 0.7 + sparkle_value  # Mix with main tone
                
                # Apply volume and envelope
                value = int(32767 * value * env * volume)
                
                # Clamp value
                value = max(-32767, min(32767, value))
                raw_buffer.append(value)
            
            pos += note_samples
        
        # Apply echo effect if specified
        if echo:
            echo_buffer = list(raw_buffer)
            delay_samples = int(sample_rate * 0.15)  # 150ms delay
            decay = 0.4  # Echo volume
            
            for i in range(delay_samples, num_samples):
                echo_buffer[i] += int(raw_buffer[i - delay_samples] * decay)
                # Clamp again
                echo_buffer[i] = max(-32767, min(32767, echo_buffer[i]))
            
            raw_buffer = echo_buffer
        
        # Convert to 8-bit unsigned format
        buf = bytearray(num_samples)
        for i in range(num_samples):
            buf[i] = ((raw_buffer[i] + 32767) >> 8) & 0xFF
        
        # Save as WAV file
        try:
            import wave
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(1)  # Mono
                wf.setsampwidth(1)  # 8-bit
                wf.setframerate(sample_rate)
                wf.writeframes(buf)
            print(f"Created awesome arpeggio: {filename}")
        except Exception as e:
            print(f"Error generating arpeggio {filename}: {e}")

    def generate_simple_music(self):
        """Generate a lofi techno chillwave 90s arcade music track"""
        try:
            print("Creating epic 90s lofi techno chillwave background music...")
            sample_rate = 44100
            duration = 30000  # 30 seconds loop for more variety
            
            num_samples = int(duration * (sample_rate / 1000.0))
            raw_buffer = [0] * num_samples  # Pre-allocate with silence
            
            # Define a more complex chord progression with jazz-inspired voicings
            # Using F minor / Ab major pentatonic as base (F, Ab, Bb, C, Eb)
            
            # Bass notes with passing tones for more movement
            bass_progressions = [
                # Fm7 - Bbm7 - Ebmaj7 - Ab6
                [174.61, 174.61, 174.61, 185.00, 233.08, 233.08, 233.08, 220.00, 
                 311.13, 311.13, 311.13, 293.66, 207.65, 207.65, 220.00, 233.08],
                
                # Cm7 - Fm7 - Bbm7 - G7b9
                [130.81, 130.81, 146.83, 130.81, 174.61, 174.61, 174.61, 185.00,
                 233.08, 233.08, 220.00, 196.00, 196.00, 196.00, 185.00, 174.61],
                
                # Abmaj7 - Db6 - Gm7b5 - C7
                [207.65, 207.65, 207.65, 196.00, 277.18, 277.18, 277.18, 261.63,
                 196.00, 196.00, 185.00, 196.00, 261.63, 261.63, 233.08, 246.94],
                
                # Fm9 - Ebmaj7#11 - Dm7b5 - G7alt
                [174.61, 174.61, 174.61, 185.00, 155.56, 155.56, 155.56, 164.81,
                 146.83, 146.83, 146.83, 138.59, 196.00, 196.00, 207.65, 185.00]
            ]
            
            # Synth pad chord voicings with extensions for richness
            # Each chord is a collection of frequencies that form the harmony
            pad_chords = [
                # Fm7 - Bbm7 - Ebmaj7 - Ab6 (first progression)
                [
                    [174.61, 220.00, 261.63, 349.23],  # Fm7 (F, A♭, C, E♭)
                    [233.08, 293.66, 349.23, 415.30],  # B♭m7 (B♭, D♭, F, A♭)
                    [311.13, 392.00, 466.16, 523.25],  # E♭maj7 (E♭, G, B♭, D)
                    [207.65, 261.63, 349.23, 415.30]   # A♭6 (A♭, C, E♭, F)
                ],
                
                # Cm7 - Fm7 - Bbm7 - G7b9 (second progression)
                [
                    [130.81, 155.56, 196.00, 261.63],  # Cm7 (C, E♭, G, B♭)
                    [174.61, 220.00, 261.63, 329.63],  # Fm7 (F, A♭, C, E♭)
                    [233.08, 293.66, 349.23, 415.30],  # B♭m7 (B♭, D♭, F, A♭)
                    [196.00, 246.94, 293.66, 415.30]   # G7b9 (G, B, D, F, A♭)
                ],
                
                # Abmaj7 - Db6 - Gm7b5 - C7 (third progression)
                [
                    [207.65, 261.63, 311.13, 392.00],  # A♭maj7 (A♭, C, E♭, G)
                    [277.18, 349.23, 415.30, 466.16],  # D♭6 (D♭, F, A♭, B♭)
                    [196.00, 233.08, 293.66, 369.99],  # Gm7♭5 (G, B♭, D♭, F)
                    [261.63, 329.63, 392.00, 466.16]   # C7 (C, E, G, B♭)
                ],
                
                # Fm9 - Ebmaj7#11 - Dm7b5 - G7alt (fourth progression)
                [
                    [174.61, 220.00, 261.63, 349.23, 392.00],  # Fm9 (F, A♭, C, E♭, G)
                    [155.56, 196.00, 233.08, 329.63, 369.99],  # E♭maj7#11 (E♭, G, B♭, D, A)
                    [146.83, 174.61, 220.00, 293.66],          # Dm7♭5 (D, F, A♭, C)
                    [196.00, 246.94, 311.13, 369.99, 415.30]   # G7alt (G, B, D♭, F, A♭)
                ]
            ]
            
            # Define F minor pentatonic scale patterns for melodies
            # F minor pentatonic: F, Ab, Bb, C, Eb
            f_minor_pentatonic = [349.23, 415.30, 466.16, 523.25, 622.25]  # F4, Ab4, Bb4, C5, Eb5
            
            # Create melodic patterns using the pentatonic scale
            # Mix of stepwise motion, skips, and directional contours for more interest
            melody_patterns = [
                # Pattern 1: Rising then falling line with rhythmic variation
                [f_minor_pentatonic[0], f_minor_pentatonic[1], f_minor_pentatonic[3], f_minor_pentatonic[4], 
                 f_minor_pentatonic[4], f_minor_pentatonic[3], f_minor_pentatonic[1], f_minor_pentatonic[0]],
                
                # Pattern 2: Arpeggiated with octave jumps
                [f_minor_pentatonic[0], f_minor_pentatonic[2], f_minor_pentatonic[4], f_minor_pentatonic[0]*2, 
                 f_minor_pentatonic[4], f_minor_pentatonic[2], f_minor_pentatonic[1], f_minor_pentatonic[0]],
                
                # Pattern 3: Syncopated rhythm with call and response
                [f_minor_pentatonic[0], 0, f_minor_pentatonic[2], 0, 
                 f_minor_pentatonic[3], f_minor_pentatonic[3], 0, f_minor_pentatonic[1]],
                
                # Pattern 4: Descending cascade with repeated notes
                [f_minor_pentatonic[4], f_minor_pentatonic[3], f_minor_pentatonic[3], f_minor_pentatonic[2], 
                 f_minor_pentatonic[2], f_minor_pentatonic[1], f_minor_pentatonic[0], 0]
            ]
            
            # Lead patterns using upper octave pentatonic notes for fills
            # Adding some blue notes (E natural, between Eb and F) for jazz feel
            lead_fill_patterns = [
                # Fill 1: Quick ascending run with blue note
                [f_minor_pentatonic[0], f_minor_pentatonic[1], f_minor_pentatonic[2], f_minor_pentatonic[3], 
                 f_minor_pentatonic[4], f_minor_pentatonic[0]*2, 659.26, f_minor_pentatonic[0]*2],  # 659.26 is E5 (blue note)
                
                # Fill 2: Descending with repeated high notes
                [f_minor_pentatonic[0]*2, f_minor_pentatonic[4], f_minor_pentatonic[4], f_minor_pentatonic[3],
                 f_minor_pentatonic[2], f_minor_pentatonic[1], f_minor_pentatonic[1], f_minor_pentatonic[0]],
                
                # Fill 3: Triplet feel with pentatonic jumps
                [f_minor_pentatonic[0], f_minor_pentatonic[2], f_minor_pentatonic[4], f_minor_pentatonic[2],
                 f_minor_pentatonic[3], f_minor_pentatonic[1], f_minor_pentatonic[2], f_minor_pentatonic[0]],
                
                # Fill 4: Jazzy chromatic approach notes
                [f_minor_pentatonic[0], f_minor_pentatonic[0]*0.94, f_minor_pentatonic[0], f_minor_pentatonic[1],
                 f_minor_pentatonic[2], f_minor_pentatonic[2]*1.06, f_minor_pentatonic[2], f_minor_pentatonic[0]]
            ]
            
            # Define drum patterns with more dynamic variation
            # 1 = kick, 2 = snare, 3 = hihat closed, 4 = hihat open, 5 = rim, 6 = shaker
            drum_patterns = [
                # Main groove with rim
                [1, 0, 3, 5, 2, 0, 3, 4, 0, 6, 3, 0, 2, 5, 3, 0],
                
                # Variation with more kicks
                [1, 0, 3, 0, 2, 1, 3, 0, 1, 0, 3, 4, 2, 0, 3, 6],
                
                # Breakdown with space
                [1, 0, 0, 0, 2, 0, 3, 0, 0, 6, 3, 0, 2, 0, 0, 4],
                
                # Fill pattern
                [1, 3, 6, 3, 2, 3, 0, 3, 1, 3, 5, 3, 2, 2, 2, 2]
            ]
            
            # More complex drum sounds with layered components - INCREASED VOLUMES
            def get_kick(time, duration=80):
                t = time % duration
                if t < duration * 0.1:
                    # Main body with frequency sweep
                    body = math.sin(2 * math.pi * (120 - t * 2)) * (1 - t/(duration * 0.1))
                    # Add click transient
                    click = math.sin(2 * math.pi * 1800 * t / sample_rate) * math.exp(-t / 4)
                    return body * 0.85 + click * 0.15
                return 0
            
            def get_snare(time, duration=80):
                t = time % duration
                env = math.exp(-t / (duration * 0.15))
                # Body tone
                tone = math.sin(2 * math.pi * 180 * t / sample_rate) * env * 0.2
                # Noise component with bandpass effect
                noise = random.uniform(-1, 1) * math.exp(-t / (duration * 0.1)) * 0.7
                # Lower noise for body
                body_noise = random.uniform(-0.5, 0.5) * math.exp(-t / (duration * 0.2)) * 0.3
                return tone + noise + body_noise
            
            def get_hihat_closed(time, duration=40):
                t = time % duration
                env = math.exp(-t / (duration * 0.08))  # Faster decay
                # High-frequency noise with subtle resonance
                noise = random.uniform(-0.7, 0.7) * env
                # Add subtle tone at around 8-10kHz
                tone = math.sin(2 * math.pi * 9000 * t / sample_rate) * env * 0.1
                return noise * 0.6 + tone * 0.1
            
            def get_hihat_open(time, duration=120):
                t = time % duration
                env = math.exp(-t / (duration * 0.4))  # Longer decay than closed
                # Similar to closed hihat but with longer decay
                noise = random.uniform(-0.7, 0.7) * env
                tone = math.sin(2 * math.pi * 8500 * t / sample_rate) * env * 0.1
                return noise * 0.5 + tone * 0.1
            
            def get_rim(time, duration=60):
                t = time % duration
                env = math.exp(-t / (duration * 0.05))  # Very short decay
                # Sharp attack with mid-range tone
                tone = math.sin(2 * math.pi * 800 * t / sample_rate) * env
                return tone * 0.4
            
            def get_shaker(time, duration=70):
                t = time % duration
                env = math.exp(-t / (duration * 0.15))
                # Filtered high-frequency noise
                return random.uniform(-0.5, 0.5) * env * 0.25
            
            # Time parameters (in milliseconds)
            beat_ms = 125  # 120 BPM (500ms per beat, 125ms per 16th note)
            beats_per_pattern = 16  # 16 16th notes per pattern
            pattern_duration = beat_ms * beats_per_pattern
            pattern_samples = int(pattern_duration * (sample_rate / 1000.0))
            num_patterns = duration // pattern_duration
            
            # Filter state for lo-fi effect
            prev_sample = 0
            filter_alpha = 0.3  # Low-pass filter coefficient
            high_freq_prev = 0  # For high-pass filter
            high_freq_alpha = 0.05  # High-pass filter coefficient
            
            # Track metrics for variation
            fill_counter = 0
            
            # Generate patterns
            for pattern_idx in range(int(num_patterns)):
                # Determine if this should be a fill pattern (every 4th pattern)
                is_fill = (pattern_idx % 4 == 3)
                fill_counter = (fill_counter + 1) % 4
                
                # Get the current patterns based on sequence with variation
                progression_idx = pattern_idx % len(bass_progressions)
                current_bass = bass_progressions[progression_idx]
                current_pads = pad_chords[progression_idx]
                
                # Alternate between melody and lead fills
                if is_fill:
                    current_melody = lead_fill_patterns[fill_counter % len(lead_fill_patterns)]
                else:
                    current_melody = melody_patterns[pattern_idx % len(melody_patterns)]
                
                # Rotate drum patterns for variation
                if is_fill:
                    current_drums = drum_patterns[3]  # Always use fill pattern for fills
                else:
                    current_drums = drum_patterns[pattern_idx % (len(drum_patterns) - 1)]
                
                # Generate each 16th note
                for beat in range(beats_per_pattern):
                    beat_start = int((pattern_idx * pattern_duration + beat * beat_ms) * (sample_rate / 1000.0))
                    beat_end = int(beat_start + beat_ms * (sample_rate / 1000.0))
                    
                    # Limit to buffer size
                    if beat_end > num_samples:
                        beat_end = num_samples
                    
                    # Current notes from patterns
                    bass_idx = beat % len(current_bass)
                    bass_freq = current_bass[bass_idx]
                    
                    chord_idx = beat // 4  # Change chord every quarter note
                    if chord_idx >= len(current_pads):
                        chord_idx = len(current_pads) - 1
                    
                    # Get pad chord - now properly handled as a list of frequencies
                    pad_chord = current_pads[chord_idx]
                    
                    # Get melody note with rhythmic variation
                    play_melody = True
                    if beat < len(current_melody):
                        melody_freq = current_melody[beat]
                        if melody_freq == 0:  # Rest
                            play_melody = False
                    else:
                        melody_freq = current_melody[0]  # Default to first note
                    
                    # Get drum hit for this beat
                    drum_hit = 0
                    if beat < len(current_drums):
                        drum_hit = current_drums[beat]
                    
                    # Generate samples for this beat
                    for i in range(beat_start, beat_end):
                        if i >= num_samples:
                            break
                            
                        sample_idx = i - beat_start
                        beat_progress = sample_idx / (beat_end - beat_start)
                        beat_samples = beat_end - beat_start
                        
                        value = 0
                        
                        # Add bass with more complex waveform mixing
                        if bass_freq > 0:  # Check for rests
                            bass_phase = ((i % (sample_rate / bass_freq)) / (sample_rate / bass_freq))
                            # Mix sine and triangle for richer bass timbre
                            bass_sine = math.sin(2 * math.pi * bass_phase)
                            bass_triangle = 4.0 * abs(bass_phase - 0.5) - 1.0
                            bass_value = bass_sine * 0.7 + bass_triangle * 0.3
                            
                            # Add subtle overdrive and compression
                            bass_value = math.tanh(bass_value * 1.8) * 0.7
                            
                            # Dynamic envelope: emphasize downbeats, softer for other beats
                            if beat % 4 == 0:  # Downbeat
                                bass_env = 0.95
                            elif beat % 2 == 0:  # Off-beat emphasis
                                bass_env = 0.75
                            else:  # Other 16ths
                                bass_env = 0.6
                                
                            value += bass_value * bass_env * 0.38  # Slightly higher volume
                        
                        # Add pad chords with rich harmonic texture and slow attack
                        # Each pad_chord is now properly a list of frequencies
                        pad_notes = pad_chord  # pad_chord is already a list of frequencies
                        
                        # Determine pad envelope - longer attack at pattern boundaries
                        if beat < 2 and pattern_idx % 2 == 0:
                            pad_attack_time = sample_rate * 0.2  # 200ms attack
                        else:
                            pad_attack_time = sample_rate * 0.1  # 100ms attack
                            
                        pad_env = min(1.0, (pattern_idx * pattern_samples + i - beat_start) / pad_attack_time)
                        pad_value = 0
                        
                        # Mix all notes in the chord with different waveforms for richness
                        for j, pad_note in enumerate(pad_notes):
                            pad_phase = ((i % (sample_rate / pad_note)) / (sample_rate / pad_note))
                            
                            # Alternate between triangle and sine for different chord tones
                            if j % 3 == 0:
                                # Triangle wave for some notes
                                note_value = 4.0 * abs(pad_phase - 0.5) - 1.0
                            elif j % 3 == 1:
                                # Sine wave for some notes
                                note_value = math.sin(2 * math.pi * pad_phase)
                            else:
                                # Soft square-ish wave for some notes (more mellow)
                                note_value = math.tanh(math.sin(2 * math.pi * pad_phase) * 2.5) * 0.8
                                
                            # Add subtle detuning for chorus/ensemble effect
                            detune = 0.05 * math.sin(2 * math.pi * 0.3 * i / sample_rate + j)
                            note_value = note_value * (1 + detune)
                            
                            # Weight higher chord tones a bit softer
                            note_weight = 1.0 - (j * 0.1)
                            if note_weight < 0.5:
                                note_weight = 0.5
                                
                            pad_value += note_value * note_weight / len(pad_notes)
                        
                        # Add subtle modulation to pad
                        mod_depth = 0.05 + 0.03 * math.sin(2 * math.pi * 0.1 * i / sample_rate)
                        pad_value = pad_value * (1 + mod_depth)
                        
                        # Add to mix with envelope
                        value += pad_value * pad_env * 0.22  # Pad volume
                        
                        # Add melody/lead with more expressive articulation
                        if play_melody and melody_freq > 0:
                            # Variable envelope based on pattern and position
                            if is_fill:  # Shorter, more staccato for fills
                                melody_env = math.exp(-sample_idx / (beat_samples * 0.5))
                            else:  # More sustained for main melody
                                if beat % 4 == 0:  # Longer notes on downbeats
                                    melody_env = math.exp(-sample_idx / (beat_samples * 0.9))
                                else:  # Shorter notes elsewhere
                                    melody_env = math.exp(-sample_idx / (beat_samples * 0.7))
                            
                            # Calculate phase
                            melody_phase = ((i % (sample_rate / melody_freq)) / (sample_rate / melody_freq))
                            
                            # Use softer sawtooth for lead sound
                            melody_raw = 2.0 * melody_phase - 1.0  # Sawtooth
                            melody_value = math.tanh(melody_raw * 1.5) * 0.8  # Soft clip for warmth
                            
                            # Apply subtle vibrato that increases with time
                            vibrato_depth = 0.02 * min(1.0, sample_idx / (beat_samples * 0.3))
                            vibrato = vibrato_depth * math.sin(2 * math.pi * 6 * i / sample_rate)  # 6 Hz vibrato
                            melody_value = melody_value * (1 + vibrato)
                            
                            # Add to mix
                            value += melody_value * melody_env * 0.2
                        
                        # Add drums with more realistic transients and layering - INCREASED VOLUMES
                        if drum_hit > 0:
                            if drum_hit == 1:  # Kick
                                drum_value = get_kick(sample_idx) * 1.2  # Increased from 0.7 to 1.2
                            elif drum_hit == 2:  # Snare
                                drum_value = get_snare(sample_idx) * 0.9  # Increased from 0.5 to 0.9
                            elif drum_hit == 3:  # Hi-hat closed
                                drum_value = get_hihat_closed(sample_idx) * 0.8  # Increased from 0.4 to 0.8
                            elif drum_hit == 4:  # Hi-hat open
                                drum_value = get_hihat_open(sample_idx) * 0.6  # Increased from 0.3 to 0.6
                            elif drum_hit == 5:  # Rim
                                drum_value = get_rim(sample_idx) * 0.7  # Increased from 0.35 to 0.7
                            elif drum_hit == 6:  # Shaker
                                drum_value = get_shaker(sample_idx) * 0.6  # Increased from 0.3 to 0.6
                            else:
                                drum_value = 0
                            
                            value += drum_value
                        
                        # Add vinyl crackle effect for lo-fi aesthetic - REDUCED
                        if random.random() < 0.003:  # Reduced from 0.008 to 0.003
                            crackle = random.uniform(-0.01, 0.01)  # Reduced from -0.03/0.03 to -0.01/0.01
                            value += crackle
                        
                        # Add subtle tape hiss background - REDUCED
                        if random.random() < 0.2:  # Reduced from 0.4 to 0.2
                            hiss = random.uniform(-0.001, 0.001)  # Reduced from -0.003/0.003 to -0.001/0.001
                            value += hiss
                        
                        # Apply multi-band processing for lo-fi effect
                        
                        # Low-pass filter for warm, lo-fi sound (main filter)
                        value = value * (1 - filter_alpha) + prev_sample * filter_alpha
                        prev_sample = value
                        
                        # High-pass filter to remove excessive low end
                        high_passed = value - high_freq_prev
                        high_freq_prev = high_freq_prev * (1 - high_freq_alpha) + value * high_freq_alpha
                        
                        # Mix back some high-passed content
                        value = value * 0.85 + high_passed * 0.15
                        
                        # Add subtle compression and saturation for "cassette" effect
                        value = math.tanh(value * 1.25) * 0.85
                        
                        # Scale to 16-bit range and add to buffer
                        scaled_value = int(value * 32767 * 0.8)  # Increased from 0.7 to 0.8 for overall volume
                        scaled_value = max(-32767, min(32767, scaled_value))
                        raw_buffer[i] = scaled_value
            
            # Apply final mastering effects
            
            # 1. Slight normalization to maximize volume
            max_value = max(max(raw_buffer), abs(min(raw_buffer)))
            if max_value > 0:
                scale_factor = 30000 / max_value  # Leave some headroom
                for i in range(len(raw_buffer)):
                    raw_buffer[i] = int(raw_buffer[i] * scale_factor)
                    raw_buffer[i] = max(-32767, min(32767, raw_buffer[i]))
            
            # 2. Apply crossfade between start and end for seamless looping
            crossfade_duration = int(sample_rate * 1.5)  # 1.5 second crossfade
            for i in range(crossfade_duration):
                if i < crossfade_duration and i < len(raw_buffer) and num_samples - crossfade_duration + i < len(raw_buffer):
                    # Crossfade weight (using equal power crossfade)
                    weight = i / crossfade_duration
                    weight1 = math.cos(weight * math.pi / 2)
                    weight2 = math.sin(weight * math.pi / 2)
                    
                    # Mix start and end
                    end_value = raw_buffer[num_samples - crossfade_duration + i]
                    start_value = raw_buffer[i]
                    # Apply crossfade
                    raw_buffer[i] = int(start_value * weight1 + end_value * weight2)
            
            # Convert to 8-bit unsigned format for WAV file
            buf = bytearray(num_samples)
            for i in range(num_samples):
                buf[i] = ((raw_buffer[i] + 32767) >> 8) & 0xFF
            
            # Save as a WAV file
            music_file = "assets/lofi_soundtrack.wav"
            import wave
            with wave.open(music_file, 'wb') as wf:
                wf.setnchannels(1)  # Mono
                wf.setsampwidth(1)  # 8-bit
                wf.setframerate(sample_rate)
                wf.writeframes(buf)
            
            # Load the newly created music
            pygame.mixer.music.load(music_file)
            pygame.mixer.music.set_volume(0.4)
            pygame.mixer.music.play(-1)  # Loop indefinitely
            
            print(f"Epic 90s lofi techno chillwave background music created successfully! Now playing: {music_file}")
        except Exception as e:
            print(f"Error generating music: {e}")
            import traceback
            traceback.print_exc()
    
    def reset_game(self):
        """Reset the game to its initial state"""
        self.score = 0
        self.lives = 3
        self.level = 1
        
        # Clear game objects
        self.asteroids.empty()
        self.lasers.empty()
        
        # Switch fluid field to grid mode for gameplay
        self.fluid_field.set_mode("grid")
        
        # Create player ship if in PLAYING state
        if self.state == PLAYING:
            self.ship = Ship(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
            
            # Create initial asteroids - increased for larger screen
            self.create_asteroids(self.level + 7)  # Was level + 4
            
            # Play welcome announcement if first time playing
            if not self.welcome_played and tts_available:
                welcome_message = f"Welcome to Asteroids, {self.player_name}!"
                speak_text(welcome_message)
                self.welcome_played = True
                
                # Reset joke timer
                self.joke_timer = pygame.time.get_ticks()
    
    def create_asteroids(self, count):
        """Create a number of asteroids"""
        for _ in range(count):
            # Choose a spawn area outside the center of the screen
            spawn_area = random.random()
            
            if spawn_area < 0.25:
                # Top
                x = random.randint(0, SCREEN_WIDTH)
                y = -50
            elif spawn_area < 0.5:
                # Right
                x = SCREEN_WIDTH + 50
                y = random.randint(0, SCREEN_HEIGHT)
            elif spawn_area < 0.75:
                # Bottom
                x = random.randint(0, SCREEN_WIDTH)
                y = SCREEN_HEIGHT + 50
            else:
                # Left
                x = -50
                y = random.randint(0, SCREEN_HEIGHT)
                
            # Create the asteroid with random position and properties
            asteroid = Asteroid(x, y, level=random.randint(1, 3))  # Mix of asteroid sizes
            self.asteroids.add(asteroid)
        
        # Make sure there's at least one asteroid if count was 0
        if count == 0:
            x = random.randint(100, SCREEN_WIDTH - 100)
            y = random.randint(100, SCREEN_HEIGHT - 100)
            asteroid = Asteroid(x, y, level=1)
            self.asteroids.add(asteroid)
    
    def check_collisions(self):
        """Check for collisions between game objects"""
        # Check for laser-asteroid collisions
        for laser in self.lasers:
            hit_asteroids = pygame.sprite.spritecollide(laser, self.asteroids, True)
            
            if hit_asteroids:
                # Remove the laser
                laser.kill()
                
                for asteroid in hit_asteroids:
                    # Add points based on asteroid size
                    self.score += (4 - asteroid.level) * 100
                    
                    # Create explosion effect
                    explosion_size = 20 + (3 - asteroid.level) * 10  # Bigger explosions for bigger asteroids
                    self.explosion_system.create_explosion(
                        asteroid.rect.centerx, 
                        asteroid.rect.centery, 
                        explosion_size,
                        asteroid.color  # Base explosion on asteroid color
                    )
                    
                    # Play explosion sound
                    if "explosion" in self.sounds:
                        self.sounds["explosion"].play()
                    
                    # Create new asteroids if not the smallest level
                    if asteroid.level < 3:
                        for _ in range(2):
                            new_asteroid = Asteroid(asteroid.rect.centerx, asteroid.rect.centery, level=asteroid.level + 1)
                            self.asteroids.add(new_asteroid)
        
        # Check for ship-asteroid collisions (if ship exists and is not invulnerable)
        if self.ship and not self.ship.invulnerable:
            if pygame.sprite.spritecollide(self.ship, self.asteroids, False, pygame.sprite.collide_circle):
                # Player hit an asteroid
                self.lives -= 1
                
                # Create explosion effect at ship position
                self.explosion_system.create_explosion(
                    self.ship.rect.centerx, 
                    self.ship.rect.centery, 
                    30,  # Larger explosion for the ship
                    self.ship.color
                )
                
                # Play explosion sound
                if "explosion" in self.sounds:
                    self.sounds["explosion"].play()
                
                if self.lives <= 0:
                    # Game over
                    self.state = GAME_OVER
                    
                    # Play game over sound
                    if "game_over" in self.sounds:
                        self.sounds["game_over"].play()
                else:
                    # Reset the ship with invulnerability
                    self.ship = Ship(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                    self.ship.set_invulnerable()
    
    def check_level_complete(self):
        """Check if the current level is complete"""
        if len(self.asteroids) == 0:
            # Level complete
            self.level += 1
            
            # Add bonus points
            self.score += self.level * 1000
            
            # Create new asteroids for the next level - increased for larger screen
            self.create_asteroids(self.level + 7)  # Was level + 4
            
            # Debug output to console
            print(f"Level {self.level} started with {len(self.asteroids)} asteroids")
            
            # Play level up sound
            if "level_up" in self.sounds:
                self.sounds["level_up"].play()
            
            # Force a brief delay to show level transition
            pygame.time.delay(500)  # 500ms delay to show level transition
    
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            # Quit event
            if event.type == QUIT:
                return False
            
            # Key press events
            if event.type == KEYDOWN:
                # Global key events
                if event.key == K_ESCAPE:
                    return False
                
                # State-specific key events
                if self.state == TITLE_SCREEN:
                    if self.name_input_active:
                        # Handle name input
                        if event.key == K_RETURN:
                            if self.player_name:  # Only proceed if name is not empty
                                self.name_input_active = False
                        elif event.key == K_BACKSPACE:
                            self.player_name = self.player_name[:-1]
                        elif len(self.player_name) < 15:  # Limit name length
                            if event.unicode.isalnum() or event.unicode.isspace():
                                self.player_name += event.unicode
                    else:
                        if event.key == K_RETURN:
                            self.state = PLAYING
                            self.reset_game()  # Reset_game will switch to grid mode
                
                elif self.state == PLAYING:
                    if event.key == K_p:
                        self.state = PAUSED
                    
                    # Debug keys (only in play mode)
                    if event.key == K_r and pygame.key.get_mods() & KMOD_CTRL:
                        # Force respawn asteroids if stuck
                        old_count = len(self.asteroids)
                        self.asteroids.empty()
                        # Create new asteroids for current level
                        self.create_asteroids(self.level + 7)
                        print(f"DEBUG: Respawned asteroids ({old_count} → {len(self.asteroids)})")
                    
                    # Sound test key
                    if event.key == K_s and pygame.key.get_mods() & KMOD_CTRL:
                        # Test all sounds
                        self.test_all_sounds()
                        print("DEBUG: Testing all sounds")
                    
                    # Ship rotation and thrust controls
                    if self.ship:
                        if event.key == K_LEFT:
                            self.ship.rotate(1)  # Counterclockwise
                        if event.key == K_RIGHT:
                            self.ship.rotate(-1)  # Clockwise
                        if event.key == K_UP:
                            self.ship.thrust(True)
                            # Play thruster sound (loop)
                            if "thrust" in self.sounds and not pygame.mixer.get_busy():
                                self.sounds["thrust"].play(-1)  # Loop
                    
                    # Fire laser
                    if event.key == K_SPACE and self.ship:
                        # Create a new laser from the ship's position
                        laser_x = self.ship.rect.centerx + self.ship.radius * math.cos(math.radians(self.ship.angle))
                        laser_y = self.ship.rect.centery - self.ship.radius * math.sin(math.radians(self.ship.angle))
                        laser = Laser(laser_x, laser_y, self.ship.angle)
                        self.lasers.add(laser)
                        
                        # Play laser sound
                        if "laser" in self.sounds:
                            self.sounds["laser"].play()
                
                elif self.state == PAUSED:
                    if event.key == K_p:
                        self.state = PLAYING
                
                elif self.state == GAME_OVER:
                    if event.key == K_RETURN:
                        # When going back to title screen, switch fluid to swirl mode
                        self.fluid_field.set_mode("swirl")
                        self.state = TITLE_SCREEN
            
            # Key release events
            if event.type == KEYUP:
                if self.state == PLAYING and self.ship:
                    # Stop ship rotation or thrust when keys are released
                    if event.key == K_LEFT and self.ship.rotation_direction == 1:
                        self.ship.rotate(0)  # Stop rotation
                    if event.key == K_RIGHT and self.ship.rotation_direction == -1:
                        self.ship.rotate(0)  # Stop rotation
                    if event.key == K_UP:
                        self.ship.thrust(False)
                        # Stop thruster sound
                        if "thrust" in self.sounds:
                            self.sounds["thrust"].stop()
        
        # Remove the continuous key press handling for ship movement
        # to prevent unexpected behavior with the improved controls
        
        return True
    
    def test_all_sounds(self):
        """Play all sound effects for testing purposes"""
        # Play each sound with slight delay
        for name, sound in self.sounds.items():
            try:
                sound.play()
                print(f"Playing sound: {name}")
                pygame.time.delay(300)  # Wait 300ms between sounds
            except Exception as e:
                print(f"Error playing sound {name}: {e}")
        
        # Test music
        try:
            # Stop music if playing
            pygame.mixer.music.stop()
            # Start from beginning
            pygame.mixer.music.play()
            print("Restarted background music")
        except Exception as e:
            print(f"Error with music: {e}")
    
    def update(self):
        """Update game state"""
        # Update fluid field, passing ship if it exists and in playing state
        if self.state == PLAYING and self.ship:
            self.fluid_field.update(self.ship)
        else:
            self.fluid_field.update()
        
        # Only update game objects if playing
        if self.state == PLAYING:
            # Update player ship
            if self.ship:
                self.ship.update()
                
                # If ship is off screen and back on, reset invulnerability
                if self.ship.off_screen_time >= self.ship.max_off_screen_time:
                    self.ship.set_invulnerable()
            
            # Track asteroids that are too far from the screen
            off_screen_asteroids = []
            
            # Update asteroids
            for asteroid in self.asteroids:
                asteroid.update()
                
                # Screen wrapping for asteroids - increased margin for larger screen
                if asteroid.rect.left > SCREEN_WIDTH + 120:
                    asteroid.position.x = -asteroid.rect.width
                elif asteroid.rect.right < -120:
                    asteroid.position.x = SCREEN_WIDTH + asteroid.rect.width
                
                if asteroid.rect.top > SCREEN_HEIGHT + 120:
                    asteroid.position.y = -asteroid.rect.height
                elif asteroid.rect.bottom < -120:
                    asteroid.position.y = SCREEN_HEIGHT + asteroid.rect.height
                
                # Check if asteroid is too far from screen (safety check) - increased margins
                if (asteroid.rect.left > SCREEN_WIDTH + 250 or 
                    asteroid.rect.right < -250 or
                    asteroid.rect.top > SCREEN_HEIGHT + 250 or
                    asteroid.rect.bottom < -250):
                    off_screen_asteroids.append(asteroid)
            
            # Handle any asteroids that are too far off-screen
            for asteroid in off_screen_asteroids:
                # Reposition to a random edge of the screen
                edge = random.randint(0, 3)  # 0=top, 1=right, 2=bottom, 3=left
                
                if edge == 0:  # Top
                    asteroid.position.x = random.randint(0, SCREEN_WIDTH)
                    asteroid.position.y = -50
                elif edge == 1:  # Right
                    asteroid.position.x = SCREEN_WIDTH + 50
                    asteroid.position.y = random.randint(0, SCREEN_HEIGHT)
                elif edge == 2:  # Bottom
                    asteroid.position.x = random.randint(0, SCREEN_WIDTH)
                    asteroid.position.y = SCREEN_HEIGHT + 50
                else:  # Left
                    asteroid.position.x = -50
                    asteroid.position.y = random.randint(0, SCREEN_HEIGHT)
                
                # Update rect position
                asteroid.rect.center = (asteroid.position.x, asteroid.position.y)
                
                # Give it a new velocity toward the screen
                angle = math.atan2(SCREEN_HEIGHT/2 - asteroid.position.y, 
                                  SCREEN_WIDTH/2 - asteroid.position.x)
                speed = max(1.0, random.random() * 3.0)
                asteroid.velocity = pygame.Vector2(
                    math.cos(angle) * speed,
                    math.sin(angle) * speed
                )
            
            # Update lasers and remove those that are off-screen
            for laser in self.lasers:
                laser.update()
                
                if (laser.rect.right < 0 or laser.rect.left > SCREEN_WIDTH or
                    laser.rect.bottom < 0 or laser.rect.top > SCREEN_HEIGHT or
                    pygame.time.get_ticks() - laser.created_time > 1500):  # 1.5 seconds lifespan
                    laser.kill()
            
            # Update explosion particles
            self.explosion_system.update()
            
            # Check for collisions
            self.check_collisions()
            
            # Check if level is complete
            self.check_level_complete()
            
            # Update joke timer for voice overs
            current_time = pygame.time.get_ticks()
            if current_time - self.joke_timer >= self.joke_interval and tts_available and self.player_name:
                self.tell_joke()
                self.joke_timer = current_time
        
        # Update cursor blink for name input
        if self.state == TITLE_SCREEN and self.name_input_active:
            current_time = pygame.time.get_ticks()
            if current_time - self.name_input_cursor_time > 500:  # 500ms cursor blink rate
                self.name_input_cursor_visible = not self.name_input_cursor_visible
                self.name_input_cursor_time = current_time

    def tell_joke(self):
        """Tell a random yo mama joke with the player's name"""
        if not self.player_name:
            return
            
        # Choose a random joke that's different from the last one
        joke_index = random.randint(0, len(self.joke_templates) - 1)
        while joke_index == self.last_joke_index and len(self.joke_templates) > 1:
            joke_index = random.randint(0, len(self.joke_templates) - 1)
            
        self.last_joke_index = joke_index
        joke_template = self.joke_templates[joke_index]
        joke = joke_template.format(name=self.player_name)
        
        # Speak the joke
        speak_text(joke)
    
    def draw_title_screen(self):
        """Draw the title screen"""
        # Draw background first
        self.screen.fill(BLACK)
        
        # Draw fluid field first
        self.fluid_field.draw(self.screen)
        
        # Add scanline effect
        self.draw_scanlines()
        
        # Retro title with shadow effect
        title_text = self.title_font.render("ASTEROIDS", True, (0, 255, 255))  # Cyan
        title_shadow = self.title_font.render("ASTEROIDS", True, (255, 0, 255))  # Magenta shadow
        
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100))
        
        # Draw shadow offset
        shadow_rect = title_rect.copy()
        shadow_rect.x += 4
        shadow_rect.y += 4
        self.screen.blit(title_shadow, shadow_rect)
        
        # Draw main title
        self.screen.blit(title_text, title_rect)
        
        # Name input field
        if self.name_input_active:
            # Prompt
            name_prompt = self.info_font.render("Enter your name:", True, (255, 255, 0))
            name_prompt_rect = name_prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20))
            self.screen.blit(name_prompt, name_prompt_rect)
            
            # Input box
            input_box_rect = pygame.Rect(0, 0, 300, 40)
            input_box_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20)
            pygame.draw.rect(self.screen, (80, 80, 80), input_box_rect)
            pygame.draw.rect(self.screen, (255, 255, 255), input_box_rect, 2)
            
            # Display name
            display_name = self.player_name
            if self.name_input_cursor_visible:
                display_name += "|"
                
            name_text = self.info_font.render(display_name, True, (255, 255, 255))
            name_text_rect = name_text.get_rect(center=input_box_rect.center)
            self.screen.blit(name_text, name_text_rect)
            
            # Input instructions
            instructions = self.small_font.render("Press ENTER when done", True, (0, 255, 0))
            instructions_rect = instructions.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 70))
            self.screen.blit(instructions, instructions_rect)
            
            # Extra instructions about jokes
            joke_info = self.small_font.render("(Your name will be used in voice over jokes during gameplay)", True, (180, 180, 180))
            joke_info_rect = joke_info.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100))
            self.screen.blit(joke_info, joke_info_rect)
        else:
            # Instructions
            instructions1 = self.info_font.render("Use arrow keys to move and space to shoot", True, (255, 255, 0))
            instructions1_rect = instructions1.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
            self.screen.blit(instructions1, instructions1_rect)
            
            # Create blinking "Press ENTER" text
            if pygame.time.get_ticks() % 1000 < 800:  # Blink effect
                instructions2 = self.info_font.render("Press ENTER to start", True, (0, 255, 0))
                instructions2_rect = instructions2.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 70))
                self.screen.blit(instructions2, instructions2_rect)
    
    def draw_scanlines(self):
        """Draw retro scanline effect"""
        scanline_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        
        for y in range(0, SCREEN_HEIGHT, 3):
            pygame.draw.line(scanline_surface, (0, 0, 0, 30), (0, y), (SCREEN_WIDTH, y), 1)
        
        self.screen.blit(scanline_surface, (0, 0))
    
    def draw_game_screen(self):
        """Draw the main game screen"""
        # Draw background
        self.screen.fill(BLACK)
        
        # Draw fluid field
        self.fluid_field.draw(self.screen)
        
        # Draw lasers with trail effects
        for laser in self.lasers:
            laser.draw(self.screen)
        
        # Draw lasers sprites
        self.lasers.draw(self.screen)
        
        # Draw asteroids with custom draw method for trails
        for asteroid in self.asteroids:
            asteroid.draw(self.screen)
        
        # Draw explosion particles
        self.explosion_system.draw(self.screen)
        
        # Draw ship
        if self.ship:
            self.ship.draw(self.screen)
        
        # Draw HUD with neon color effects
        score_color = (0, 255, 255)  # Cyan
        lives_color = (255, 100, 100)  # Light red
        level_color = (255, 255, 0)  # Yellow
        asteroid_color = (0, 255, 0)  # Green
        
        # Score
        score_text = self.info_font.render(f"SCORE: {self.score}", True, score_color)
        self.screen.blit(score_text, (20, 20))
        
        # Lives
        lives_text = self.info_font.render(f"LIVES: {self.lives}", True, lives_color)
        lives_rect = lives_text.get_rect(topright=(SCREEN_WIDTH - 20, 20))
        self.screen.blit(lives_text, lives_rect)
        
        # Level
        level_text = self.info_font.render(f"LEVEL: {self.level}", True, level_color)
        level_rect = level_text.get_rect(midtop=(SCREEN_WIDTH // 2, 20))
        self.screen.blit(level_text, level_rect)
        
        # Asteroid Counter
        asteroid_text = self.info_font.render(f"ASTEROIDS: {len(self.asteroids)}", True, asteroid_color)
        asteroid_rect = asteroid_text.get_rect(topright=(SCREEN_WIDTH - 20, 60))
        self.screen.blit(asteroid_text, asteroid_rect)
        
        # Add scanline effect
        self.draw_scanlines()
    
    def draw_paused_screen(self):
        """Draw the pause screen overlay"""
        # Draw the game screen first
        self.draw_game_screen()
        
        # Draw semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))
        
        # Pause text with glow effect
        pause_color = (255, 255, 0)  # Yellow
        pause_glow = (255, 255, 0, 100)  # Semi-transparent yellow
        
        # Create glow surface
        glow_surface = pygame.Surface((SCREEN_WIDTH, 100), pygame.SRCALPHA)
        pygame.draw.ellipse(
            glow_surface, 
            pause_glow, 
            (SCREEN_WIDTH // 2 - 100, 0, 200, 100)
        )
        self.screen.blit(glow_surface, (0, SCREEN_HEIGHT // 2 - 50))
        
        # Pause text
        pause_text = self.title_font.render("PAUSED", True, pause_color)
        pause_rect = pause_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(pause_text, pause_rect)
        
        # Resume instructions
        resume_text = self.info_font.render("Press P to resume", True, (255, 255, 255))
        resume_rect = resume_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50))
        self.screen.blit(resume_text, resume_rect)
    
    def draw_game_over_screen(self):
        """Draw the game over screen"""
        # Draw semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))
        
        # Game over text with neon effect
        game_over_color = (255, 50, 50)  # Red
        
        over_text = self.title_font.render("GAME OVER", True, game_over_color)
        over_rect = over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
        
        # Add glow effect
        glow_surface = pygame.Surface((over_rect.width + 20, over_rect.height + 20), pygame.SRCALPHA)
        pygame.draw.ellipse(
            glow_surface, 
            (*game_over_color, 100), 
            (0, 0, over_rect.width + 20, over_rect.height + 20)
        )
        self.screen.blit(
            glow_surface, 
            (over_rect.x - 10, over_rect.y - 10)
        )
        
        # Draw the game over text
        self.screen.blit(over_text, over_rect)
        
        # Final score with rainbow effect
        # Generate shifting rainbow colors
        hue = (pygame.time.get_ticks() // 20) % 360
        score_color = pygame.Color(0, 0, 0)
        score_color.hsva = (hue, 100, 100, 100)
        
        score_text = self.info_font.render(f"FINAL SCORE: {self.score}", True, score_color)
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(score_text, score_rect)
        
        # Restart instructions - blink effect
        if pygame.time.get_ticks() % 1000 < 800:  # Blink
            restart_text = self.info_font.render("Press ENTER to play again", True, (0, 255, 0))
            restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50))
            self.screen.blit(restart_text, restart_rect)
    
    def draw(self):
        """Draw the current game state"""
        if self.state == TITLE_SCREEN:
            self.draw_title_screen()
        elif self.state == PLAYING:
            self.draw_game_screen()
        elif self.state == PAUSED:
            self.draw_paused_screen()
        elif self.state == GAME_OVER:
            self.draw_game_screen()
            self.draw_game_over_screen()
        
        # Update the display
        pygame.display.flip()
    
    def run(self):
        """Main game loop"""
        running = True
        
        while running:
            # Process events (this will handle key presses and releases)
            running = self.handle_events()
            
            # Update game objects based on the current state
            self.update()
            
            # Draw everything to the screen
            self.draw()
            
            # Cap the frame rate
            self.clock.tick(FPS)
        
        # Clean up when the game exits
        pygame.quit()

# Run the game if this script is executed
if __name__ == "__main__":
    game = AsteroidGame()
    game.run() 