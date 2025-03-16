import asyncio
import json
import logging
import os
import random
import time
import uuid
from datetime import datetime
import websockets
from aiohttp import web
import pygame

# Import game objects (without initializing pygame's display)
os.environ["SDL_VIDEODRIVER"] = "dummy"  # Headless mode for server
pygame.init()
pygame.mixer.init()

from ship import Ship
from asteroid import Asteroid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("asteroids_server")

# Game constants
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
UPDATE_RATE = 1 / 60  # 60 FPS
MAX_PLAYERS = 8

class AsteroidsServer:
    def __init__(self):
        self.clients = {}  # Maps WebSocket to player_id
        self.ships = {}  # Maps player_id to Ship object
        self.asteroids = []  # List of asteroids
        self.lasers = []  # List of lasers
        self.game_state = {
            "ships": {},
            "asteroids": [],
            "lasers": [],
            "scores": {},
            "level": 1,
        }
        self.running = False
        self.last_update = time.time()
        self.color_indexes = list(range(8))  # 8 unique colors
        random.shuffle(self.color_indexes)  # Randomize colors
        
        # Create initial asteroids
        self.create_asteroids(10)
        
        logger.info("Asteroids server initialized")
    
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
            asteroid = {"x": x, "y": y, "level": random.randint(1, 3), "id": str(uuid.uuid4())}
            self.asteroids.append(asteroid)
    
    def get_player_color_idx(self):
        """Get a unique color index for a new player"""
        if not self.color_indexes:
            # If all colors are taken, start recycling them
            self.color_indexes = list(range(8))
            random.shuffle(self.color_indexes)
        return self.color_indexes.pop(0)
    
    async def register(self, websocket, player_name):
        """Register a new player"""
        try:
            player_id = str(uuid.uuid4())
            color_idx = self.get_player_color_idx()
            
            # Create a new ship for the player at a random position
            x = random.randint(SCREEN_WIDTH // 4, 3 * SCREEN_WIDTH // 4)
            y = random.randint(SCREEN_HEIGHT // 4, 3 * SCREEN_HEIGHT // 4)
            
            logger.info(f"Creating ship for player {player_name} with ID {player_id}")
            ship = Ship(x, y, player_id=player_id, player_name=player_name, color_idx=color_idx)
            ship.set_invulnerable()  # Make the ship invulnerable when joining
            
            # Store client and ship
            self.clients[websocket] = player_id
            self.ships[player_id] = ship
            self.game_state["scores"][player_id] = 0
            
            logger.info(f"Player {player_name} ({player_id}) connected")
            
            # Send initial game state to the new player
            await self.send_game_state(websocket)
            
            # Broadcast updated player list
            await self.broadcast({"type": "player_joined", "player_id": player_id, "player_name": player_name})
        except Exception as e:
            logger.error(f"Error registering player {player_name}: {str(e)}", exc_info=True)
            raise
    
    async def unregister(self, websocket):
        """Unregister a player when they disconnect"""
        if websocket in self.clients:
            player_id = self.clients[websocket]
            player_name = self.ships[player_id].player_name if player_id in self.ships else "Unknown"
            
            # Free up the color index
            if player_id in self.ships:
                color_idx = self.ships[player_id].to_dict()["color_idx"]
                if color_idx not in self.color_indexes:
                    self.color_indexes.append(color_idx)
            
            # Remove player data
            del self.clients[websocket]
            if player_id in self.ships:
                del self.ships[player_id]
            if player_id in self.game_state["scores"]:
                del self.game_state["scores"][player_id]
            
            logger.info(f"Player {player_name} ({player_id}) disconnected")
            
            # Broadcast player left
            await self.broadcast({"type": "player_left", "player_id": player_id, "player_name": player_name})
    
    async def process_message(self, websocket, message):
        """Process a message from a client"""
        try:
            logger.debug(f"Processing message: {message}")
            
            if "type" not in message:
                logger.warning(f"Message missing 'type' field: {message}")
                return
                
            player_id = self.clients.get(websocket)
            if not player_id and message["type"] != "join":
                logger.warning(f"Message from unregistered client: {message}")
                return
            
            if message["type"] == "input":
                # Update the player's ship based on input
                if player_id in self.ships:
                    ship = self.ships[player_id]
                    inputs = message["data"]
                    
                    if "rotation" in inputs:
                        ship.rotate(inputs["rotation"])
                    if "thrust" in inputs:
                        ship.thrust(inputs["thrust"])
                    if "fire" in inputs and inputs["fire"]:
                        # Create a new laser
                        laser_x = ship.rect.centerx + ship.radius * pygame.math.Vector2(1, 0).rotate(-ship.angle).x
                        laser_y = ship.rect.centery + ship.radius * pygame.math.Vector2(1, 0).rotate(-ship.angle).y
                        laser = {
                            "x": laser_x,
                            "y": laser_y,
                            "angle": ship.angle,
                            "player_id": player_id,
                            "id": str(uuid.uuid4()),
                            "created": time.time(),
                            "lifetime": 1.5,  # 1.5 seconds lifetime
                            "speed": 10,
                        }
                        self.lasers.append(laser)
            
            elif message["type"] == "join":
                # Register a new player
                if "player_name" not in message:
                    logger.warning("Join message missing player_name")
                    return
                    
                await self.register(websocket, message["player_name"])
            else:
                logger.warning(f"Unknown message type: {message['type']}")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
    
    async def handle_client(self, websocket, path=None):
        """Handle a client connection"""
        logger.info(f"New client connection from {websocket.remote_address}")
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    logger.debug(f"Received message: {data}")
                    await self.process_message(websocket, data)
                except json.JSONDecodeError:
                    logger.warning("Received invalid JSON")
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}", exc_info=True)
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Connection closed: {e.code} - {e.reason}")
        except Exception as e:
            logger.error(f"Unexpected error in client handler: {str(e)}", exc_info=True)
        finally:
            logger.info(f"Client disconnected: {websocket.remote_address}")
            await self.unregister(websocket)
    
    async def broadcast(self, message):
        """Send a message to all connected clients"""
        if not self.clients:
            return
        
        message_data = json.dumps(message)
        await asyncio.gather(
            *[client.send(message_data) for client in self.clients],
            return_exceptions=True
        )
    
    async def send_game_state(self, websocket=None):
        """Send the current game state to a specific client or all clients"""
        # Update the game state dictionary
        self.game_state["ships"] = {player_id: ship.to_dict() for player_id, ship in self.ships.items()}
        self.game_state["asteroids"] = self.asteroids
        self.game_state["lasers"] = self.lasers
        
        # Create the message
        message = {
            "type": "game_state",
            "data": self.game_state,
            "timestamp": time.time()
        }
        
        if websocket:
            # Send to specific client
            await websocket.send(json.dumps(message))
        else:
            # Broadcast to all clients
            await self.broadcast(message)
    
    async def update_game(self):
        """Update the game state"""
        current_time = time.time()
        dt = current_time - self.last_update
        self.last_update = current_time
        
        # Update all ships
        for ship in self.ships.values():
            ship.update()
        
        # Update lasers
        new_lasers = []
        for laser in self.lasers:
            # Move the laser
            laser["x"] += laser["speed"] * pygame.math.Vector2(1, 0).rotate(-laser["angle"]).x
            laser["y"] += laser["speed"] * pygame.math.Vector2(1, 0).rotate(-laser["angle"]).y
            
            # Check if the laser is still alive
            if current_time - laser["created"] < laser["lifetime"]:
                # Check if the laser is still on screen
                if (0 <= laser["x"] <= SCREEN_WIDTH and 
                    0 <= laser["y"] <= SCREEN_HEIGHT):
                    new_lasers.append(laser)
        
        self.lasers = new_lasers
        
        # Update asteroids
        new_asteroids = []
        for asteroid in self.asteroids:
            # Calculate velocity based on level
            velocity = (4 - asteroid["level"]) * 1.0
            
            # Move the asteroid (simple linear movement)
            # TODO: Implement actual asteroid movement with angles
            angle = random.uniform(0, 360)
            asteroid["x"] += velocity * pygame.math.Vector2(1, 0).rotate(-angle).x
            asteroid["y"] += velocity * pygame.math.Vector2(1, 0).rotate(-angle).y
            
            # Check if the asteroid is still on or near the screen
            if (-100 <= asteroid["x"] <= SCREEN_WIDTH + 100 and 
                -100 <= asteroid["y"] <= SCREEN_HEIGHT + 100):
                new_asteroids.append(asteroid)
        
        self.asteroids = new_asteroids
        
        # Check for collisions between lasers and asteroids
        self.check_laser_asteroid_collisions()
        
        # Check for collisions between ships and asteroids
        self.check_ship_asteroid_collisions()
        
        # If no asteroids, create more
        if not self.asteroids:
            self.game_state["level"] += 1
            self.create_asteroids(10 + self.game_state["level"])
        
        # Send updated game state to all clients
        await self.send_game_state()
    
    def check_laser_asteroid_collisions(self):
        """Check for collisions between lasers and asteroids"""
        # We'll use a simple circle-based collision detection
        lasers_to_remove = set()
        asteroids_to_remove = set()
        
        for laser_idx, laser in enumerate(self.lasers):
            for asteroid_idx, asteroid in enumerate(self.asteroids):
                # Simple distance-based collision
                dx = laser["x"] - asteroid["x"]
                dy = laser["y"] - asteroid["y"]
                distance = (dx*dx + dy*dy) ** 0.5
                
                # Asteroid radius based on level (larger = bigger)
                asteroid_radius = (4 - asteroid["level"]) * 15
                
                if distance < asteroid_radius:
                    # Collision detected
                    lasers_to_remove.add(laser_idx)
                    asteroids_to_remove.add(asteroid_idx)
                    
                    # Create smaller asteroids if not smallest
                    if asteroid["level"] < 3:
                        for _ in range(2):
                            new_asteroid = {
                                "x": asteroid["x"],
                                "y": asteroid["y"],
                                "level": asteroid["level"] + 1,
                                "id": str(uuid.uuid4())
                            }
                            self.asteroids.append(new_asteroid)
                    
                    # Award points to the player
                    if "player_id" in laser and laser["player_id"] in self.ships:
                        player_id = laser["player_id"]
                        # Points based on asteroid size (smaller = more points)
                        points = (4 - asteroid["level"]) * 100
                        self.game_state["scores"][player_id] = self.game_state["scores"].get(player_id, 0) + points
                        # Update the ship's score for client-side display
                        self.ships[player_id].score = self.game_state["scores"][player_id]
        
        # Remove the collided objects
        self.lasers = [laser for idx, laser in enumerate(self.lasers) if idx not in lasers_to_remove]
        self.asteroids = [asteroid for idx, asteroid in enumerate(self.asteroids) if idx not in asteroids_to_remove]
    
    def check_ship_asteroid_collisions(self):
        """Check for collisions between ships and asteroids"""
        for player_id, ship in list(self.ships.items()):
            if ship.invulnerable:
                continue  # Skip invulnerable ships
                
            for asteroid in self.asteroids:
                # Simple distance-based collision
                dx = ship.position.x - asteroid["x"]
                dy = ship.position.y - asteroid["y"]
                distance = (dx*dx + dy*dy) ** 0.5
                
                # Asteroid radius based on level
                asteroid_radius = (4 - asteroid["level"]) * 15
                
                if distance < ship.radius + asteroid_radius:
                    # Ship hit by asteroid - respawn and make invulnerable
                    ship.position.x = random.randint(SCREEN_WIDTH // 4, 3 * SCREEN_WIDTH // 4)
                    ship.position.y = random.randint(SCREEN_HEIGHT // 4, 3 * SCREEN_HEIGHT // 4)
                    ship.velocity = pygame.Vector2(0, 0)
                    ship.set_invulnerable()
                    
                    # Penalize score
                    penalty = 50
                    self.game_state["scores"][player_id] = max(0, self.game_state["scores"].get(player_id, 0) - penalty)
                    ship.score = self.game_state["scores"][player_id]
    
    async def game_loop(self):
        """Main game loop"""
        self.running = True
        
        while self.running:
            start_time = time.time()
            
            # Update game state
            await self.update_game()
            
            # Calculate how long to sleep to maintain the update rate
            elapsed = time.time() - start_time
            sleep_time = max(0, UPDATE_RATE - elapsed)
            
            # Sleep until next update
            await asyncio.sleep(sleep_time)

async def handle_index(request):
    """Serve the index.html file"""
    with open('index.html', encoding='utf-8') as f:
        return web.Response(text=f.read(), content_type='text/html')

async def handle_js(request):
    """Serve the client.js file"""
    with open('client.js', encoding='utf-8') as f:
        return web.Response(text=f.read(), content_type='application/javascript')

async def handle_css(request):
    """Serve the style.css file"""
    with open('style.css', encoding='utf-8') as f:
        return web.Response(text=f.read(), content_type='text/css')

async def start_server():
    """Start the game server and web server"""
    # Create the game server
    game_server = AsteroidsServer()
    
    # Create the web server
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_get('/client.js', handle_js)
    app.router.add_get('/style.css', handle_css)
    
    # Set up the HTTP server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    logger.info("Web server started at http://localhost:8080")
    
    # Start the WebSocket server
    ws_server = await websockets.serve(
        game_server.handle_client, '0.0.0.0', 8081
    )
    logger.info("WebSocket server started at ws://localhost:8081")
    
    # Start the game loop
    asyncio.create_task(game_server.game_loop())
    
    return ws_server, runner

if __name__ == "__main__":
    async def main():
        # Start the server
        ws_server, runner = await start_server()
        
        # Keep the server running until interrupted
        try:
            # This creates a future that never completes, keeping the event loop running
            forever = asyncio.Future()
            await forever
        except asyncio.CancelledError:
            pass
        finally:
            # Clean up
            ws_server.close()
            await ws_server.wait_closed()
            await runner.cleanup()
            logger.info("Server shutdown complete")
            
    try:
        # Run everything in a single asyncio.run() call
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutting down...") 