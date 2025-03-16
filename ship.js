class Ship {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        
        // Ship position starts in the middle of the screen
        this.x = canvas.width / 2;
        this.y = canvas.height / 2;
        
        // Ship properties
        this.radius = 15;
        this.angle = 90 / 180 * Math.PI; // Convert to radians, facing up
        this.rotation = 0;
        this.thrusting = false;
        this.thrust = {
            x: 0,
            y: 0
        };
        
        // Ship movement
        this.rotationSpeed = 0.1;
        this.thrustSpeed = 0.1;
        this.friction = 0.05;
        
        // Invulnerability when respawning
        this.invulnerable = false;
        this.invulnerabilityTime = 3000; // 3 seconds
        this.blinkTime = 100; // Blink every 100ms
        this.lastBlinkTime = 0;
        this.visible = true;
    }
    
    rotate(dir) {
        // dir: 1 for right, -1 for left
        this.rotation = dir * this.rotationSpeed;
    }
    
    stopRotation() {
        this.rotation = 0;
    }
    
    toggleThrust(on) {
        this.thrusting = on;
    }
    
    setInvulnerable() {
        this.invulnerable = true;
        setTimeout(() => {
            this.invulnerable = false;
            this.visible = true;
        }, this.invulnerabilityTime);
    }
    
    update(deltaTime) {
        // Handle rotation
        this.angle += this.rotation;
        
        // Handle thrust
        if (this.thrusting) {
            this.thrust.x += this.thrustSpeed * Math.cos(this.angle);
            this.thrust.y -= this.thrustSpeed * Math.sin(this.angle);
        } else {
            // Apply friction when not thrusting
            this.thrust.x *= (1 - this.friction);
            this.thrust.y *= (1 - this.friction);
        }
        
        // Update position
        this.x += this.thrust.x;
        this.y += this.thrust.y;
        
        // Screen wrapping
        if (this.x < 0 - this.radius) {
            this.x = this.canvas.width + this.radius;
        } else if (this.x > this.canvas.width + this.radius) {
            this.x = 0 - this.radius;
        }
        
        if (this.y < 0 - this.radius) {
            this.y = this.canvas.height + this.radius;
        } else if (this.y > this.canvas.height + this.radius) {
            this.y = 0 - this.radius;
        }
        
        // Handle blinking if invulnerable
        if (this.invulnerable) {
            if (Date.now() - this.lastBlinkTime > this.blinkTime) {
                this.visible = !this.visible;
                this.lastBlinkTime = Date.now();
            }
        }
    }
    
    draw() {
        if (!this.visible) return;
        
        this.ctx.strokeStyle = 'white';
        this.ctx.lineWidth = 2;
        this.ctx.beginPath();
        
        // Nose of the ship
        const noseX = this.x + this.radius * Math.cos(this.angle);
        const noseY = this.y - this.radius * Math.sin(this.angle);
        
        // Rear left of the ship
        const rearLeftX = this.x - this.radius * (Math.cos(this.angle) + Math.sin(this.angle) * 0.5);
        const rearLeftY = this.y + this.radius * (Math.sin(this.angle) - Math.cos(this.angle) * 0.5);
        
        // Rear right of the ship
        const rearRightX = this.x - this.radius * (Math.cos(this.angle) - Math.sin(this.angle) * 0.5);
        const rearRightY = this.y + this.radius * (Math.sin(this.angle) + Math.cos(this.angle) * 0.5);
        
        // Draw the ship
        this.ctx.moveTo(noseX, noseY);
        this.ctx.lineTo(rearLeftX, rearLeftY);
        this.ctx.lineTo(rearRightX, rearRightY);
        this.ctx.closePath();
        this.ctx.stroke();
        
        // Draw thrust if applicable
        if (this.thrusting) {
            this.ctx.beginPath();
            this.ctx.moveTo(
                rearLeftX + (rearRightX - rearLeftX) * 0.5,
                rearLeftY + (rearRightY - rearLeftY) * 0.5
            );
            this.ctx.lineTo(
                rearLeftX - this.radius * 0.5 * Math.cos(this.angle),
                rearLeftY + this.radius * 0.5 * Math.sin(this.angle)
            );
            this.ctx.stroke();
        }
    }
} 