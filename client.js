// Global variables
let canvas;
let ctx;
let socket;
let gameState = null;
let playerId = null;
let playerName = '';
let lastUpdateTime = 0;
let keys = {};
let lastControlsJson = '';

// Game constants
const KEYS = {
    LEFT: 37,
    UP: 38,
    RIGHT: 39,
    DOWN: 40,
    SPACE: 32
};

// Ship colors
const SHIP_COLORS = [
  [255, 100, 100],  // Red
  [100, 255, 100],  // Green
  [100, 100, 255],  // Blue
  [255, 255, 100],  // Yellow
  [255, 100, 255],  // Magenta
  [100, 255, 255],  // Cyan
  [255, 200, 100]   // Orange
];

// Fluid simulation for background
let fluidField = {
    particles: [],
    numParticles: 400,
    flowField: [],
    gridSize: 20,
    flowSpeed: 0.8,
    turbulence: 0.05,
    fieldTime: 0,
    updateRate: 0.02,
    influenceRadius: 150,
    shipInfluence: 4.0,
    
    init: function() {
        // Initialize particles
        this.particles = [];
        for (let i = 0; i < this.numParticles; i++) {
            this.particles.push({
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                vx: 0,
                vy: 0,
                size: 1 + Math.random() * 2,
                color: this.getParticleColor(),
                age: Math.random() * 100,
                trail: [],
                maxTrail: 6 + Math.floor(Math.random() * 10),
                turbulence: Math.random() * 0.1
            });
        }
        
        // Initialize flow field grid
        this.flowField = [];
        const cols = Math.ceil(canvas.width / this.gridSize);
        const rows = Math.ceil(canvas.height / this.gridSize);
        
        for (let y = 0; y < rows; y++) {
            for (let x = 0; x < cols; x++) {
                const angle = Math.sin(x * 0.1) * Math.cos(y * 0.1) * Math.PI * 2;
                const index = y * cols + x;
                this.flowField[index] = {
                    x: Math.cos(angle),
                    y: Math.sin(angle)
                };
            }
        }
    },
    
    getParticleColor: function() {
        // Color palette inspired by the PyGame version with blues, cyans and some purple accents
        const hue = 190 + Math.random() * 40; // Blue to cyan range
        const saturation = 70 + Math.random() * 30;
        const brightness = 70 + Math.random() * 30;
        
        // Sometimes add a purple accent
        if (Math.random() < 0.1) {
            return `hsl(${280 + Math.random() * 20}, ${saturation}%, ${brightness}%)`;
        }
        
        return `hsl(${hue}, ${saturation}%, ${brightness}%)`;
    },
    
    update: function() {
        // Update the flow field over time
        this.fieldTime += this.updateRate;
        
        // Check if any ships are affecting the fluid
        let ships = [];
        if (gameState && gameState.ships) {
            for (const id in gameState.ships) {
                const ship = gameState.ships[id];
                if (ship.x !== undefined && ship.y !== undefined) {
                    ships.push({
                        x: ship.x,
                        y: ship.y,
                        vx: ship.vx || 0,
                        vy: ship.vy || 0,
                        angle: ship.angle,
                        thrusting: ship.thrusting
                    });
                }
            }
        }
        
        // Update each particle
        for (let i = 0; i < this.particles.length; i++) {
            const p = this.particles[i];
            
            // Find the flow field cell this particle is in
            const cols = Math.ceil(canvas.width / this.gridSize);
            const cellX = Math.floor(p.x / this.gridSize);
            const cellY = Math.floor(p.y / this.gridSize);
            const index = cellY * cols + cellX;
            
            // Get flow direction from the field
            let flowX = 0;
            let flowY = 0;
            
            if (index >= 0 && index < this.flowField.length) {
                flowX = this.flowField[index].x;
                flowY = this.flowField[index].y;
            }
            
            // Apply perlin-like noise to make movement more organic
            const noise = this.simplex2(p.x * 0.003, p.y * 0.003);
            const noise2 = this.simplex2(p.x * 0.006 + 100, p.y * 0.006 + 100);
            
            flowX += noise * this.turbulence;
            flowY += noise2 * this.turbulence;
            
            // Apply all ships' influence on nearby particles
            for (const ship of ships) {
                const dx = p.x - ship.x;
                const dy = p.y - ship.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                
                if (dist < this.influenceRadius) {
                    // Calculate influence factor (stronger closer to ship)
                    const influence = Math.pow(1 - dist / this.influenceRadius, 2) * 2;
                    
                    // Get ship's movement vector and speed
                    const shipSpeed = Math.sqrt(ship.vx * ship.vx + ship.vy * ship.vy);
                    
                    // Convert angle to radians if needed
                    let shipAngle = ship.angle;
                    if (Math.abs(shipAngle) > Math.PI * 2) {
                        shipAngle = shipAngle * Math.PI / 180;
                    }
                    
                    const shipDirectionX = Math.cos(shipAngle);
                    const shipDirectionY = Math.sin(shipAngle);
                    
                    // Push particles away from ship's direction of travel
                    flowX += shipDirectionX * influence * shipSpeed * 0.05;
                    flowY += shipDirectionY * influence * shipSpeed * 0.05;
                    
                    // Add turbulence near ship
                    flowX += (Math.random() - 0.5) * influence * 1.0;
                    flowY += (Math.random() - 0.5) * influence * 1.0;
                    
                    // Enhanced effect when ship is thrusting
                    if (ship.thrusting) {
                        // Calculate point behind ship
                        const behindX = ship.x - shipDirectionX * 30;
                        const behindY = ship.y - shipDirectionY * 30;
                        
                        // Distance from particle to behind ship
                        const bDx = p.x - behindX;
                        const bDy = p.y - behindY;
                        const bDist = Math.sqrt(bDx * bDx + bDy * bDy);
                        
                        if (bDist < 80) {
                            const thrustInfluence = Math.pow(1 - bDist / 80, 2) * 5;
                            flowX -= shipDirectionX * thrustInfluence;
                            flowY -= shipDirectionY * thrustInfluence;
                            
                            // Add more turbulence in thrust wake
                            flowX += (Math.random() - 0.5) * thrustInfluence * 2;
                            flowY += (Math.random() - 0.5) * thrustInfluence * 2;
                        }
                    }
                }
            }
            
            // Apply flow to particle velocity with smooth transition
            p.vx = p.vx * 0.95 + flowX * this.flowSpeed * 0.05;
            p.vy = p.vy * 0.95 + flowY * this.flowSpeed * 0.05;
            
            // Add slight random movement
            p.vx += (Math.random() - 0.5) * p.turbulence;
            p.vy += (Math.random() - 0.5) * p.turbulence;
            
            // Update position
            p.x += p.vx;
            p.y += p.vy;
            
            // Add to trail
            p.trail.push({x: p.x, y: p.y, age: 0});
            if (p.trail.length > p.maxTrail) {
                p.trail.shift();
            }
            
            // Age the trail
            for (let j = 0; j < p.trail.length; j++) {
                p.trail[j].age++;
            }
            
            // Wrap around screen edges
            if (p.x < 0) p.x = canvas.width;
            if (p.x > canvas.width) p.x = 0;
            if (p.y < 0) p.y = canvas.height;
            if (p.y > canvas.height) p.y = 0;
            
            // Age particles
            p.age += 0.1;
            if (p.age > 100) {
                // Reset old particles
                p.x = Math.random() * canvas.width;
                p.y = Math.random() * canvas.height;
                p.trail = [];
                p.age = 0;
                p.color = this.getParticleColor();
            }
        }
    },
    
    draw: function() {
        // Set global alpha for particles
        ctx.globalAlpha = 0.4;
        
        // Draw particles with trails
        for (let i = 0; i < this.particles.length; i++) {
            const p = this.particles[i];
            
            // Draw trail
            if (p.trail.length > 1) {
                ctx.beginPath();
                ctx.strokeStyle = p.color;
                ctx.lineWidth = p.size * 0.8;
                
                // Draw trail with fading effect
                for (let j = 0; j < p.trail.length - 1; j++) {
                    const t1 = p.trail[j];
                    const t2 = p.trail[j+1];
                    
                    // Calculate alpha based on age
                    const alpha = 1 - (t1.age / 20);
                    if (alpha <= 0) continue;
                    
                    ctx.globalAlpha = alpha * 0.2;
                    
                    ctx.beginPath();
                    ctx.moveTo(t1.x, t1.y);
                    ctx.lineTo(t2.x, t2.y);
                    ctx.stroke();
                }
            }
            
            // Draw particle
            ctx.globalAlpha = 0.5;
            ctx.fillStyle = p.color;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            ctx.fill();
        }
        
        // Reset alpha
        ctx.globalAlpha = 1.0;
    },
    
    // Simplified Perlin noise implementation
    simplex2: function(x, y) {
        // Use time as a third dimension for variation
        const time = this.fieldTime * 0.1;
        
        // Create some pseudo-perlin noise with sin/cos
        return Math.sin(x * 3.1 + time) * Math.cos(y * 2.7 + time * 0.8) * 0.5 +
               Math.sin(x * 5.2 + y * 1.9 + time * 1.2) * 0.25 +
               Math.cos(x * 2.6 - y * 3.3 + time * 0.7) * 0.25;
    }
};

