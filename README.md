# Computer User Agent

A Python-based agent that uses OpenAI's models to control a virtual desktop environment running in Docker. This project allows AI to interact with GUI applications through a VNC-connected virtual machine.

## Overview

This project creates a containerized Linux desktop environment that can be controlled programmatically by an AI agent. The agent interprets natural language instructions and executes them as mouse movements, clicks, key presses, and other actions on the virtual desktop.

Key features:
- Dockerized Linux desktop environment with XFCE
- VNC and noVNC for remote access and visualization
- Integration with OpenAI's Computer Use model
- Web-based interface using Gradio
- Real-time visualization of the agent's actions

## System Requirements

- Docker and Docker Compose
- Python 3.8 or higher
- OpenAI API key with access to the `computer-use-preview` model

## Project Structure

```
COMPUTER_USE/
├── agent/                    # Agent module
│   └── agent.py              # Agent class implementation
├── computers/                # Computer implementations
│   ├── __init__.py
│   ├── computer.py           # Computer protocol definition
│   └── docker_computer.py    # Docker-based computer implementation
├── docker-compose.yml        # Docker Compose configuration
├── Dockerfile                # Docker image definition
├── gradio_app.py             # Gradio web interface
├── requirements.txt          # Python dependencies
├── stream.sh                 # Container startup script
└── utils.py                  # Utility functions
```

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd COMPUTER_USE
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your OpenAI API key as an environment variable:
   ```bash
   export OPENAI_API_KEY="your-api-key"
   ```

## Usage

### Start the Web Interface

1. Launch the Gradio app:
   ```bash
   python gradio_app.py
   ```

