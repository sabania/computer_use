import gradio as gr
import sys
import os
from pathlib import Path
import json

# Ensure the current directory is in the path
current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

# Import our custom modules
from computers.docker_computer import DockerComputer
from agent.agent import Agent

# Create global variables for the Docker Computer and Agent
docker_computer = None
agent = None
debug_mode = False
processing = False
stop_requested = False

def safety_check_callback(message):
    """Handle safety check prompts from the agent"""
    print(f"Safety Check: {message}")
    return True

def should_stop():
    """Callback to check if the conversation should stop"""
    global stop_requested
    return stop_requested

def init_docker_computer(container_name, display, vnc_port, api_key_input, shutdown_on_exit = False):
    """Initialize the Docker Computer and Agent"""
    global docker_computer, agent, debug_mode
    
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
            
            # Initialize Agent, passing the api_key (if not found in environment)
            agent = Agent(
                api_key=api_key_input,
                computer=computer,
                print_steps=True,
                debug=debug_mode,
                acknowledge_safety_check_callback=safety_check_callback
            )
            
            return f"Connected to Docker container with dimensions: {dimensions[0]}x{dimensions[1]}"
    except Exception as e:
        error_message = f"Failed to connect to Docker container: {str(e)}"
        if debug_mode:
            error_message += f"\n\nStack trace: {e.__traceback__}"
        return error_message

def chat_with_agent(message, history):
    """Process a message with the agent and return updates in the format Gradio expects"""
    global docker_computer, agent, processing, stop_requested
    
    # Basic checks
    if not docker_computer or not agent:
        return "Please connect to Docker first."
    
    if processing:
        return "Already processing a message. Please wait."
    
    # Reset stop flag at the start of a new conversation
    stop_requested = False
    
    # Start processing
    processing = True
    
    try:
        with docker_computer as computer:
            all_content = ""
            
            # Modify run_conversation to use the should_stop callback
            for update in agent.run_conversation(message, should_stop_callback=should_stop):                
                print(f"Update received: {update}")  # Debug print
                
                if "role" in update and update["role"] == "assistant":
                    # Add assistant's message
                    all_content += f"\n\n{update.get('content', '')}"
                    yield all_content.strip()
                
                elif "role" in update and update["role"] == "reasoning":
                    # Add reasoning
                    reasoning = update.get("content", "")
                    all_content += f"\n\n**🧠 Agent Reasoning:**\n{reasoning}"
                    yield all_content.strip()
                
                elif "action" in update:
                    # Add action
                    action = update["action"]
                    params = update.get("params", {})
                    all_content += f"\n\n**🔄 Action: {action}**\n```\n{json.dumps(params, indent=2)}\n```"
                    yield all_content.strip()                
                
            # Ensure at least one yield happens
            if not all_content:
                yield "No response received from the agent."
    
    except Exception as e:
        error_message = f"Error: {str(e)}"
        if debug_mode and hasattr(e, '__traceback__'):
            import traceback
            tb_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            error_message += f"\n\nStack Trace:\n{tb_str}"
        
        yield error_message
    
    finally:
        processing = False
        stop_requested = False  # Reset the stop flag

def stop_conversation():
    """Request to stop the current conversation"""
    global stop_requested, processing
    
    if processing:
        stop_requested = True
        return "Stopping the current operation..."
    else:
        return "No active operation to stop."

def reset_chat_history():
    """Reset the chat history and agent's state"""
    global agent, stop_requested
    
    # Reset the stop flag
    stop_requested = False
    
    # Reset the agent's conversation state if agent exists
    if agent:
        agent.last_response_id = None
        print("Reset agent's last_response_id to None")
    
    # Return empty list to reset chat history
    return []

def toggle_debug_mode(value):
    """Toggle debug mode"""
    global debug_mode
    debug_mode = value
    return value

def get_vnc_html(port):
    """Generate HTML for the VNC iframe"""
    vnc_url = f"http://localhost:{port}/vnc.html?autoconnect=true&password=secret&resize=scale"
    return f"""
    <div style="border: 1px solid #d9d9d9; border-radius: 0.5rem; overflow: hidden; background-color: white; width: 100%; height: 80vh;">
        <iframe src="{vnc_url}" style="width: 100%; height: 100%; border: none;"></iframe>
    </div>
    """

# Custom CSS for better layout
css = """
.fixed-height-container {
    height: 80vh !important;
}

/* Make sure the chatbot interface takes the full height */
.fixed-height-container > div {
    height: 100% !important;
}

/* Ensure the message list is scrollable */
.fixed-height-container .message-list {
    max-height: calc(100% - 120px) !important;
    overflow-y: auto !important;
}

/* Style for the stop button to make it more visible */
.stop-btn {
    background-color: #ff5252 !important;
    color: white !important;
}
"""

# Get the Gradio version
try:
    gradio_version = gr.__version__
    print(f"Gradio version: {gradio_version}")
except:
    gradio_version = "unknown"
    print("Could not determine Gradio version")

# Get the API key from environment, if available.
api_key_env = os.environ.get("OPENAI_API_KEY", "")

# First try with Blocks and newer components
with gr.Blocks(title="Computer User Agent", css=css) as demo:
    
    with gr.Sidebar():
        gr.Markdown("## Settings")
        
        # Check for OpenAI API key
        api_status = gr.Markdown(
            "✅ OpenAI API Key found in environment variables" if api_key_env 
            else "⚠️ No OpenAI API Key found in environment."
        )
        # Provide an input for the API key regardless; if found in env, it will be prefilled.
        api_key_input = gr.Textbox(label="OpenAI API Key", visible=not api_key_env, value=api_key_env, placeholder="Enter your OpenAI API Key")
        container_name = gr.Textbox(label="Container Name", value="vnc-desktop")
        display = gr.Textbox(label="Display", value=":99")
        vnc_port = gr.Textbox(label="VNC Port", value="6080")
        
        with gr.Row():
            connect_btn = gr.Button("Connect to VM")
            reset_btn = gr.Button("Reset Chat")
        
        stop_btn = gr.Button("Stop Operation", elem_classes="stop-btn")
        stop_status = gr.Markdown()
        
        connection_status = gr.Markdown()
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("## Streaming VM Display")
            vnc_html = gr.HTML("Please connect to VM first.")
        with gr.Column(scale=1, elem_classes="fixed-height-container"):
            chat_interface = gr.ChatInterface(
                fn=chat_with_agent,
                title="Computer User Agent",
                type="messages"
            )
    
    # Connect event handlers for Docker: now include API key input.
    connect_btn.click(
        init_docker_computer,
        inputs=[container_name, display, vnc_port, api_key_input],
        outputs=[connection_status]
    ).then(
        lambda port: get_vnc_html(port),
        inputs=[vnc_port],
        outputs=[vnc_html]
    )
    
    reset_btn.click(
        reset_chat_history,
        None,
        chat_interface.chatbot_value
    )
    
    stop_btn.click(
        stop_conversation,
        None,
        stop_status
    )

if __name__ == "__main__":
    print(f"Starting Gradio app (version: {gradio_version})")
    demo.launch()
