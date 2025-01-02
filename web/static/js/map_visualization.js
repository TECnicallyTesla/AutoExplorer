class MapVisualization {
    constructor(canvasId, config) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.config = config;
        
        // Map dimensions from config
        this.width = config.width_cm;
        this.height = config.height_cm;
        this.resolution = config.resolution_cm;
        
        // Calculate grid dimensions
        this.gridWidth = Math.ceil(this.width / this.resolution);
        this.gridHeight = Math.ceil(this.height / this.resolution);
        
        // Colors for different cell types
        this.colors = {
            unknown: '#404040',
            free: '#28a745',
            occupied: '#dc3545',
            path: '#ffc107',
            robot: '#17a2b8'
        };
        
        // Robot properties
        this.robotRadius = config.robot_radius_cm;
        this.robotPosition = { x: 0, y: 0, orientation: 0 };
        
        // Path planning
        this.currentPath = [];
        
        // Initialize the canvas
        this._initCanvas();
        this._setupResizeHandler();
    }
    
    _initCanvas() {
        // Set canvas size to match container while maintaining aspect ratio
        const container = this.canvas.parentElement;
        const containerWidth = container.clientWidth;
        const containerHeight = container.clientHeight;
        
        // Calculate size to maintain aspect ratio
        const aspectRatio = this.width / this.height;
        let canvasWidth = containerWidth;
        let canvasHeight = containerWidth / aspectRatio;
        
        if (canvasHeight > containerHeight) {
            canvasHeight = containerHeight;
            canvasWidth = containerHeight * aspectRatio;
        }
        
        this.canvas.width = canvasWidth;
        this.canvas.height = canvasHeight;
        
        // Calculate scaling factors
        this.scaleX = canvasWidth / this.width;
        this.scaleY = canvasHeight / this.height;
    }
    
    _setupResizeHandler() {
        // Update canvas size when window is resized
        window.addEventListener('resize', () => {
            this._initCanvas();
            this.render();
        });
    }
    
    _worldToCanvas(x, y) {
        // Convert world coordinates to canvas coordinates
        return {
            x: x * this.scaleX,
            y: this.canvas.height - (y * this.scaleY)
        };
    }
    
    _drawGrid(occupancyGrid) {
        // Clear canvas
        this.ctx.fillStyle = '#1a1a1a';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Draw grid cells
        const cellWidth = this.canvas.width / this.gridWidth;
        const cellHeight = this.canvas.height / this.gridHeight;
        
        for (let y = 0; y < this.gridHeight; y++) {
            for (let x = 0; x < this.gridWidth; x++) {
                const value = occupancyGrid[y * this.gridWidth + x];
                
                // Determine cell color based on occupancy value
                let color;
                if (value < this.config.free_threshold) {
                    color = this.colors.free;
                } else if (value > this.config.occupied_threshold) {
                    color = this.colors.occupied;
                } else {
                    color = this.colors.unknown;
                }
                
                // Draw cell
                this.ctx.fillStyle = color;
                this.ctx.fillRect(
                    x * cellWidth,
                    y * cellHeight,
                    cellWidth,
                    cellHeight
                );
            }
        }
    }
    
    _drawPath() {
        if (!this.currentPath.length) return;
        
        // Draw planned path
        this.ctx.strokeStyle = this.colors.path;
        this.ctx.lineWidth = 2;
        this.ctx.beginPath();
        
        const start = this._worldToCanvas(
            this.currentPath[0][0],
            this.currentPath[0][1]
        );
        this.ctx.moveTo(start.x, start.y);
        
        for (let i = 1; i < this.currentPath.length; i++) {
            const point = this._worldToCanvas(
                this.currentPath[i][0],
                this.currentPath[i][1]
            );
            this.ctx.lineTo(point.x, point.y);
        }
        
        this.ctx.stroke();
    }
    
    _drawRobot() {
        const pos = this._worldToCanvas(
            this.robotPosition.x,
            this.robotPosition.y
        );
        
        // Draw robot body
        this.ctx.fillStyle = this.colors.robot;
        this.ctx.beginPath();
        this.ctx.arc(
            pos.x,
            pos.y,
            this.robotRadius * this.scaleX,
            0,
            2 * Math.PI
        );
        this.ctx.fill();
        
        // Draw orientation indicator
        this.ctx.strokeStyle = '#ffffff';
        this.ctx.lineWidth = 2;
        this.ctx.beginPath();
        this.ctx.moveTo(pos.x, pos.y);
        this.ctx.lineTo(
            pos.x + Math.cos(this.robotPosition.orientation) * this.robotRadius * this.scaleX,
            pos.y - Math.sin(this.robotPosition.orientation) * this.robotRadius * this.scaleY
        );
        this.ctx.stroke();
    }
    
    updateOccupancyGrid(grid) {
        this.occupancyGrid = grid;
        this.render();
    }
    
    updateRobotPosition(x, y, orientation) {
        this.robotPosition = { x, y, orientation };
        this.render();
    }
    
    updatePath(path) {
        this.currentPath = path;
        this.render();
    }
    
    render() {
        if (!this.occupancyGrid) return;
        
        this._drawGrid(this.occupancyGrid);
        this._drawPath();
        this._drawRobot();
    }
}

// Export for use in other files
window.MapVisualization = MapVisualization; 