// Audio system implementation
const audioContext = new (window.AudioContext || window.webkitAudioContext)();
let backgroundMusic;
let isAudioInitialized = false;
let soundEffects = {};

// Initialize when the document is loaded
document.addEventListener('DOMContentLoaded', init);

// Initialize the game
function init() {
    // Check if we're on the login screen
    const loginScreen = document.getElementById('loginScreen');
    if (loginScreen) {
        // Setup connection form
        const connectForm = document.getElementById('connectForm');
        connectForm.addEventListener('submit', (e) => {
            e.preventDefault();
            playerName = document.getElementById('nameInput').value.trim();
            if (playerName) {
                document.getElementById('loginScreen').style.display = 'none';
                document.getElementById('gameScreen').style.display = 'block';
                
                // Now that we have visibility, initialize the canvas
                initGameCanvas();
            }
        });
    } else {
        // No login screen, initialize directly
        initGameCanvas();
    }
}

// Initialize the game canvas and start the WebSocket
function initGameCanvas() {
    // Create the canvas
    canvas = document.getElementById('gameCanvas');
    ctx = canvas.getContext('2d');
    
    // Set canvas size to match window
    canvas.width = window.innerWidth - 20;
    canvas.height = window.innerHeight - 20;
    
    // Initialize fluid field
    fluidField.init();
    
    // Set up audio system
    setupAudio();
    
    // Set up keyboard event listeners
    setupKeyboardControls();
    
    // Set up WebSocket connection
    connectToServer();
    
    // Start the game loop
    lastUpdateTime = Date.now();
    gameLoop();
    
    // Set resize handler to update canvas size
    window.addEventListener('resize', function() {
        canvas.width = window.innerWidth - 20;
        canvas.height = window.innerHeight - 20;
        fluidField.init(); // Reinitialize fluid field when canvas size changes
    });
}

