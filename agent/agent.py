import base64
import time
from typing import Callable, List, Dict, Any, Generator
from openai import OpenAI
from openai.types.responses import ResponseOutputItem

from computers.computer import Computer
from utils import check_blocklisted_url

class Agent:
    """
    An agent class that interacts with a computer using OpenAI's Response API.
    """

    def __init__(
        self,
        api_key=None,
        model="computer-use-preview",
        computer:Computer=None,
        print_steps=True,
        debug=False,
        show_images=False,
        acknowledge_safety_check_callback: Callable = lambda message: True,
    ):
        """
        Initialize the agent.
        
        Args:
            api_key: OpenAI API key (if None, will use from environment)
            model: The OpenAI model to use
            computer: An instance that implements the Computer protocol
            print_steps: Whether to print steps to the console
            debug: Whether to print debug information
            show_images: Whether to display images
            acknowledge_safety_check_callback: Callback for safety checks
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.computer = computer
        self.print_steps = print_steps
        self.debug = debug
        self.show_images = show_images
        self.acknowledge_safety_check_callback = acknowledge_safety_check_callback
        self.last_response_id = None
        
        # Define tools for computer interaction - simple tool definition for Computer Use
        self.tools = [
            {
                "type": "computer-preview",
                "display_width": computer.dimensions[0] if computer else 1280,
                "display_height": computer.dimensions[1] if computer else 720,
                "environment": computer.environment if computer else "linux",
            }
        ]

    def handle_item(self, computer_call: ResponseOutputItem):
        """
        Handle a computer call from the model.
        
        Args:
            computer_call: The computer call object from the model response
            
        Returns:
            The call_id and a dictionary with the results for the next API call
        """
        call_id = computer_call.call_id
        action = computer_call.action
        action_type = action.type
        
        if self.debug:
            print(f"Handling computer call: {action_type}")
            print(f"Computer call structure: {dir(computer_call)}")
            print(f"Action structure: {dir(action)}")
        
        # Extract action parameters based on the action type
        try:
            if action_type == "click":
                # Try various parameter structures
                try:
                    # Try direct params access
                    if hasattr(action, "x") and hasattr(action, "y"):
                        x = action.x
                        y = action.y
                        button = getattr(action, "button", "left")
                    else:
                        raise ValueError("Could not extract coordinates for click action")
                    
                    params = {"x": x, "y": y, "button": button}
                except Exception as e:
                    if self.debug:
                        print(f"Error extracting click parameters: {e}")
                    raise e
                
            elif action_type == "type":
                # Try different parameter structures for 'type' action
                if hasattr(action, "text"):
                    text = action.text
                else:
                    raise ValueError("Could not extract text for type action")
                
                params = {"text": text}
                
            elif action_type == "keypress":
                # Get keys from various locations
                if hasattr(action, "keys"):
                    keys = action.keys
                else:
                    raise ValueError("Could not extract keys for keypress action")
                
                # Ensure keys is a list
                if not isinstance(keys, list):
                    keys = [keys]
                
                params = {"keys": keys}
                
            elif action_type == "scroll":
                # Try various parameter structures
                try:
                    if hasattr(action, "scroll_x") and hasattr(action, "scroll_y"):
                        x = action.x
                        y = action.y
                    else:
                        raise ValueError("Could not extract scroll parameters")
                    params = {"x": x, "y": y, "scroll_x": action.scroll_x, "scroll_y": action.scroll_y}                  
                    
                except Exception as e:
                    if self.debug:
                        print(f"Error extracting scroll parameters: {e}")
                    raise e
                
            elif action_type == "double_click":
                # Try various parameter structures
                try:
                    if hasattr(action, "x") and hasattr(action, "y"):
                        x = action.x
                        y = action.y
                    else:
                        raise ValueError("Could not extract coordinates for double_click action")
                    
                    params = {"x": x, "y": y}
                except Exception as e:
                    if self.debug:
                        print(f"Error extracting double_click parameters: {e}")
                    raise e
                
            elif action_type == "drag":
                # Try various parameter structures
                try:
                    path_data = None
                    if hasattr(action, "path"):
                        path_data = action.path
                    
                    if not path_data:
                        raise ValueError("Could not extract path for drag action")
                    
                    path = []
                    for point in path_data:
                        path.append({"x": point.x, "y": point.y})
                    
                    params = {"path": path}
                except Exception as e:
                    if self.debug:
                        print(f"Error extracting drag parameters: {e}")
                    raise e
                    
            elif action_type == "wait":
                # Extract the wait time (ms) parameter
                try:
                    # Try different parameter structures
                    if hasattr(action, "params") and hasattr(action.params, "ms"):
                        ms = action.params.ms
                    elif hasattr(action, "ms"):
                        ms = action.ms
                    elif hasattr(action, "params") and hasattr(action.params, "time"):
                        ms = action.params.time
                    elif hasattr(action, "time"):
                        ms = action.time
                    else:
                        # Default to 1000ms (1 second) if not specified
                        ms = 1000
                        
                    params = {"ms": ms}
                except Exception as e:
                    if self.debug:
                        print(f"Error extracting wait parameters: {e}")
                    # Default to 1000ms (1 second) if there's an error
                    params = {"ms": 1000}
            
            elif action_type == "screenshot":
                # No parameters needed for screenshot action
                params = {}
                
            else:
                if self.debug:
                    print(f"Unknown action type: {action_type}")
                raise ValueError(f"Unknown action type: {action_type}")
            
        except Exception as e:
            if self.debug:
                print(f"Error determining action parameters: {e}")
                import traceback
                traceback.print_exc()
            raise e
        
        if self.print_steps:
            print(f"Action: {action_type}")
            print(f"Parameters: {params}")
        
        try:
            # Execute the action using the computer method
            method = getattr(self.computer, action_type)
            method(**params)
            
            # Wait for action to take effect (except for wait action, which already waits)
            if action_type != "wait":
                time.sleep(0.5)
            
            # Get a screenshot after the action
            screenshot_base64 = self.computer.screenshot()
            
            # Handle safety checks if present
            pending_checks = getattr(computer_call, "pending_safety_checks", [])
            for check in pending_checks:
                message = getattr(check, "message", "Safety check with no message")
                if not self.acknowledge_safety_check_callback(message):
                    raise ValueError(
                        f"Safety check failed: {message}. Cannot continue with unacknowledged safety checks."
                    )
            
            # Return the call_id and the screenshot for the next API call
            # return value informs model of the latest screenshot
            call_output = {
                "type": "computer_call_output",
                "call_id": computer_call.call_id,
                "acknowledged_safety_checks": pending_checks,
                "output": {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{screenshot_base64}",
                },
            }

            # additional URL safety checks for browser environments
            if self.computer.environment == "browser":
                current_url = self.computer.get_current_url()
                call_output["output"]["current_url"] = current_url
                check_blocklisted_url(current_url)

            return [call_output], {"action": action_type, "params": params}
            
        except Exception as e:
            if self.debug:
                print(f"Error executing {action_type}: {e}")
                import traceback
                traceback.print_exc()
            raise e
        

    def run_conversation(self, user_input: str, should_stop_callback=None) -> Generator[Dict[str, Any], None, None]:
        """
        Run a conversation with the model.
        
        Args:
            user_input: The user input to send to the model.
            should_stop_callback: An optional callback that returns True if the conversation should stop.
            
        Returns:
            A generator that yields updates as they are received.
        """
        items = []
        items.append({"role": "user", "content": user_input})
        continue_conversation = True

        while continue_conversation:            

            try:
                response = self.client.responses.create(
                    model=self.model,
                    previous_response_id=self.last_response_id if self.last_response_id else None,
                    tools=self.tools,
                    input=items,
                    reasoning={"generate_summary": "concise"},
                    truncation="auto"
                )
                self.last_response_id = response.id

                if not response.output:
                    print(response)
                    raise ValueError("No output from model")

                continue_conversation = False  # Assume no further actions until proven otherwise.
                for item in response.output:                    
                    if hasattr(item, 'role') and item.role == "assistant":
                        yield {"role": item.role, "content": item.content[0].text}
                    elif item.type == "reasoning":
                        reasoning_text = ""
                        if hasattr(item, "summary"):
                            reasoning_text = '\n'.join([x.text for x in item.summary])
                        yield {"role": "reasoning", "content": reasoning_text}
                    elif item.type == "computer_call":
                        result_items, action_obj = self.handle_item(item)
                        items.extend(result_items)
                        continue_conversation = True
                        yield action_obj

                # Flush any pending items before the next iteration.
                # Check if we should stop via the callback before making an API call.
                if should_stop_callback and should_stop_callback():
                    items.append({"role": "user", "content": "Operation stopped by user. No further actions required until user input."})
                    try:
                        flush_response = self.client.responses.create(
                            model=self.model,
                            previous_response_id=self.last_response_id,
                            tools=self.tools,
                            input=items,
                            reasoning={"generate_summary": "concise"},
                            truncation="auto"
                        )
                        self.last_response_id = flush_response.id
                        items = []  # Clear pending items.
                    except Exception as e:
                        print(f"Error flushing pending items: {e}")
                    yield {"role": "assistant", "content": "Conversation stopped by user."}
                    continue_conversation = False

            except Exception as e:
                error_message = f"Error during conversation: {str(e)}"
                print(error_message)
                yield {"role": "assistant", "content": f"An error occurred: {error_message}"}
                break

