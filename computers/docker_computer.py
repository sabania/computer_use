import subprocess
import time
import base64
import os
import socket
from typing import List, Dict, Optional, Tuple, Literal

from computers.computer import Computer

class DockerComputer(Computer):
    environment = "linux"
    dimensions = (1280, 720)  # Default fallback; will be updated in __enter__.

    def __init__(
        self,
        container_name="vnc-desktop",
        display=":99",
        vnc_port=None,
        novnc_port=None,
        compose_file="docker-compose.yml",
        compose_project="computer-user-agent",
        shutdown_on_exit=False,
    ):
        """
        Initialize the DockerComputer.
        
        Args:
            container_name: Name of the Docker container
            display: X11 display number
            vnc_port: VNC port (if None, will find available port)
            novnc_port: noVNC web port (if None, will find available port)
            compose_file: Path to docker-compose.yml file
            compose_project: Docker compose project name
            shutdown_on_exit: Whether to shutdown the container on exit (default: False)
        """
        self.container_name = container_name
        self.display = display
        self.vnc_port = vnc_port or self._find_available_port(5900)
        self.novnc_port = novnc_port or self._find_available_port(6080)
        self.compose_file = compose_file
        self.compose_project = compose_project
        self.shutdown_on_exit = shutdown_on_exit
        self._current_url = None  # For browser integration if needed
        self.container_started_by_us = False  # Track if we started the container

    def _find_available_port(self, preferred_port):
        """Find an available port, starting with the preferred port."""
        port = preferred_port
        max_attempts = 10
        
        for _ in range(max_attempts):
            try:
                # Check if the port is in use
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                
                # If port is available (connection failed)
                if result != 0:
                    return port
                
                # Port is in use, try the next one
                port += 1
            except:
                # If we hit an error, move to the next port
                port += 1
        
        # If we couldn't find an available port, return the last one we tried
        return port

    def _start_container(self):
        """Start the Docker container using docker-compose with environment variables."""
        try:
            # Check if the container is already running
            result = subprocess.run(
                ["docker", "ps", "-q", "-f", f"name={self.container_name}"],
                capture_output=True,
                text=True,
            )
            
            if result.stdout.strip():
                print(f"Container {self.container_name} is already running")
                return
            
            # Prepare environment variables for docker-compose
            env = os.environ.copy()
            env.update({
                "VNC_PORT": str(self.vnc_port),
                "NOVNC_PORT": str(self.novnc_port),
                "DISPLAY_NUM": self.display.replace(":", "")
            })
            
            # Start the container using docker-compose with environment variables
            print(f"Starting container {self.container_name} with VNC port {self.vnc_port} and noVNC port {self.novnc_port}")
            subprocess.run(
                [
                    "docker-compose", 
                    "-f", self.compose_file, 
                    "-p", self.compose_project,
                    "up", "-d", "--build"
                ],
                env=env,
                check=True
            )
            
            # Wait for container to be ready
            max_attempts = 10
            for attempt in range(max_attempts):
                time.sleep(2)  # Wait for container to start
                try:
                    health_check = subprocess.run(
                        ["docker", "inspect", "--format", "{{.State.Health.Status}}", self.container_name],
                        capture_output=True,
                        text=True,
                    )
                    status = health_check.stdout.strip()
                    
                    if status == "healthy" or attempt == max_attempts - 1:
                        break
                    
                    print(f"Waiting for container to be ready... (attempt {attempt+1}/{max_attempts})")
                except:
                    # Container might not be created yet
                    print(f"Waiting for container to start... (attempt {attempt+1}/{max_attempts})")
            
            self.container_started_by_us = True
            print(f"Container {self.container_name} started successfully")
            
        except Exception as e:
            print(f"Error starting container: {e}")
            raise RuntimeError(f"Failed to start container: {e}")

    def _stop_container(self):
        """Stop the Docker container if we started it and shutdown_on_exit is True."""
        if self.container_started_by_us and self.shutdown_on_exit:
            try:
                print(f"Stopping container {self.container_name}")
                env = os.environ.copy()
                env.update({
                    "VNC_PORT": str(self.vnc_port),
                    "NOVNC_PORT": str(self.novnc_port),
                    "DISPLAY_NUM": self.display.replace(":", "")
                })
                
                subprocess.run(
                    [
                        "docker-compose",
                        "-f", self.compose_file,
                        "-p", self.compose_project,
                        "down"
                    ],
                    env=env,
                    check=True
                )
                print(f"Container {self.container_name} stopped")
            except Exception as e:
                print(f"Error stopping container: {e}")
        elif self.container_started_by_us and not self.shutdown_on_exit:
            print(f"Container {self.container_name} left running (shutdown_on_exit=False)")

    def __enter__(self):
        # Start the container if needed
        self._start_container()
        
        # Check if the container is running
        result = subprocess.run(
            ["docker", "ps", "-q", "-f", f"name={self.container_name}"],
            capture_output=True,
            text=True,
        )

        if not result.stdout.strip():
            raise RuntimeError(
                f"Container {self.container_name} is not running. "
                f"Check the logs using: docker logs {self.container_name}"
            )

        # Give the container a moment to fully initialize
        time.sleep(2)
        
        # Fetch display geometry
        geometry = self._exec(
            f"DISPLAY={self.display} xdotool getdisplaygeometry"
        ).strip()
        if geometry:
            w, h = geometry.split()
            self.dimensions = (int(w), int(h))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Stop the container if we started it and shutdown_on_exit is True
        self._stop_container()

    def _exec(self, cmd: str) -> str:
        """
        Run 'cmd' in the container.
        We wrap cmd in double quotes and escape any double quotes inside it,
        so spaces or quotes don't break the shell call.
        """
        # Escape any existing double quotes in cmd
        safe_cmd = cmd.replace('"', '\\"')

        # Then wrap the entire cmd in double quotes for `sh -c`
        docker_cmd = f'docker exec {self.container_name} sh -c "{safe_cmd}"'

        try:
            return subprocess.check_output(docker_cmd, shell=True).decode(
                "utf-8", errors="ignore"
            )
        except subprocess.CalledProcessError as e:
            print(f"Error executing command: {cmd}")
            print(f"Error output: {e.output.decode('utf-8', errors='ignore') if e.output else 'None'}")
            return ""

    def screenshot(self) -> str:
        """
        Takes a screenshot with ImageMagick (import), returning base64-encoded PNG.
        Requires 'import'.
        """
        cmd = (
            f"export DISPLAY={self.display} && "
            "import -window root png:- | base64 -w 0"
        )

        return self._exec(cmd)

    def get_screenshot_bytes(self) -> bytes:
        """
        Return the screenshot as bytes instead of base64 string
        """
        base64_str = self.screenshot()
        return base64.b64decode(base64_str)

    def click(self, x: int, y: int, button: str = "left") -> None:
        button_map = {"left": 1, "middle": 2, "right": 3}
        b = button_map.get(button, 1)
        self._exec(f"DISPLAY={self.display} xdotool mousemove {x} {y} click {b}")

    def double_click(self, x: int, y: int) -> None:
        self._exec(
            f"DISPLAY={self.display} xdotool mousemove {x} {y} click --repeat 2 1"
        )

    def scroll(self, x: int, y: int, scroll_x: int, scroll_y: int) -> None:
        """
        For simple vertical scrolling: xdotool click 4 (scroll up) or 5 (scroll down).
        """
        self._exec(f"DISPLAY={self.display} xdotool mousemove {x} {y}")
        clicks = abs(scroll_y)
        button = 4 if scroll_y < 0 else 5
        for _ in range(clicks):
            self._exec(f"DISPLAY={self.display} xdotool click {button}")

    def type(self, text: str) -> None:
        """
        Type the given text via xdotool, properly handling newlines.
        """
        # If text contains newlines, split and handle separately
        if '\n' in text:
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if i > 0:
                    # Press Return/Enter for newlines
                    self._exec(f"DISPLAY={self.display} xdotool key Return")
                    time.sleep(0.1)  # Small delay after Return
                
                if line:  # Only type if there's text in this line
                    # Escape single quotes in the line text
                    safe_text = line.replace("'", "'\\''")
                    # Type the line
                    cmd = f"DISPLAY={self.display} xdotool type -- '{safe_text}'"
                    self._exec(cmd)
                    time.sleep(0.1)  # Small delay after typing
        else:
            # Original approach for text without newlines
            safe_text = text.replace("'", "'\\''")
            cmd = f"DISPLAY={self.display} xdotool type -- '{safe_text}'"
            self._exec(cmd)

    def wait(self, ms: int = 1000) -> None:
        time.sleep(ms / 1000)

    def move(self, x: int, y: int) -> None:
        self._exec(f"DISPLAY={self.display} xdotool mousemove {x} {y}")

    def keypress(self, keys: List[str]) -> None:
        mapping = {
            "ENTER": "Return",
            "LEFT": "Left",
            "RIGHT": "Right",
            "UP": "Up",
            "DOWN": "Down",
            "ESC": "Escape",
            "SPACE": "space",
            "BACKSPACE": "BackSpace",
            "TAB": "Tab",
            "CTRL": "ctrl",
            "ALT": "alt",
            "SHIFT": "shift",
            "SUPER": "super",
            "META": "meta",
            "WIN": "super",
            "DELETE": "Delete",
            "HOME": "Home",
            "END": "End",
            "PAGEUP": "Page_Up",
            "PAGEDOWN": "Page_Down",
        }
        mapped_keys = [mapping.get(key, key) for key in keys]
        combo = "+".join(mapped_keys)
        self._exec(f"DISPLAY={self.display} xdotool key {combo}")

    def drag(self, path: List[Dict[str, int]]) -> None:
        if not path:
            return
        start_x = path[0]["x"]
        start_y = path[0]["y"]
        self._exec(
            f"DISPLAY={self.display} xdotool mousemove {start_x} {start_y} mousedown 1"
        )
        for point in path[1:]:
            self._exec(f"DISPLAY={self.display} xdotool mousemove {point['x']} {point['y']}")
        self._exec(f"DISPLAY={self.display} xdotool mouseup 1")
    
    def get_current_url(self) -> str:
        """
        Attempt to get the current URL from Firefox browser if running.
        This is a basic implementation and might need improvement.
        """
        try:
            # Try to get URL from Firefox using xdotool
            cmd = f"DISPLAY={self.display} xdotool search --onlyvisible --class Firefox getwindowname"
            window_name = self._exec(cmd).strip()
            
            # Firefox usually has the URL or page title in the window name
            if window_name and " - Mozilla Firefox" in window_name:
                title = window_name.replace(" - Mozilla Firefox", "")
                return title
            
            # Fallback to stored URL
            return self._current_url or "unknown"
        except Exception as e:
            print(f"Error getting current URL: {e}")
            return "unknown"

    def get_vnc_url(self) -> str:
        """
        Returns the URL for accessing the VNC display via browser
        """
        return f"http://localhost:{self.novnc_port}/vnc.html?autoconnect=true&password=secret&resize=local"