// Function to connect to the WebSocket server
function connectToServer() {
    try {
        console.log("Attempting to connect to WebSocket server...");
        
        // Create WebSocket connection - using port 8081 (not 8080)
        // The WebSocket server is running on port 8081 while the HTTP server is on 8080
        const wsUrl = `ws://${window.location.hostname}:8081`;
        console.log(`Connecting to: ${wsUrl}`);
        socket = new WebSocket(wsUrl);
        
        socket.onopen = function() {
            console.log('Connected to server successfully');
            // Send player info when connection is established
            socket.send(JSON.stringify({
                type: 'join',
                player_name: playerName || 'Player'
            }));
        };
        
        socket.onmessage = function(event) {
            try {
                const message = JSON.parse(event.data);
                console.log("Received message:", message.type);
                
                if (message.type === 'game_state') {
                    // Update game state
                    gameState = message.data;
                    
                    // Get player ID from server response
                    if (!playerId) {
                        // Find our player ID by matching player_name
                        for (const id in gameState.ships) {
                            if (gameState.ships[id].player_name === playerName) {
                                playerId = id;
                                console.log('Found player ID:', playerId);
                                break;
                            }
                        }
                    }
                } else if (message.type === 'hit') {
                    // Play explosion sound when an asteroid is hit
                    playSound('explosion', 0.5);
                }
            } catch (error) {
                console.error("Error parsing message:", error, event.data);
            }
        };
        
        socket.onclose = function(event) {
            console.log(`Disconnected from server: code=${event.code}, reason=${event.reason}`);
            // Attempt to reconnect after 3 seconds
            setTimeout(connectToServer, 3000);
        };
        
        socket.onerror = function(error) {
            console.error('WebSocket error:', error);
            // Instead of immediately reconnecting, show a visible error message
            if (ctx) {
                ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                ctx.fillRect(canvas.width/2 - 200, canvas.height/2 - 60, 400, 120);
                ctx.fillStyle = 'red';
                ctx.font = '18px Arial';
                ctx.textAlign = 'center';
                ctx.fillText('Connection Error!', canvas.width/2, canvas.height/2 - 30);
                ctx.fillStyle = 'white';
                ctx.font = '14px Arial';
                ctx.fillText('Check if the server is running and refresh the page.', canvas.width/2, canvas.height/2);
                ctx.fillText('See console for details (F12)', canvas.width/2, canvas.height/2 + 30);
            }
        };
    } catch (err) {
        console.error("Error setting up WebSocket:", err);
    }
}

// Set up keyboard controls
function setupKeyboardControls() {
    document.addEventListener('keydown', function(e) {
        // Store key state
        keys[e.key] = true;
        
        // If this is the first interaction, initialize audio
        if (!isAudioInitialized) {
            initializeAudioOnInteraction();
        }
        
        // Send control updates to server
        sendControlUpdate();
    });
    
    document.addEventListener('keyup', function(e) {
        // Update key state
        keys[e.key] = false;
        
        // Send control updates to server
        sendControlUpdate();
    });
}

// Function to send control updates to the server
function sendControlUpdate() {
    if (socket && socket.readyState === WebSocket.OPEN) {
        // Calculate rotation value (1 = left, -1 = right, 0 = none)
        let rotation = 0;
        if (keys['ArrowLeft'] || keys['a']) rotation += 1;
        if (keys['ArrowRight'] || keys['d']) rotation -= 1;
        
        const controls = {
            type: 'input',
            data: {
                rotation: rotation,
                thrust: keys['ArrowUp'] || keys['w'] || false,
                fire: keys[' '] || keys['f'] || false
            }
        };
        
        // Only send if controls have changed
        const controlsJson = JSON.stringify(controls);
        if (controlsJson !== lastControlsJson) {
            socket.send(controlsJson);
            lastControlsJson = controlsJson;
        }
    }
}

// Clear the screen
function clearScreen() {
    ctx.fillStyle = 'black';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
}

// Draw an asteroid
function drawAsteroid(asteroid) {
    const x = asteroid.x;
    const y = asteroid.y;
    // Calculate radius based on level (match server's logic)
    const level = asteroid.level || 1;
    const radius = (4 - level) * 15;
    
    // Create vertices if not present
    if (!asteroid.vertices) {
        asteroid.vertices = Array(8).fill(0).map(() => 0.8 + Math.random() * 0.4);
        asteroid.rotation = 0;
        asteroid.rotationSpeed = (Math.random() - 0.5) * 0.02; // Add rotation speed
    }
    
    // Update rotation based on rotation speed
    asteroid.rotation += asteroid.rotationSpeed;
    
    // FIXED: Update position based on velocity if available
    if (asteroid.vx !== undefined && asteroid.vy !== undefined) {
        asteroid.x += asteroid.vx;
        asteroid.y += asteroid.vy;
        
        // Wrap around screen edges
        if (asteroid.x < 0) asteroid.x = canvas.width;
        if (asteroid.x > canvas.width) asteroid.x = 0;
        if (asteroid.y < 0) asteroid.y = canvas.height;
        if (asteroid.y > canvas.height) asteroid.y = 0;
    }
    
    // Draw the asteroid
    ctx.strokeStyle = '#aaa';
    ctx.lineWidth = 2;
    ctx.beginPath();
    
    // Draw an irregular polygon for the asteroid
    for (let i = 0; i < asteroid.vertices.length; i++) {
        const vertex = asteroid.vertices[i];
        const angle = (i / asteroid.vertices.length) * Math.PI * 2;
        const distance = radius * vertex;
        
        const vx = x + distance * Math.cos(angle + asteroid.rotation);
        const vy = y + distance * Math.sin(angle + asteroid.rotation);
        
        if (i === 0) {
            ctx.moveTo(vx, vy);
        } else {
            ctx.lineTo(vx, vy);
        }
    }
    
    ctx.closePath();
    ctx.stroke();
    
    // Fill with a slight gradient for 3D effect
    const gradient = ctx.createRadialGradient(
        x, y, 0,
        x, y, radius
    );
    gradient.addColorStop(0, '#555');
    gradient.addColorStop(1, '#333');
    ctx.fillStyle = gradient;
    ctx.fill();
}

