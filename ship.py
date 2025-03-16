import pygame
import math
import random

# Retro color constants
NEON_BLUE = (0, 195, 255)
NEON_PINK = (255, 0, 153)
NEON_GREEN = (57, 255, 20)
NEON_YELLOW = (255, 255, 0)
NEON_ORANGE = (255, 128, 0)
NEON_PURPLE = (180, 90, 255)
NEON_CYAN = (0, 255, 195)
NEON_RED = (255, 50, 50)

# Extended color palette for multiplayer
SHIP_COLORS = [NEON_BLUE, NEON_PINK, NEON_GREEN, NEON_YELLOW, NEON_ORANGE, NEON_PURPLE, NEON_CYAN, NEON_RED]
THRUSTER_COLORS = [NEON_ORANGE, NEON_YELLOW, (255, 255, 255)]

class Ship(pygame.sprite.Sprite):
    def __init__(self, x, y, player_id=None, player_name=None, color_idx=None):
        """Initialize the player's ship"""
        super().__init__()
        
        # Player identification for multiplayer
        self.player_id = player_id if player_id is not None else "local"
        self.player_name = player_name if player_name is not None else "Player"
        
        # Ship properties
        self.radius = 15  # For collision detection
        self.angle = 90  # Starting angle (facing up)
        self.rotation_speed = 6  # Degrees per frame (increased from 5)
        self.rotation_direction = 0  # 0 = not rotating, 1 = clockwise, -1 = counter-clockwise
        
        # Movement properties
        self.position = pygame.Vector2(x, y)
        self.velocity = pygame.Vector2(0, 0)
        self.acceleration = 0.3  # Increased from 0.2
        self.friction = 0.97  # Improved friction for better control (was 0.95)
        self.max_speed = 8.5  # Increased speed limit from 6.0
        self.thrusting = False
        
        # Ship color - assign from index or random if not specified
        if color_idx is not None and 0 <= color_idx < len(SHIP_COLORS):
            self.color = SHIP_COLORS[color_idx]
        else:
            self.color = random.choice(SHIP_COLORS)
        
        # Create the ship's image
        self.original_image = self.create_ship_image()
        self.image = self.original_image
        self.rect = self.image.get_rect(center=(x, y))
        
        # Thruster effect params
        self.thrust_particles = []
        self.thrust_counter = 0
        
        # Invulnerability properties
        self.invulnerable = False
        self.invulnerable_time = 1500  # Reduced from 3 seconds to 1.5 seconds
        self.blink_time = 100  # Blink every 100ms
        self.last_blink = 0
        self.visible = True
        
        # Off-screen timer - track how long the ship has been off-screen
        self.off_screen_time = 0
        self.max_off_screen_time = 3.0  # 3 seconds max off-screen before respawning
        
        # Score tracking for multiplayer
        self.score = 0
        self.last_update_time = pygame.time.get_ticks()
    
    def create_ship_image(self):
        """Create the ship's image as a triangle with neon glow effect"""
        # Create a transparent surface
        size = self.radius * 3
        image = pygame.Surface((size, size), pygame.SRCALPHA)
        
        # Define the ship's shape (triangle)
        points = [
            (size//2, 0),           # Nose
            (0, size),              # Rear left
            (size, size)            # Rear right
        ]
        
        # Draw the glowing effect (larger triangle)
        glow_points = [
            (size//2, -2),          # Nose with glow
            (-2, size+2),           # Rear left with glow
            (size+2, size+2)        # Rear right with glow
        ]
        pygame.draw.polygon(image, (*self.color, 100), glow_points)  # Semi-transparent glow
        
        # Draw the ship (solid)
        pygame.draw.polygon(image, self.color, points, 0)  # Filled
        
        # Add a white outline for better visibility
        pygame.draw.polygon(image, (255, 255, 255), points, 1)
        
        return image
    
    def rotate(self, direction):
        """Rotate the ship (direction: 1 for left, -1 for right)"""
        self.rotation_direction = direction
    
    def thrust(self, on):
        """Toggle the ship's thrust"""
        self.thrusting = on
    
    def set_invulnerable(self):
        """Make the ship temporarily invulnerable"""
        self.invulnerable = True
        self.last_blink = pygame.time.get_ticks()
        
        # Reset invulnerability after a delay
        pygame.time.set_timer(pygame.USEREVENT, self.invulnerable_time)
    
    def update(self):
        """Update the ship's position and rotation"""
        # Update rotation (only when keys are pressed)
        if self.rotation_direction != 0:
            self.angle += self.rotation_direction * self.rotation_speed
            
            # Keep angle in the range [0, 360)
            self.angle %= 360
            
            # Rotate the image
            self.image = pygame.transform.rotate(self.original_image, self.angle - 90)
            self.rect = self.image.get_rect(center=self.rect.center)
        
        # Apply thrust if the ship is thrusting
        if self.thrusting:
            # Calculate thrust direction based on ship's angle
            angle_rad = math.radians(self.angle)
            thrust_x = math.cos(angle_rad) * self.acceleration
            thrust_y = -math.sin(angle_rad) * self.acceleration
            
            # Apply thrust to velocity
            self.velocity.x += thrust_x
            self.velocity.y += thrust_y
            
            # Limit maximum speed
            speed = self.velocity.length()
            if speed > self.max_speed:
                self.velocity.normalize_ip()  # Convert to unit vector
                self.velocity *= self.max_speed  # Scale to max_speed
        
        # Apply friction to gradually slow down
        self.velocity *= self.friction
        
        # If velocity is very small, stop completely to prevent endless drifting
        if self.velocity.length() < 0.1:
            self.velocity = pygame.Vector2(0, 0)
        
        # Update position
        self.position += self.velocity
        self.rect.center = (int(self.position.x), int(self.position.y))
        
        # Check if ship is off-screen
        screen_width = 1024  # Updated screen dimensions 
        screen_height = 768
        screen_rect = pygame.Rect(0, 0, screen_width, screen_height)
        ship_visible = screen_rect.collidepoint(self.position.x, self.position.y)
        
        if not ship_visible:
            # Ship is off-screen, increment timer (assuming 60 FPS)
            self.off_screen_time += 1/60
            
            # If ship has been off-screen too long, respawn it at center
            if self.off_screen_time >= self.max_off_screen_time:
                self.position.x = screen_width // 2
                self.position.y = screen_height // 2
                self.velocity = pygame.Vector2(0, 0)
                self.off_screen_time = 0
                self.set_invulnerable()  # Make ship invulnerable after respawn
        else:
            # Reset timer when ship is on screen
            self.off_screen_time = 0
        
        # Handle invulnerability blinking effect
        if self.invulnerable:
            current_time = pygame.time.get_ticks()
            
            if current_time - self.last_blink > self.blink_time:
                self.visible = not self.visible
                self.last_blink = current_time
            
            # Check if invulnerability period is over
            if current_time > self.last_blink + self.invulnerable_time:
                self.invulnerable = False
                self.visible = True
        
        # Update thruster particles
        self.thrust_counter += 1
        
        # Update last update time for networking
        self.last_update_time = pygame.time.get_ticks()
    
    def draw(self, surface):
        """Draw the ship to the screen"""
        if self.visible:
            surface.blit(self.image, self.rect)
            
            # Draw thrust fire if thrusting
            if self.thrusting:
                # Calculate thrust position
                angle_rad = math.radians(self.angle)
                thrust_x = self.rect.centerx - math.cos(angle_rad) * self.radius
                thrust_y = self.rect.centery + math.sin(angle_rad) * self.radius
                
                # Create thruster flame with multiple segments and color gradient
                for i in range(3):
                    length = self.radius * (0.5 + (0.3 * i))
                    end_x = thrust_x - math.cos(angle_rad) * length
                    end_y = thrust_y + math.sin(angle_rad) * length
                    
                    # Add some flutter to the flame
                    if self.thrust_counter % 2 == 0:
                        jitter = random.uniform(-1, 1)
                        end_x += jitter
                        end_y += jitter
                    
                    # Choose color based on position in flame
                    color = THRUSTER_COLORS[i]
                    pygame.draw.line(surface, color, (thrust_x, thrust_y), (end_x, end_y), 2)
            
            # Draw player name above ship
            if self.player_name:
                font = pygame.font.Font(None, 20)
                name_text = font.render(self.player_name, True, self.color)
                name_rect = name_text.get_rect(centerx=self.rect.centerx, bottom=self.rect.top - 5)
                surface.blit(name_text, name_rect)
    
    def to_dict(self):
        """Convert ship state to a dictionary for network transmission"""
        return {
            'player_id': self.player_id,
            'player_name': self.player_name,
            'x': self.position.x,
            'y': self.position.y,
            'angle': self.angle,
            'velocity_x': self.velocity.x,
            'velocity_y': self.velocity.y,
            'thrusting': self.thrusting,
            'rotation_direction': self.rotation_direction,
            'invulnerable': self.invulnerable,
            'visible': self.visible,
            'score': self.score,
            'color_idx': SHIP_COLORS.index(self.color) if self.color in SHIP_COLORS else 0
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create a ship from a dictionary (received from network)"""
        ship = cls(
            data['x'], 
            data['y'],
            player_id=data['player_id'],
            player_name=data['player_name'],
            color_idx=data['color_idx']
        )
        ship.angle = data['angle']
        ship.velocity.x = data['velocity_x']
        ship.velocity.y = data['velocity_y']
        ship.thrusting = data['thrusting']
        ship.rotation_direction = data['rotation_direction']
        ship.invulnerable = data['invulnerable']
        ship.visible = data['visible']
        ship.score = data['score']
        
        # Update the image based on the angle
        ship.image = pygame.transform.rotate(ship.original_image, ship.angle - 90)
        ship.rect = ship.image.get_rect(center=ship.rect.center)
        
        return ship 