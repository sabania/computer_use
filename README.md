# Computer User Agent - Installation and Usage Guide

This guide will help you set up and run the Computer User Agent that integrates with your Docker-based VNC environment.

## Prerequisites

1. **Docker**: Make sure Docker is installed and running
2. **Python 3.8+**: Required for running the Streamlit app
3. **OpenAI API Key**: With access to the Computer Use Preview API

## Project Structure

```
computer-user-agent/
│
├── app.py                     # Streamlit application
├── agent.py                   # Agent implementation 
├── utils.py                   # Utilities (your existing file)
│
├── computers/
│   ├── __init__.py            # Empty init file
│   ├── computer.py            # Computer protocol definition (your file)
│   └── docker_computer.py     # Docker Computer implementation
│
├── Dockerfile                 # Docker file for VNC container
├── start.sh                   # Startup script for Docker container
└── docker-compose.yml         # Docker Compose configuration
```

## Setup Instructions

1. **Create Project Directory Structure**

   ```bash
   mkdir -p computer-user-agent/computers
   touch computer-user-agent/computers/__init__.py
   ```

2. **Set OpenAI API Key**

   ```bash
   # For Linux/macOS
   export OPENAI_API_KEY=your_api_key_here
   
   # For Windows (PowerShell)
   $env:OPENAI_API_KEY="your_api_key_here"
   ```

3. **Install Required Packages**

   ```bash
   pip install streamlit pillow openai python-dotenv requests
   ```

4. **Build and Run Docker Container**

   ```bash
   docker-compose up -d
   ```

5. **Run the Streamlit App**

   ```bash
   streamlit run app.py
   ```

## Usage Guide

1. **First-time Setup**
   - Open the Streamlit app (usually at http://localhost:8501)
   - Click "Connect to Docker" in the sidebar
   - The app should detect your Docker container and display its dimensions

2. **Using the App**
   - The "Computer + Chat" tab combines the VNC display with computer control capabilities
   - Enter tasks for the AI to perform on the computer
   - Watch as the AI performs actions on the VNC display and explains what it's doing

3. **Example Commands to Try**
   - "Open a terminal and list files in the home directory"
   - "Open Firefox and search for information about Python"
   - "Create a new text file on the desktop with some sample content"
   - "Open the system settings and check the display resolution"

## Troubleshooting

- **Connection Issues**: Make sure the Docker container is running with `docker ps`
- **API Key Issues**: Check that your OPENAI_API_KEY environment variable is set properly
- **VNC Not Showing**: Verify ports 5900 and 6080 are exposed in your Docker container
- **Action Failures**: Check the debug output by enabling "Debug Mode" in the sidebar

## Advanced Configuration

The app provides several configuration options in the sidebar:

- **Debug Mode**: Enables detailed logging for troubleshooting
- **Show Screenshots in Chat**: Displays screenshots in the chat interface
- **Container Settings**: Change container name, display, and VNC port

## Security Notes

- The Computer User Agent uses OpenAI's safety mechanisms to prevent harmful actions
- URL blocking is implemented to prevent navigation to known harmful domains
- The agent will display safety warnings when performing potentially risky actions

## Additional Resources

- OpenAI Computer Use API Documentation: https://platform.openai.com/docs/guides/tools-computer-use
- VNC Documentation: https://github.com/novnc/noVNC