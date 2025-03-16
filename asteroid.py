import pygame
import math
import random

# Retro color constants
NEON_COLORS = [
    (0, 195, 255),    # Cyan
    (255, 0, 153),    # Pink
    (255, 230, 0),    # Yellow
    (57, 255, 20),    # Green
    (225, 53, 255),   # Purple
    (255, 89, 0)      # Orange
]

class AsteroidTrail:
    """Class for creating a visual trail behind asteroids"""
    def __init__(self, color, max_points=8):
        self.color = color
        self.max_points = max_points
        self.points = []
        self.counter = 0
        
    def update(self, x, y):
        # Add new trail points periodically
        self.counter += 1
        if self.counter % 4 == 0:  # Add trail point every 4 frames
            self.points.append((x, y))
            if len(self.points) > self.max_points:
                self.points.pop(0)
                
    def draw(self, surface):
        if len(self.points) < 2:
            return
            
        # Draw trail with fading opacity
        for i in range(len(self.points) - 1):
            # Calculate opacity based on point age
            opacity = int(255 * (i / len(self.points)) * 0.5)  # Max 50% opacity
            # Calculate line width based on point age
            width = max(1, int(3 * (i / len(self.points))))
            
            start_point = self.points[i]
            end_point = self.points[i+1]
            
            # Draw the trail line
            pygame.draw.line(
                surface, 
                (*self.color[:3], opacity),  # Color with calculated opacity
                start_point, 
                end_point, 
                width
            )

