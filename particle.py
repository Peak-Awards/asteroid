import pygame
import random
import math

class Particle:
    def __init__(self, x, y, color=None):
        """Initialize a single explosion particle"""
        self.position = pygame.Vector2(x, y)
        
        # Random velocity with outward explosion motion
        speed = random.uniform(0.5, 3.0)
        angle = random.uniform(0, math.pi * 2)
        self.velocity = pygame.Vector2(
            math.cos(angle) * speed,
            math.sin(angle) * speed
        )
        
        # Random colorful appearance
        if color is None:
            # Bright, vibrant neon colors
            self.color = random.choice([
                (255, 0, 128),      # Hot pink
                (0, 255, 255),      # Cyan
                (255, 255, 0),      # Yellow
                (0, 255, 0),        # Neon green
                (255, 128, 0),      # Orange
                (128, 0, 255),      # Purple
                (0, 128, 255),      # Blue
            ])
        else:
            self.color = color
        
        # Particle properties
        self.radius = random.uniform(1.5, 3.0)
        self.life = 1.0  # Full life
        self.decay_rate = random.uniform(0.01, 0.03)  # How fast it fades
    
    def update(self):
        """Update particle position and life"""
        # Move the particle
        self.position += self.velocity
        
        # Apply some drag
        self.velocity *= 0.98
        
        # Reduce life
        self.life -= self.decay_rate
        
        # Return True if particle is still alive
        return self.life > 0
    
    def draw(self, surface):
        """Draw the particle"""
        # Fade the color as life decreases
        alpha = int(self.life * 255)
        color = (*self.color, alpha)
        
        # Create a surface for the particle with alpha channel
        particle_surface = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        
        # Draw the particle
        pygame.draw.circle(
            particle_surface, 
            color, 
            (self.radius, self.radius), 
            self.radius
        )
        
        # Draw the particle on the main surface
        surface.blit(
            particle_surface, 
            (self.position.x - self.radius, self.position.y - self.radius)
        )

class ExplosionSystem:
    def __init__(self):
        """Manage multiple particle explosions"""
        self.particle_groups = []
    
    def create_explosion(self, x, y, size=20, color=None):
        """Create a new explosion at the given position"""
        # Create a new group of particles
        particles = []
        for _ in range(size):
            particles.append(Particle(x, y, color))
        
        self.particle_groups.append(particles)
    
    def update(self):
        """Update all particle groups"""
        for i in range(len(self.particle_groups) - 1, -1, -1):
            # Update particles in this group
            self.particle_groups[i] = [p for p in self.particle_groups[i] if p.update()]
            
            # Remove empty groups
            if len(self.particle_groups[i]) == 0:
                self.particle_groups.pop(i)
    
    def draw(self, surface):
        """Draw all particle groups"""
        for group in self.particle_groups:
            for particle in group:
                particle.draw(surface) 