// Draw a ship
function drawShip(ship) {
    // Get ship position (could be in rect property or directly in x,y)
    const x = ship.rect ? ship.rect.centerx : ship.x;
    const y = ship.rect ? ship.rect.centery : ship.y;
    
    // Ensure we have a valid angle value
    let angle = ship.angle || 0;
    
    // Convert from degrees to radians if needed (PyGame uses degrees, we use radians)
    const angleRad = (Math.abs(angle) > Math.PI * 2) ? (angle * Math.PI / 180) : angle;
    
    const size = 15;
    
    // Determine ship color based on color_idx
    let color = [255, 255, 255]; // Default white
    if (ship.color_idx >= 0 && ship.color_idx < SHIP_COLORS.length) {
        color = SHIP_COLORS[ship.color_idx];
    }
    
    // Check if this is our ship
    const isOurShip = ship.id === playerId;
    
    // Skip if ship is invisible (blinking during invulnerability)
    if (ship.visible === false) return;
    
    // Save context for rotation
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(angleRad);
    
    // Draw the ship - FIXED: Adjusted the shape to point in the correct direction
    ctx.strokeStyle = `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
    ctx.lineWidth = 2;
    ctx.beginPath();
    // The ship should point right when angle is 0
    ctx.moveTo(size, 0);           // Nose of ship
    ctx.lineTo(-size/2, -size/2);  // Bottom-left corner
    ctx.lineTo(-size/4, 0);        // Back center
    ctx.lineTo(-size/2, size/2);   // Top-left corner
    ctx.closePath();
    ctx.stroke();
    
    // Fill with a gradient for a 3D effect
    const gradient = ctx.createRadialGradient(0, 0, 0, 0, 0, size);
    gradient.addColorStop(0, `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.7)`);
    gradient.addColorStop(1, `rgba(${color[0]}, ${color[1]}, ${color[2]}, 0.1)`);
    ctx.fillStyle = gradient;
    ctx.fill();
    
    // Draw engine flames when thrusting
    if (ship.thrusting) {
        // Randomize the flame length for a more dynamic look
        const flameLength = size * (0.6 + Math.random() * 0.4);
        
        // Draw the flame - FIXED: Positioned correctly behind the ship
        ctx.beginPath();
        ctx.moveTo(-size/4, 0);
        ctx.lineTo(-size/2 - flameLength, 0);
        ctx.lineTo(-size/4, size/4);
        ctx.lineTo(-size/3, 0);
        ctx.lineTo(-size/4, -size/4);
        ctx.closePath();
        
        // Create flame gradient
        const flameGradient = ctx.createLinearGradient(-size/4, 0, -size/2 - flameLength, 0);
        flameGradient.addColorStop(0, 'rgba(255, 255, 50, 0.9)');
        flameGradient.addColorStop(0.3, 'rgba(255, 120, 0, 0.8)');
        flameGradient.addColorStop(1, 'rgba(255, 20, 0, 0)');
        
        ctx.fillStyle = flameGradient;
        ctx.fill();
    }
    
    // Show player name above ship
    if (ship.player_name) {
        ctx.fillStyle = `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
        ctx.textAlign = 'center';
        ctx.font = '12px Arial';
        ctx.fillText(ship.player_name, 0, -size - 5);
    }
    
    // Restore context
    ctx.restore();
}