class Asteroid(pygame.sprite.Sprite):
    def __init__(self, x, y, radius=None, level=1):
        """Initialize an asteroid"""
        super().__init__()
        
        # Asteroid properties
        self.level = level
        self.radius = radius or self.calculate_radius()
        self.position = pygame.Vector2(x, y)
        
        # Set random velocity with a minimum speed - increased for faster movement
        min_speed = 1.2  # Higher minimum speed (was 0.5)
        # Increased base speed multiplier from 2 to 3.5
        speed = max(min_speed, (random.random() * 3.5 + 0.8) / self.level)
        angle = random.random() * math.pi * 2
        self.velocity = pygame.Vector2(
            math.cos(angle) * speed,
            math.sin(angle) * speed
        )
        
        # Ensure the asteroid is always moving in both x and y with increased minimums
        if abs(self.velocity.x) < 0.5:  # Increased from 0.2
            # Too slow in x direction, increase it
            self.velocity.x = 0.5 if self.velocity.x >= 0 else -0.5
        if abs(self.velocity.y) < 0.5:  # Increased from 0.2
            # Too slow in y direction, increase it
            self.velocity.y = 0.5 if self.velocity.y >= 0 else -0.5
        
        # Rotation properties
        self.rotation = 0
        self.rotation_speed = random.uniform(-2, 2)  # Increased rotation speed too (was -1 to 1)
        
        # Color - different for each level
        level_colors = {
            1: NEON_COLORS[:2],    # Large asteroids - cyan/pink
            2: NEON_COLORS[2:4],   # Medium asteroids - yellow/green
            3: NEON_COLORS[4:]     # Small asteroids - purple/orange
        }
        self.color = random.choice(level_colors[level])
        self.glow_color = (*self.color, 100)  # Semi-transparent for glow
        
        # Add shadow effect for 3D appearance - MOVED THIS BEFORE create_asteroid_image() call
        self.shadow_offset = (random.randint(-3, 3), random.randint(2, 5))
        
        # Add visual trail effect
        self.trail = AsteroidTrail(self.color)
        
        # Add oscillating light effect for 3D appearance
        self.light_angle = random.uniform(0, math.pi * 2)
        self.light_speed = random.uniform(0.05, 0.2)  # Speed of light rotation
        
        # Create the asteroid's image
        self.original_image = self.create_asteroid_image()
        self.image = self.original_image
        self.rect = self.image.get_rect(center=(x, y))
    
    def calculate_radius(self):
        """Calculate radius based on asteroid level"""
        return (4 - self.level) * 20
    
    def create_asteroid_image(self):
        """Create a jagged circular asteroid image with neon effect and 3D appearance"""
        # Create a transparent surface large enough for the asteroid
        diameter = self.radius * 2.5  # Make sure there's room for jagged edges
        image = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
        
        # Create a jagged circle with 7-10 vertices
        num_vertices = random.randint(7, 10)
        points = []
        glow_points = []  # Slightly larger for glow effect
        
        for i in range(num_vertices):
            angle = (i / num_vertices) * math.pi * 2
            
            # Random jagged radius between 70% and 130% of the base radius
            jag = random.random() * 0.6 + 0.7
            r = self.radius * jag
            
            # Calculate vertex position
            center = diameter // 2
            x = center + math.cos(angle) * r
            y = center + math.sin(angle) * r
            
            points.append((x, y))
            
            # Add glow points (slightly larger)
            glow_r = r * 1.05
            glow_x = center + math.cos(angle) * glow_r
            glow_y = center + math.sin(angle) * glow_r
            glow_points.append((glow_x, glow_y))
        
        # Draw shadow for 3D effect
        shadow_points = [(x + self.shadow_offset[0], y + self.shadow_offset[1]) for x, y in points]
        pygame.draw.polygon(image, (0, 0, 0, 100), shadow_points, 0)
        
        # Draw the glow effect
        pygame.draw.polygon(image, self.glow_color, glow_points, 0)
        
        # Draw the asteroid (filled with neon color)
        pygame.draw.polygon(image, self.color, points, 0)
        
        # Add internal details for 3D look (craters/texture)
        self.add_asteroid_details(image, points, center)
        
        # Add white outline for better visibility
        pygame.draw.polygon(image, (255, 255, 255), points, 1)
        
        # Add highlight edge for 3D effect
        highlight_direction = random.uniform(0, math.pi * 2)
        self.add_highlight_edge(image, points, highlight_direction)
        
        return image
    
    def add_asteroid_details(self, image, points, center):
        """Add crater details and texture to make the asteroid look more 3D"""
        # Add 2-4 craters/details to the asteroid
        num_details = random.randint(2, 4)
        
        for _ in range(num_details):
            # Random position within the asteroid
            angle = random.uniform(0, math.pi * 2)
            distance = random.uniform(0.2, 0.7) * self.radius
            
            x = center + math.cos(angle) * distance
            y = center + math.sin(angle) * distance
            
            # Crater size proportional to asteroid
            crater_size = random.uniform(0.15, 0.3) * self.radius
            
            # Draw crater/detail
            crater_color = (
                max(0, self.color[0] - random.randint(30, 70)),
                max(0, self.color[1] - random.randint(30, 70)),
                max(0, self.color[2] - random.randint(30, 70)),
                random.randint(120, 200)
            )
            
            pygame.draw.circle(image, crater_color, (int(x), int(y)), int(crater_size))
            
            # Add highlight to crater for 3D effect
            highlight_angle = angle + math.pi/4  # Highlight from same direction
            highlight_x = x + math.cos(highlight_angle) * (crater_size * 0.5)
            highlight_y = y + math.sin(highlight_angle) * (crater_size * 0.5)
            
            highlight_color = (
                min(255, self.color[0] + 50),
                min(255, self.color[1] + 50),
                min(255, self.color[2] + 50),
                100
            )
            
            pygame.draw.circle(
                image, 
                highlight_color, 
                (int(highlight_x), int(highlight_y)), 
                int(crater_size * 0.25)
            )
    
    def add_highlight_edge(self, image, points, direction):
        """Add a bright edge highlight to give the asteroid a 3D look"""
        # Find points that face the light direction
        center_x = sum(x for x, y in points) / len(points)
        center_y = sum(y for x, y in points) / len(points)
        
        highlight_points = []
        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i+1) % len(points)]
            
            # Calculate the normal of this edge
            edge_normal = (
                -(p2[1] - p1[1]),  # Normal y = -(edge x)
                p2[0] - p1[0]       # Normal x = edge y
            )
            
            # Normalize the normal
            length = math.sqrt(edge_normal[0]**2 + edge_normal[1]**2)
            if length > 0:
                edge_normal = (edge_normal[0] / length, edge_normal[1] / length)
                
            # Calculate the light direction
            light_dir = (
                math.cos(direction),
                math.sin(direction)
            )
            
            # Dot product to determine if edge faces light
            dot_product = edge_normal[0] * light_dir[0] + edge_normal[1] * light_dir[1]
            
            # If edge faces light, add to highlight
            if dot_product > 0.2:  # Threshold to control highlight size
                highlight_points.append(p1)
                highlight_points.append(p2)
        
        # Draw highlight on edges that face the light
        if len(highlight_points) >= 2:
            for i in range(0, len(highlight_points), 2):
                if i+1 < len(highlight_points):
                    p1 = highlight_points[i]
                    p2 = highlight_points[i+1]
                    
                    # Bright highlight color
                    highlight_color = (
                        min(255, self.color[0] + 100),
                        min(255, self.color[1] + 100),
                        min(255, self.color[2] + 100),
                        150
                    )
                    
                    pygame.draw.line(image, highlight_color, p1, p2, 2)
    
    def update(self):
        """Update the asteroid's position and rotation"""
        # Move the asteroid
        self.position += self.velocity
        
        # Update the trail
        self.trail.update(self.position.x, self.position.y)
        
        # Update light angle for 3D lighting effect
        self.light_angle += self.light_speed
        
        # Rotate the asteroid
        self.rotation += self.rotation_speed
        self.image = pygame.transform.rotate(self.original_image, self.rotation)
        
        # Update the rect position, keeping the center
        self.rect = self.image.get_rect(center=(int(self.position.x), int(self.position.y)))
    
    def draw(self, surface):
        """Draw the asteroid with trail effect"""
        # Draw the trail first (behind asteroid)
        self.trail.draw(surface)
        
        # Draw the asteroid itself (handled by sprite group)
        surface.blit(self.image, self.rect)
    
    def break_apart(self):
        """Create smaller asteroids when this one is destroyed"""
        # Only break if not already at the smallest level
        if self.level >= 3:
            return []
        
        # Create two smaller asteroids
        new_asteroids = []
        for _ in range(2):
            new_asteroid = Asteroid(
                self.rect.centerx,
                self.rect.centery,
                None,
                self.level + 1
            )
            new_asteroids.append(new_asteroid)
        
        return new_asteroids

    def split(self):
        """Split asteroid into two smaller ones when hit"""
        # ... existing code ...
    
    def draw_glow(self, surface):
        """Draw the glow effect around the asteroid"""
        # ... existing code ...
        
    def break_apart(self, game):
        """Break the asteroid into smaller pieces"""
        # ... existing code ... 