2. Open your browser and navigate to the URL shown in the terminal (typically http://localhost:7860).

3. In the web interface:
   - Configure the Docker container settings (container name, display, VNC port)
   - Click "Connect to VM" to start the virtual desktop
   - Once connected, you'll see the Linux desktop in the iframe
   - Use the chat interface to instruct the agent

### Initializing the System Programmatically

Here's a complete example of how to initialize both the DockerComputer and Agent:

```python
def init_docker_computer(container_name, display, vnc_port, api_key_input, shutdown_on_exit=False):
    """Initialize the Docker Computer and Agent"""
    try:
        # Initialize Docker Computer
        docker_computer = DockerComputer(
            container_name=container_name,
            display=display,
            vnc_port=vnc_port,
            shutdown_on_exit=shutdown_on_exit
        )
        
        # Test connection
        with docker_computer as computer:
            dimensions = computer.dimensions
            
            # Initialize Agent, passing the api_key
            agent = Agent(
                api_key=api_key_input,
                computer=computer,
                print_steps=True,
                debug=False,
                acknowledge_safety_check_callback=lambda message: True  # Simple safety check callback
            )
            
            return docker_computer, agent, f"Connected to Docker container with dimensions: {dimensions[0]}x{dimensions[1]}"
    except Exception as e:
        error_message = f"Failed to connect to Docker container: {str(e)}"
        return None, None, error_message

# Usage example
docker_computer, agent, status = init_docker_computer(
    container_name="vnc-desktop",
    display=":99",
    vnc_port=5900,
    api_key_input="your-openai-api-key"
)

if agent:
    # Use the agent with the connected computer
    with docker_computer as computer:
        for update in agent.run_conversation("Open Firefox and go to openai.com"):
            print(update)
```

### Example Commands

You can provide natural language instructions like:

- "Open Firefox and navigate to openai.com"
- "Create a new text file on the desktop and write 'Hello World' in it"
- "Open the terminal and check the system information"

## Key Components

### Agent Class

The `Agent` class is responsible for:
- Communicating with the OpenAI API
- Converting model outputs into computer actions
- Handling safety checks and validations
- Managing the conversation flow

```python
# Create an agent
agent = Agent(
    api_key="your-openai-api-key",
    computer=computer_instance,
    print_steps=True
)

# Run a conversation with the agent
for update in agent.run_conversation("Open Firefox"):
    print(update)
```

### Computer Protocol

The `Computer` protocol defines the interface for different computer implementations:

```python
class Computer(Protocol):
    @property
    def environment(self) -> Literal["windows", "mac", "linux", "browser"]: ...
    @property
    def dimensions(self) -> tuple[int, int]: ...

    def screenshot(self) -> str: ...
    def click(self, x: int, y: int, button: str = "left") -> None: ...
    def double_click(self, x: int, y: int) -> None: ...
    def scroll(self, x: int, y: int, scroll_x: int, scroll_y: int) -> None: ...
    def type(self, text: str) -> None: ...
    def wait(self, ms: int = 1000) -> None: ...
    def move(self, x: int, y: int) -> None: ...
    def keypress(self, keys: List[str]) -> None: ...
    def drag(self, path: List[Dict[str, int]]) -> None: ...
    def get_current_url() -> str: ...
```

### DockerComputer Implementation

The `DockerComputer` class implements the Computer protocol using a Docker container. It's designed to be used with Python's context manager (`with` statement) to properly handle container lifecycle:

```python
# Create a Docker computer
with DockerComputer(
    container_name="vnc-desktop",  # Name of the Docker container
    display=":99",                 # X11 display number
    vnc_port=5900,                 # Port for VNC server (optional)
    novnc_port=6080,               # Port for noVNC web interface (optional)
    shutdown_on_exit=False         # Whether to stop container when exiting the context
) as computer:
    # Get screen dimensions
    dimensions = computer.dimensions
    
    # Take a screenshot
    screenshot = computer.screenshot()
    
    # Click at a specific position
    computer.click(x=100, y=200)
    
    # Type text
    computer.type("Hello World")
```

#### Context Manager Functionality

When using the `with` statement:

1. The `__enter__` method:
   - Starts the Docker container if it's not already running
   - Checks if the container is healthy
   - Fetches the display geometry
   - Returns the computer instance for use within the context block

2. The `__exit__` method:
   - Stops the container if `shutdown_on_exit=True` and the container was started by this instance
   - Performs cleanup operations

#### Port Configuration

- **VNC Port**: If not specified, an available port will be automatically found (starting from 5900)
- **noVNC Port**: If not specified, an available port will be automatically found (starting from 6080)
- These ports are mapped from the host to the container in the docker-compose.yml file

#### Accessing the VNC Display

You can get the noVNC URL to access the desktop in a browser:
```python
vnc_url = computer.get_vnc_url()
print(f"Access the desktop at: {vnc_url}")
```

### Gradio Web Interface

The web interface provides:
- Connection settings for the Docker container
- Real-time visualization of the virtual desktop
- Chat interface for issuing commands to the agent
- Controls to stop operations and reset the chat

## Docker Configuration

The Docker container includes:
- Ubuntu 22.04 with XFCE desktop
- VNC server for remote access
- noVNC for web-based access
- Firefox ESR browser
- X11 utilities and xdotool for GUI automation

## Troubleshooting

### Docker Container Issues
- **Container not starting**: Check Docker logs with `docker logs vnc-desktop`
- **VNC connection failures**: Verify the port mappings in docker-compose.yml
- **Display not visible**: Ensure Xvfb and XFCE are running properly

### Agent Issues
- **API key errors**: Verify your OpenAI API key is valid and has access to the required model
- **Action failures**: Check that the Docker container is healthy and VNC is accessible
- **Slow responses**: The model may take time to process complex instructions

## Extending the Project

### Adding New Computer Implementations

To add a different computer implementation:
1. Create a new class that implements the Computer protocol
2. Implement all required methods (screenshot, click, type, etc.)
3. Set the environment and dimensions properties

### Customizing the Docker Environment

To customize the Docker environment:
1. Modify the Dockerfile to add new packages or tools
2. Update stream.sh if you need to change startup behavior
3. Rebuild the container with `docker-compose build`