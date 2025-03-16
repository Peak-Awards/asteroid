import pygame
import math
import random

# Vibrant laser colors
LASER_COLORS = [
    (0, 255, 255),    # Cyan
    (255, 0, 255),    # Magenta
    (255, 255, 0),    # Yellow
    (0, 255, 0),      # Green
    (255, 128, 0)     # Orange
]

class Laser(pygame.sprite.Sprite):
    def __init__(self, x, y, angle):
        """Initialize a laser projectile"""
        super().__init__()
        
        # Laser properties
        self.position = pygame.Vector2(x, y)
        self.radius = 3  # Slightly larger for better visibility
        self.speed = 10
        
        # Calculate velocity based on angle
        angle_rad = math.radians(angle)
        self.velocity = pygame.Vector2(
            math.cos(angle_rad) * self.speed,
            -math.sin(angle_rad) * self.speed
        )
        
        # Random vibrant color
        self.color = random.choice(LASER_COLORS)
        
        # Create the laser's image with glow effect
        self.image = self.create_laser_image()
        self.rect = self.image.get_rect(center=(x, y))
        
        # Track creation time for lifespan
        self.created_time = pygame.time.get_ticks()
        
        # Trail effect
        self.trail_length = 5
        self.trail_positions = []
    
    def create_laser_image(self):
        """Create a glowing laser image"""
        # Create a surface for the laser with extra space for glow
        diameter = self.radius * 5
        center = diameter // 2
        image = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
        
        # Draw outer glow (larger, semi-transparent)
        pygame.draw.circle(image, (*self.color, 70), (center, center), self.radius * 2)
        
        # Draw middle glow (medium)
        pygame.draw.circle(image, (*self.color, 150), (center, center), self.radius * 1.5)
        
        # Draw inner core (bright)
        pygame.draw.circle(image, self.color, (center, center), self.radius)
        
        # Draw white center for extra brightness
        pygame.draw.circle(image, (255, 255, 255), (center, center), self.radius * 0.5)
        
        return image
    
    def update(self):
        """Update the laser's position and trail"""
        # Save the old position for trail effect
        self.trail_positions.append(pygame.Vector2(self.position))
        
        # Keep only the most recent positions
        if len(self.trail_positions) > self.trail_length:
            self.trail_positions.pop(0)
            
        # Move the laser
        self.position += self.velocity
        self.rect.center = (int(self.position.x), int(self.position.y))
    
    def draw(self, surface):
        """Draw the laser with trail effect"""
        # Draw the trail (fading)
        for i, pos in enumerate(self.trail_positions):
            # Calculate alpha based on position in trail
            alpha = int(((i + 1) / self.trail_length) * 200)
            
            # Create fading trail surface
            trail_size = int(self.radius * (0.5 + i / self.trail_length))
            trail_surface = pygame.Surface((trail_size * 2, trail_size * 2), pygame.SRCALPHA)
            
            # Draw fading circle
            pygame.draw.circle(
                trail_surface, 
                (*self.color, alpha), 
                (trail_size, trail_size), 
                trail_size
            )
            
            # Draw the trail
            surface.blit(
                trail_surface, 
                (pos.x - trail_size, pos.y - trail_size)
            )
        
        # Draw the main laser (default pygame sprite draw will handle this)
        # surface.blit(self.image, self.rect) 