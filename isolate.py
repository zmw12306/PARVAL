from query_repo_recursive import *
from typing_extensions import Annotated
from autogen import ConversableAgent
import autogen
import global_vars
import argparse

# TODO: add the LLM config list
config_list = []


def create_file_with_code(
    filename: Annotated[str, "Name of file to create."], code: Annotated[str, "Code to write in the file."]
):
    with open(filename, "w") as file:
        file.write(code)
        print(entry_file)

    with open(entry_file, 'a') as file:   
        file.write('\n' + code)

    # TODO: modify the main function to call the new parser function, add build logic and run
    return 0, "Build successfully"    

def get_task_prompt(function):
        
    task_prompt = f"Given the function definitions for a protocol, which might mix input buffer parsing code with processing code, refactor the code to introduce a new parser function that validates the input structure. The parser function should only take the input buffer and input buffer len as two parameters, and return True or False. Please remove the checking not directly on input buffer or input buffer length, to make the generated function syntax-correct. Don't includes basic length validation for minimum packet size if the check does not exist in the original code\n \
               \n- Iteratively call 'query_function' to retrieve function definition to find parsing logic in deeper function call. \n \
               \n- Please output complete function content for each newly added or modified function. Don't omit unchanged lines for brevity. *** Don't add basic length validation if it does not exist in the original code, even if there is a bug ***\n \
               \n- ****Important!!!***When the input field is checked together with doing further processing, e.g., if(check1) process; else if(check2) process2; else {{Status = error_code; goto exit;}}. The new parsing function should contain: if !((check1 || check2)) {{Status = error_code}}. And in the original code: if(check1) process; else if(check2) process2; \n \
               \nThe entry function is:\n```c \n {function} \n```  \
                "
    return task_prompt

# Let's first define the assistant agent that suggests tool calls.
def get_developer_prompt():
    with open("example.txt", "r") as f:
        example = f.read()

    prompt = f"""Code Refactor Expert Developer. Given a new entry function and its dependency functions, your task is to refactor the code and call the provided function: 'handle_refactor'. Steps to Follow:\    
       
        1. Iteratively call 'query_function' to fetch all necessary dependent functions. Query iteratively until no further dependent functions are required for validation.
        
        2. Extract Input Buffer Extraction and Validation:\
        - Identify and extract the code that validates the input buffer.
        - Trace the data flow of the input buffer: locate variables that are assigned values from parts of the input buffer (e.g., x = buf[3]), and include these assignments and validations in the parsing function (e.g., if (x > 3) return false;).
        - ****Important!!!***If the input field is checked together with further processing, e.g., if (check1) process; else if (check2) process2; else {{abort;}}, the new parsing function should handle this logic. For example, if !((check1 || check2)) {{return False}}.\
        - Write down the analyze process.

        3. Create Isolated Parsing Functions:\
        Create a new parse function containing all validations on the input buffer and input buffer length from Step 2.\
        The new function should **only have two input parameters**: input buffer and input buffer length, and return true/false.\
        The other functions called by the new function should also be refactored to only contain parsing logic. *** Don't add basic length validation if it does not exist in the original code, even if there is a bug ***\
        Donot redefine any struct or macro types.\
        Ensure all validation logic is included without any processing logic.\
 
        \n \n ############# \n \
    Here is an example for this task:\n {example}. \

    You can iteratively call 'query_function' for multiple times when you consider a function containing input validation checking and need function definition.
    Return 'TERMINATE' when finished querying all parsing related function and develop the isolated code.
"""
    return prompt


def get_critic_prompt():
    critic_prompt = f"Generate critique and recommendations on the isolated parsing function. The Developer agent often misses input validation logics. If the result is already correct, finally call create_file_with_code to write isolated parsing functions and type 'TERMINATE' to complete the task. If not, please provide detailed suggestions for developer agent to improve."
    return critic_prompt


initializer = ConversableAgent(
        name="Init",
        code_execution_config=False,
)

assistant = ConversableAgent(
    name="Developer",
    system_message = get_developer_prompt(),
    is_termination_msg=lambda msg: msg.get("content") is not None and "Build successfully" in msg["content"],
    llm_config={"config_list": config_list},
)

# The user proxy agent is used for interacting with the assistant agent
# and executes tool calls.
user_proxy = ConversableAgent(
    name="Executor",
    llm_config=False,
    human_input_mode="NEVER",
)

critic = ConversableAgent(
    name="Critic",
    system_message= get_critic_prompt(),
    llm_config={"config_list": config_list},
)

# Register the tool signature with the assistant agent.
assistant.register_for_llm(name="query_function", description="Query function definiton")(query_function)

# Register the tool function with the user proxy agent.
user_proxy.register_for_execution(name="query_function")(query_function)

# Register the tool signature with the assistant agent.
critic.register_for_llm(name="create_file_with_code", description="create a new file with code content")(create_file_with_code)

# Register the tool function with the user proxy agent.
user_proxy.register_for_execution(name="create_file_with_code")(create_file_with_code)
   
def state_transition(last_speaker, groupchat):
    messages = groupchat.messages
    if last_speaker is initializer:
        return assistant
    
    elif last_speaker is assistant:
        if 'tool_calls' in messages[-1]:
            return user_proxy
        else:
            return critic
    elif last_speaker is critic:
        if 'tool_calls' in messages[-1]:
            return user_proxy
       
        else:
            return assistant
        return user_proxy
    elif last_speaker is user_proxy:
            return assistant
      
    

groupchat = autogen.GroupChat(
    agents = [initializer, assistant, user_proxy, critic],
    messages=[],
    max_round=30,
    speaker_selection_method=state_transition
)

manager = autogen.GroupChatManager(groupchat=groupchat, llm_config={"config_list": config_list},)


# Create the argument parser
parser = argparse.ArgumentParser(description="Isolating parsing function.")

# Add arguments
parser.add_argument("--fun", type=str, required=True, help="Specify the entry parsing function name.")
parser.add_argument("--file_path", type=str, required=True, help="Specify the entry parsing function path.")
parser.add_argument("--proj_path", type=str, required=True, help="Specify the project path.")


# Parse the arguments
args = parser.parse_args()

global entry_function
entry_function = args.fun
global entry_file
entry_file = args.file_path

global_vars.project_path = args.proj_path
global_vars.project_data = init(global_vars.project_path)


function = query_function(entry_function)

init_msg = get_task_prompt(function)

chat_result = initializer.initiate_chat(manager, message = init_msg)
