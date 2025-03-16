# Multiplayer Asteroids Game

A multiplayer version of the classic Asteroids game that can be played over LAN. Players can join from any device with a web browser on the same network.

## Features

- Multiplayer gameplay over LAN with WebSockets
- Each player gets a unique colored spaceship
- Real-time synchronization of game state
- Scoreboard to track player performance
- Beautiful fluid field background effects
- Support for up to 8 concurrent players

## Requirements

- Python 3.6+
- Pygame
- WebSockets (websockets)
- aiohttp

## Installation

1. Clone this repository:
```
git clone https://github.com/yourusername/multiplayer-asteroids.git
cd multiplayer-asteroids
```

2. Install the required dependencies:
```
pip install pygame websockets aiohttp
```

## Running the Game

### Starting the Server

1. Run the server script:
```
python server.py
```

2. The server will start and be accessible at:
   - Web interface: http://localhost:8080
   - WebSocket server: ws://localhost:8081

### Joining the Game

1. Find the IP address of the computer running the server:
   - On Windows: Open Command Prompt and type `ipconfig`
   - On macOS/Linux: Open Terminal and type `ifconfig` or `ip addr`

2. Other players on the same network can join by opening their web browser and navigating to:
```
http://<server-ip-address>:8080
```

3. Enter your name on the login screen and click PLAY.

## How to Play

- **Arrow Keys**: 
  - ← (Left Arrow): Rotate counterclockwise
  - → (Right Arrow): Rotate clockwise
  - ↑ (Up Arrow): Apply thrust
- **Spacebar**: Fire lasers
- **Objective**: Destroy asteroids and avoid collisions
- **Scoring**:
  - Large asteroid: 300 points
  - Medium asteroid: 200 points
  - Small asteroid: 100 points
  - Colliding with an asteroid: -50 points

## Project Structure

- `server.py`: Main server that handles game logic and WebSocket connections
- `client.js`: Client-side JavaScript for rendering the game
- `index.html`: Web interface
- `style.css`: Styling for the web interface
- `ship.py`: Ship class implementation
- `asteroid.py`: Asteroid class implementation
- `laser.py`: Laser class implementation
- `main.py`: Original single-player game (not used in multiplayer)

## Network Architecture

The game uses a client-server architecture:

1. The server maintains the authoritative game state
2. Clients send input commands to the server
3. The server updates the game state and broadcasts it to all clients
4. Clients render the game state received from the server

## Customizing

- You can modify the `SCREEN_WIDTH` and `SCREEN_HEIGHT` in both server.py and client.js to change the game window size.
- Additional ship colors can be added in the `SHIP_COLORS` array in both ship.py and client.js.
- Adjust the `MAX_PLAYERS` constant in server.py to change the maximum number of concurrent players.

## Troubleshooting

- If players cannot connect, ensure your firewall allows connections on ports 8080 and 8081.
- Make sure all players are on the same local network.
- If you're using a VPN, it might interfere with local network connections.

## License

MIT License - Feel free to use, modify, and distribute this code. 