// Draw the scoreboard
function drawScoreboard() {
    if (!gameState) return;
    
    // Sort players by score
    const players = [];
    for (const id in gameState.ships) {
        players.push({
            id: id,
            name: gameState.ships[id].player_name || `Player ${id}`,
            score: gameState.scores && gameState.scores[id] || 0,
            color_idx: gameState.ships[id].color_idx
        });
    }
    
    players.sort((a, b) => b.score - a.score);
    
    // Draw scoreboard
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    ctx.fillRect(10, 10, 200, 30 + players.length * 25);
    
    // Title
    ctx.fillStyle = 'white';
    ctx.font = 'bold 16px Arial';
    ctx.textAlign = 'left';
    ctx.fillText('Players', 20, 30);
    ctx.fillText('Score', 150, 30);
    
    // Player scores
    ctx.font = '14px Arial';
    for (let i = 0; i < players.length; i++) {
        const player = players[i];
        const y = 55 + i * 25;
        
        // Determine color
        let color = [255, 255, 255]; // Default white
        if (player.color_idx >= 0 && player.color_idx < SHIP_COLORS.length) {
            color = SHIP_COLORS[player.color_idx];
        }
        
        // Highlight current player
        if (player.id === playerId) {
            ctx.fillStyle = 'rgba(255, 255, 100, 0.3)';
            ctx.fillRect(15, y - 15, 190, 20);
        }
        
        // Player name and score
        ctx.fillStyle = `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
        ctx.fillText(player.name, 20, y);
        ctx.fillText(player.score.toString(), 150, y);
    }
    
    // Also display level if it's in the game state
    if (gameState.level) {
        ctx.fillStyle = 'white';
        ctx.font = 'bold 16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(`LEVEL ${gameState.level}`, canvas.width / 2, 30);
    }
}

// Set up audio system
function setupAudio() {
    // We'll initialize audio on first user interaction
    document.addEventListener('click', initializeAudioOnInteraction, { once: true });
    document.addEventListener('keydown', initializeAudioOnInteraction, { once: true });
}

function initializeAudioOnInteraction() {
    if (!isAudioInitialized) {
        isAudioInitialized = true;
        audioContext.resume().then(() => {
            console.log('Audio context started');
            generateBackgroundMusic();
            initSoundEffects();
        });
    }
}

// Generate lo-fi background music similar to the PyGame version
function generateBackgroundMusic() {
    console.log("Generating background music...");
    
    const musicLength = 30; // 30 seconds loop
    const sampleRate = audioContext.sampleRate;
    const numSamples = musicLength * sampleRate;
    
    // Create buffer for the music
    const buffer = audioContext.createBuffer(2, numSamples, sampleRate);
    const leftChannel = buffer.getChannelData(0);
    const rightChannel = buffer.getChannelData(1);
    
    // Define a chord progression with jazz-inspired voicings (F minor / Ab major pentatonic)
    const bassProgressions = [
        // Fm7 - Bbm7 - Ebmaj7 - Ab6
        [174.61, 174.61, 174.61, 185.00, 233.08, 233.08, 233.08, 220.00, 
         311.13, 311.13, 311.13, 293.66, 207.65, 207.65, 220.00, 233.08],
        
        // Cm7 - Fm7 - Bbm7 - G7b9
        [130.81, 130.81, 146.83, 130.81, 174.61, 174.61, 174.61, 185.00,
         233.08, 233.08, 220.00, 196.00, 196.00, 196.00, 185.00, 174.61],
    ];
    
    // Synth pad chord voicings with extensions for richness
    const padChords = [
        // Fm7 - Bbm7 - Ebmaj7 - Ab6 (first progression)
        [
            [174.61, 220.00, 261.63, 349.23],  // Fm7 (F, A♭, C, E♭)
            [233.08, 293.66, 349.23, 415.30],  // B♭m7 (B♭, D♭, F, A♭)
            [311.13, 392.00, 466.16, 523.25],  // E♭maj7 (E♭, G, B♭, D)
            [207.65, 261.63, 349.23, 415.30]   // A♭6 (A♭, C, E♭, F)
        ],
        
        // Cm7 - Fm7 - Bbm7 - G7b9 (second progression)
        [
            [130.81, 155.56, 196.00, 261.63],  // Cm7 (C, E♭, G, B♭)
            [174.61, 220.00, 261.63, 329.63],  // Fm7 (F, A♭, C, E♭)
            [233.08, 293.66, 349.23, 415.30],  // B♭m7 (B♭, D♭, F, A♭)
            [196.00, 246.94, 293.66, 415.30]   // G7b9 (G, B, D, F, A♭)
        ],
    ];
    
    // F minor pentatonic scale for melodies: F, Ab, Bb, C, Eb
    const fMinorPentatonic = [349.23, 415.30, 466.16, 523.25, 622.25];  // F4, Ab4, Bb4, C5, Eb5
    
    // Melody patterns using the pentatonic scale
    const melodyPatterns = [
        // Pattern 1: Rising then falling
        [fMinorPentatonic[0], fMinorPentatonic[1], fMinorPentatonic[3], fMinorPentatonic[4], 
         fMinorPentatonic[4], fMinorPentatonic[3], fMinorPentatonic[1], fMinorPentatonic[0]],
        
        // Pattern 2: Arpeggiated with octave jumps
        [fMinorPentatonic[0], fMinorPentatonic[2], fMinorPentatonic[4], fMinorPentatonic[0]*2, 
         fMinorPentatonic[4], fMinorPentatonic[2], fMinorPentatonic[1], fMinorPentatonic[0]],
    ];
    
    // Define drum patterns
    // 1 = kick, 2 = snare, 3 = hihat closed, 4 = hihat open, 5 = rim, 6 = shaker
    const drumPatterns = [
        // Main groove with rim
        [1, 0, 3, 5, 2, 0, 3, 4, 0, 6, 3, 0, 2, 5, 3, 0],
        
        // Variation with more kicks
        [1, 0, 3, 0, 2, 1, 3, 0, 1, 0, 3, 4, 2, 0, 3, 6],
    ];
    
    // Time parameters
    const beatMs = 125;  // 120 BPM (500ms per beat, 125ms per 16th note)
    const beatsPerPattern = 16;  // 16 16th notes per pattern
    const patternDuration = beatMs * beatsPerPattern / 1000;  // in seconds
    const patternSamples = patternDuration * sampleRate;
    const numPatterns = Math.floor(musicLength / patternDuration);
    
    // Filter state for lo-fi effect
    let prevSample = 0;
    const filterAlpha = 0.3;  // Low-pass filter coefficient
    let highFreqPrev = 0;  // For high-pass filter
    const highFreqAlpha = 0.05;  // High-pass filter coefficient
    
    // Helper functions for drum sounds
    function getKick(t, duration = 0.08) {
        t = t % duration;
        if (t < duration * 0.1) {
            // Main body with frequency sweep
            const body = Math.sin(2 * Math.PI * (120 - t * 2000)) * (1 - t/(duration * 0.1));
            // Add click transient
            const click = Math.sin(2 * Math.PI * 1800 * t) * Math.exp(-t * 250);
            return body * 0.85 + click * 0.15;
        }
        return 0;
    }
    
    function getSnare(t, duration = 0.08) {
        t = t % duration;
        const env = Math.exp(-t / (duration * 0.15));
        // Body tone
        const tone = Math.sin(2 * Math.PI * 180 * t) * env * 0.2;
        // Noise component with bandpass effect
        const noise = (Math.random() * 2 - 1) * Math.exp(-t / (duration * 0.1)) * 0.7;
        // Lower noise for body
        const bodyNoise = (Math.random() * 1 - 0.5) * Math.exp(-t / (duration * 0.2)) * 0.3;
        return tone + noise + bodyNoise;
    }
    
    function getHihatClosed(t, duration = 0.04) {
        t = t % duration;
        const env = Math.exp(-t / (duration * 0.08));  // Faster decay
        // High-frequency noise with subtle resonance
        const noise = (Math.random() * 1.4 - 0.7) * env;
        // Add subtle tone at around 8-10kHz
        const tone = Math.sin(2 * Math.PI * 9000 * t) * env * 0.1;
        return noise * 0.6 + tone * 0.1;
    }
    
    function getHihatOpen(t, duration = 0.12) {
        t = t % duration;
        const env = Math.exp(-t / (duration * 0.4));  // Longer decay than closed
        // Similar to closed hihat but with longer decay
        const noise = (Math.random() * 1.4 - 0.7) * env;
        const tone = Math.sin(2 * Math.PI * 8500 * t) * env * 0.1;
        return noise * 0.5 + tone * 0.1;
    }
    
    function getRim(t, duration = 0.06) {
        t = t % duration;
        const env = Math.exp(-t / (duration * 0.05));  // Very short decay
        // Sharp attack with mid-range tone
        const tone = Math.sin(2 * Math.PI * 800 * t) * env;
        return tone * 0.4;
    }
    
    function getShaker(t, duration = 0.07) {
        t = t % duration;
        const env = Math.exp(-t / (duration * 0.15));
        // Filtered high-frequency noise
        return (Math.random() - 0.5) * env * 0.25;
    }
    
    // Generate the music data
    for (let pattern = 0; pattern < numPatterns; pattern++) {
        // Choose patterns for this section
        const progressionIdx = pattern % bassProgressions.length;
        const currentBass = bassProgressions[progressionIdx];
        const currentPads = padChords[progressionIdx];
        const currentMelody = melodyPatterns[pattern % melodyPatterns.length];
        const currentDrums = drumPatterns[pattern % drumPatterns.length];
        
        for (let beat = 0; beat < beatsPerPattern; beat++) {
            const beatStartSample = Math.floor((pattern * patternDuration + beat * beatMs/1000) * sampleRate);
            const beatEndSample = Math.floor(beatStartSample + (beatMs/1000) * sampleRate);
            const beatSamples = beatEndSample - beatStartSample;
            
            // Current notes from patterns
            const bassIdx = beat % currentBass.length;
            const bassFreq = currentBass[bassIdx];
            
            const chordIdx = Math.floor(beat / 4);  // Change chord every quarter note
            const padChord = currentPads[chordIdx >= currentPads.length ? currentPads.length - 1 : chordIdx];
            
            // Get melody note
            let melodyFreq = 0;
            let playMelody = false;
            if (beat < currentMelody.length) {
                melodyFreq = currentMelody[beat];
                playMelody = melodyFreq > 0;
            }
            
            // Get drum hit
            let drumHit = 0;
            if (beat < currentDrums.length) {
                drumHit = currentDrums[beat];
            }
            
            // Generate samples for this beat
            for (let i = 0; i < beatSamples; i++) {
                const sampleIdx = i / beatSamples;  // 0 to 1 position within the beat
                const t = (pattern * patternDuration + beat * beatMs/1000 + i / sampleRate);  // time in seconds
                let value = 0;
                
                // Add bass with some envelope
                const bassEnv = Math.exp(-sampleIdx * 2);  // Envelope decay over the beat
                if (bassFreq > 0) {
                    // Calculate phase for oscillator
                    const bassPhase = ((t * bassFreq) % 1);
                    // Simple bass sound - mix of sine and square for harmonics
                    const bassSine = Math.sin(2 * Math.PI * bassPhase);
                    const bassSquare = Math.sign(Math.sin(2 * Math.PI * bassPhase));
                    const bassValue = bassSine * 0.7 + bassSquare * 0.3;
                    
                    // Add to mix with envelope
                    value += bassValue * bassEnv * 0.2;  // Bass volume
                }
                
                // Add pad chord
                const padEnv = 1.0;  // Pads sustain throughout
                let padValue = 0;
                for (const padFreq of padChord) {
                    const padPhase = ((t * padFreq) % 1);
                    // Use sine waves for pads
                    const noteValue = Math.sin(2 * Math.PI * padPhase);
                    // Random weight for more organic feel
                    const noteWeight = 0.5 + Math.random() * 0.5;
                    padValue += noteValue * noteWeight / padChord.length;
                }
                
                // Add to mix with envelope
                value += padValue * padEnv * 0.15;  // Pad volume
                
                // Add melody with more expressive articulation
                if (playMelody) {
                    const melodyEnv = Math.exp(-sampleIdx * 3);  // Faster decay for melody
                    const melodyPhase = ((t * melodyFreq) % 1);
                    // Use sawtooth for lead sound
                    const melodyValue = 2.0 * melodyPhase - 1.0;
                    value += melodyValue * melodyEnv * 0.15;  // Melody volume
                }
                
                // Add drums
                if (drumHit > 0) {
                    let drumValue = 0;
                    const drumT = i / sampleRate;
                    
                    if (drumHit === 1) {  // Kick
                        drumValue = getKick(drumT) * 1.2;  // Kick volume
                    } else if (drumHit === 2) {  // Snare
                        drumValue = getSnare(drumT) * 0.9;  // Snare volume
                    } else if (drumHit === 3) {  // Hi-hat closed
                        drumValue = getHihatClosed(drumT) * 0.8;  // Closed hi-hat volume
                    } else if (drumHit === 4) {  // Hi-hat open
                        drumValue = getHihatOpen(drumT) * 0.6;  // Open hi-hat volume
                    } else if (drumHit === 5) {  // Rim
                        drumValue = getRim(drumT) * 0.7;  // Rim volume
                    } else if (drumHit === 6) {  // Shaker
                        drumValue = getShaker(drumT) * 0.6;  // Shaker volume
                    }
                    
                    value += drumValue;
                }
                
                // Add vinyl crackle effect
                if (Math.random() < 0.003) {
                    const crackle = (Math.random() * 0.02 - 0.01);
                    value += crackle;
                }
                
                // Apply lo-fi filter effect
                value = value * 0.7 + prevSample * 0.3;  // Low-pass
                const highFreq = value - prevSample;  // High-pass component
                value += highFreq * 0.1;  // Add a bit of high-end for clarity
                
                prevSample = value;
                
                // Limit output to prevent clipping
                value = Math.tanh(value);
                
                // Apply a slight stereo effect
                const stereoOffset = Math.sin(t * 0.5) * 0.1;
                const leftGain = 1.0 - Math.max(0, stereoOffset);
                const rightGain = 1.0 - Math.max(0, -stereoOffset);
                
                // Write to both channels with slight variation for stereo effect
                const bufferPos = beatStartSample + i;
                if (bufferPos < numSamples) {
                    leftChannel[bufferPos] = value * leftGain;
                    rightChannel[bufferPos] = value * rightGain;
                }
            }
        }
    }
    
    // Normalize the buffer to prevent clipping
    let maxSample = 0;
    for (let i = 0; i < numSamples; i++) {
        maxSample = Math.max(maxSample, Math.abs(leftChannel[i]), Math.abs(rightChannel[i]));
    }
    
    if (maxSample > 0) {
        const gain = 0.9 / maxSample;  // Leave a little headroom
        for (let i = 0; i < numSamples; i++) {
            leftChannel[i] *= gain;
            rightChannel[i] *= gain;
        }
    }
    
    // Create the source node and connect it to the destination
    backgroundMusic = audioContext.createBufferSource();
    backgroundMusic.buffer = buffer;
    backgroundMusic.loop = true;
    
    // Add a volume control
    const gainNode = audioContext.createGain();
    gainNode.gain.value = 0.7;  // Adjust the volume
    
    // Connect the nodes: source -> gain -> destination
    backgroundMusic.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    // Start playing the music
    backgroundMusic.start();
    console.log("Background music started");
}

// Initialize sound effects
function initSoundEffects() {
    const effectsToLoad = {
        'laser': createLaserSound,
        'explosion': createExplosionSound,
        'thrust': createThrustSound
    };
    
    // Create each sound effect
    for (const [name, createFn] of Object.entries(effectsToLoad)) {
        const buffer = createFn();
        soundEffects[name] = {
            buffer: buffer,
            lastPlayed: 0 // For rate limiting
        };
    }
}

// Create laser sound effect
function createLaserSound() {
    const duration = 0.2; // seconds
    const sampleRate = audioContext.sampleRate;
    const numSamples = duration * sampleRate;
    const buffer = audioContext.createBuffer(1, numSamples, sampleRate);
    const channel = buffer.getChannelData(0);
    
    // Frequency sweep from high to low
    const startFreq = 1200;
    const endFreq = 600;
    
    for (let i = 0; i < numSamples; i++) {
        const t = i / sampleRate;
        const progress = i / numSamples;
        
        // Envelope - quick attack, longer decay
        const env = Math.exp(-progress * 15);
        
        // Frequency sweep
        const freq = startFreq + (endFreq - startFreq) * progress;
        
        // Oscillator - mix of sine and noise for a sci-fi sound
        const sine = Math.sin(2 * Math.PI * freq * t);
        const noise = Math.random() * 2 - 1;
        
        // Combine with envelope
        channel[i] = (sine * 0.8 + noise * 0.2) * env;
    }
    
    return buffer;
}

// Create explosion sound effect
function createExplosionSound() {
    const duration = 0.5; // seconds
    const sampleRate = audioContext.sampleRate;
    const numSamples = duration * sampleRate;
    const buffer = audioContext.createBuffer(1, numSamples, sampleRate);
    const channel = buffer.getChannelData(0);
    
    // Noise-based explosion with low frequency rumble
    for (let i = 0; i < numSamples; i++) {
        const t = i / sampleRate;
        const progress = i / numSamples;
        
        // Envelope - quick attack, medium decay
        const env = Math.exp(-progress * 8);
        
        // Mix of noise and low-frequency rumble
        const noise = Math.random() * 2 - 1;
        const rumble = Math.sin(2 * Math.PI * 80 * t) * 0.5 + 
                       Math.sin(2 * Math.PI * 60 * t) * 0.3 +
                       Math.sin(2 * Math.PI * 40 * t) * 0.2;
        
        // Combine with envelope
        channel[i] = (noise * 0.6 + rumble * 0.4) * env;
    }
    
    return buffer;
}

// Create thrust sound effect
function createThrustSound() {
    const duration = 0.3; // seconds
    const sampleRate = audioContext.sampleRate;
    const numSamples = duration * sampleRate;
    const buffer = audioContext.createBuffer(1, numSamples, sampleRate);
    const channel = buffer.getChannelData(0);
    
    // Filtered noise for rocket/thrust sound
    for (let i = 0; i < numSamples; i++) {
        const progress = i / numSamples;
        
        // Envelope - sustain with slight fade
        const env = 1.0 - progress * 0.5;
        
        // Generate filtered noise
        const noise = Math.random() * 2 - 1;
        
        // Low-pass filter (simple implementation)
        if (i > 0) {
            channel[i] = (noise * 0.2 + channel[i-1] * 0.8) * env;
        } else {
            channel[i] = noise * env;
        }
    }
    
    return buffer;
}

// Play a sound effect with rate limiting
function playSound(name, volume = 1.0) {
    if (!isAudioInitialized || !soundEffects[name]) return;
    
    const now = Date.now();
    const sound = soundEffects[name];
    
    // Rate limiting to prevent sound overlapping too much
    const minDelay = {
        'laser': 80,     // Can fire laser every 80ms
        'explosion': 200, // Explosions less frequent
        'thrust': 150     // Thrust every 150ms
    };
    
    if (now - sound.lastPlayed < minDelay[name]) return;
    sound.lastPlayed = now;
    
    // Create source node
    const source = audioContext.createBufferSource();
    source.buffer = sound.buffer;
    
    // Add volume control
    const gainNode = audioContext.createGain();
    gainNode.gain.value = volume;
    
    // Connect nodes
    source.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    // Start playing
    source.start();
}

// Update the game loop to handle sound effects
function updateGameLoop() {
    // Play laser sounds when others fire
    for (const laser of gameState.lasers) {
        // Check if this is a new laser
        if (laser.created > lastUpdateTime / 1000) {
            playSound('laser', 0.2);
        }
    }
    
    // Play thrust sound if our ship is thrusting
    const ourShip = playerId && gameState.ships[playerId];
    if (ourShip && ourShip.thrusting) {
        playSound('thrust', 0.15);
    }
}

// Main game loop
function gameLoop() {
    // Calculate delta time
    const now = Date.now();
    const dt = (now - lastUpdateTime) / 1000;
    lastUpdateTime = now;
    
    // Clear the screen
    clearScreen();
    
    // Update and draw the fluid field
    fluidField.update();
    fluidField.draw();
    
    // Update audio for game events
    if (gameState) {
        updateGameLoop();
        
        // FIXED: Update all positions between server updates for smoother movement
        updateGameObjects(dt);
    }
    
    // Draw game objects
    if (gameState) {
        // Draw all asteroids
        for (const asteroid of gameState.asteroids) {
            drawAsteroid(asteroid);
        }
        
        // Draw all lasers
        for (const laser of gameState.lasers) {
            drawLaser(laser);
        }
        
        // Draw all ships
        for (const id in gameState.ships) {
            drawShip(gameState.ships[id]);
        }
        
        // Draw the scoreboard
        drawScoreboard();
    } else {
        // Draw connecting message if we don't have game state yet
        ctx.fillStyle = 'white';
        ctx.font = '24px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Connecting to server...', canvas.width / 2, canvas.height / 2);
    }
    
    // Continue the game loop
    requestAnimationFrame(gameLoop);
}

// ADDED: Function to update all game objects positions between server updates
function updateGameObjects(dt) {
    // Update asteroid positions
    for (const asteroid of gameState.asteroids) {
        if (asteroid.vx !== undefined && asteroid.vy !== undefined) {
            asteroid.x += asteroid.vx * dt * 60; // Scale by dt for smooth movement
            asteroid.y += asteroid.vy * dt * 60;
            
            // Wrap around screen edges
            if (asteroid.x < 0) asteroid.x = canvas.width;
            if (asteroid.x > canvas.width) asteroid.x = 0;
            if (asteroid.y < 0) asteroid.y = canvas.height;
            if (asteroid.y > canvas.height) asteroid.y = 0;
        }
    }
    
    // Update laser positions
    for (const laser of gameState.lasers) {
        if (laser.vx !== undefined && laser.vy !== undefined) {
            laser.x += laser.vx * dt * 60;
            laser.y += laser.vy * dt * 60;
        }
    }
    
    // Update ship positions
    for (const id in gameState.ships) {
        const ship = gameState.ships[id];
        if (ship.vx !== undefined && ship.vy !== undefined) {
            ship.x += ship.vx * dt * 60;
            ship.y += ship.vy * dt * 60;
            
            // Wrap around screen edges
            if (ship.x < 0) ship.x = canvas.width;
            if (ship.x > canvas.width) ship.x = 0;
            if (ship.y < 0) ship.y = canvas.height;
            if (ship.y > canvas.height) ship.y = 0;
        }
    }
}

// Draw a laser
function drawLaser(laser) {
    const x = laser.x;
    const y = laser.y;
    
    // Convert the color value to an array for easier manipulation
    let colors = [255, 100, 100]; // Default red
    
    // If this laser belongs to a player, use their ship color
    if (laser.player_id && gameState.ships[laser.player_id]) {
        const ship = gameState.ships[laser.player_id];
        if (ship.color_idx >= 0 && ship.color_idx < SHIP_COLORS.length) {
            colors = SHIP_COLORS[ship.color_idx];
        }
    }
    
    // Update laser position based on velocity if available
    if (laser.vx !== undefined && laser.vy !== undefined) {
        laser.x += laser.vx;
        laser.y += laser.vy;
    }
    
    // Calculate the front of the laser
    // Convert angle from degrees to radians if needed
    let angle = laser.angle || 0;
    const angleRad = (Math.abs(angle) > Math.PI * 2) ? (angle * Math.PI / 180) : angle;
    
    const length = 18; // Increased laser length
    const endX = x + Math.cos(angleRad) * length;
    const endY = y + Math.sin(angleRad) * length;
    
    // Draw the glow effect (outer layer)
    const gradient = ctx.createRadialGradient(
        x, y, 0,
        x, y, 10
    );
    gradient.addColorStop(0, `rgba(${colors[0]}, ${colors[1]}, ${colors[2]}, 0.7)`);
    gradient.addColorStop(1, 'rgba(255, 100, 100, 0)');
    
    ctx.beginPath();
    ctx.fillStyle = gradient;
    ctx.arc(x, y, 10, 0, Math.PI * 2);
    ctx.fill();
    
    // Draw the core beam with glow
    ctx.beginPath();
    ctx.strokeStyle = `rgba(${colors[0]}, ${colors[1]}, ${colors[2]}, 0.3)`;
    ctx.lineWidth = 6;
    ctx.moveTo(x, y);
    ctx.lineTo(endX, endY);
    ctx.stroke();
    
    // Middle glow
    ctx.beginPath();
    ctx.strokeStyle = `rgba(${colors[0]}, ${colors[1]}, ${colors[2]}, 0.5)`;
    ctx.lineWidth = 3;
    ctx.moveTo(x, y);
    ctx.lineTo(endX, endY);
    ctx.stroke();
    
    // Core beam
    ctx.beginPath();
    ctx.strokeStyle = `rgb(${colors[0]}, ${colors[1]}, ${colors[2]})`;
    ctx.lineWidth = 1.5;
    ctx.moveTo(x, y);
    ctx.lineTo(endX, endY);
    ctx.stroke();
    
    // Add small dynamic particles along the laser path
    for (let i = 0; i < 3; i++) {
        const t = Math.random();
        const particleX = x + (endX - x) * t;
        const particleY = y + (endY - y) * t;
        const particleSize = 1 + Math.random() * 2;
        
        ctx.beginPath();
        ctx.fillStyle = `rgba(${colors[0]}, ${colors[1]}, ${colors[2]}, ${0.5 + Math.random() * 0.5})`;
        ctx.arc(particleX, particleY, particleSize, 0, Math.PI * 2);
        ctx.fill();
    }
} 