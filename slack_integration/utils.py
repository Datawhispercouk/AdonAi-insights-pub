from tabulate import tabulate
import plotly.graph_objs as go
import plotly.io as pio
import json
import os
from dotenv import load_dotenv
import requests
import time
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from slack_sdk import WebClient
import traceback

load_dotenv('.env')

slack_token = os.environ.get("SLACK_BOT_TOKEN")
slack_client = WebClient(slack_token)

channel_access_token = {}

def signin(username, password, channel_id):
    global channel_access_token
    payload = {
        "username": username,
        "password": password
    }
    api_url = os.environ.get("BASE_API") + "/user/login"
    response = requests.post(api_url, json=payload)
    print(response.json())
    if response.status_code == 200:
        response_data = response.json()
        access_token = response_data.get('access_token')
        channel_access_token[channel_id] = access_token

        info_response_data = get_user_info(channel_id)
        if info_response_data == "Unauthorized":
            return None
        elif info_response_data != None:
            vds_id = info_response_data["Division"]["DefaultVdsID"]
            username = info_response_data["UserName"]
            vds_name = info_response_data["Division"]["DefaultVds"]
            return [vds_id, username, vds_name]
        else:
            return "Couldn't get User Info"
    else:
        return "Invalid Username or password"
    
def get_user_info(channel_id):
    global channel_access_token
    access_token = channel_access_token[channel_id]
    info_api_url = os.environ.get("BASE_API") + "/user/user-info"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    info_response = requests.get(info_api_url, headers=headers)
    if info_response.status_code == 200:
        info_response_data = info_response.json()
        return info_response_data
    elif info_response.status_code == 401:
        return "Unauthorized"
    else:
        print(info_response.text)
        return None 

    
def getSessionID(vds, channel_id):
    global channel_access_token
    access_token = channel_access_token[channel_id]
    payload = {
        "vds_id": vds
    }
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    api_url = os.environ.get("BASE_API") + "/sessionservice/session"
    response = requests.post(api_url, json=payload, headers=headers)
    if response.status_code == 200:
        response_data = response.json()
        print(response_data.get('session_id'))
        return response_data.get('session_id')
    elif response.status_code == 401:
        return "Unauthorized"
    else:
        return "API call failed"

def structured_api_call(question, session_id, channel_id):
    global channel_access_token
    access_token = channel_access_token[channel_id]
    payload = {
        "question": question
    }
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    api_url = os.environ.get("BASE_API") + f'/chatservice/chatbot-structured/{session_id}'

    response = requests.post(api_url, json=payload, headers=headers)
    if response.status_code == 200:
        response_data = response.json()
        print("Response: ", response_data.get('result'))
        return (response_data.get('result'))
    elif response.status_code == 401:
        return "Unauthorized"
    else:
        print(response.text)
        return None  
   
def rag_api_call(question, session_id, channel_id):
    global channel_access_token
    access_token = channel_access_token[channel_id]
    payload = {
        "question": question
    }
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    api_url = os.environ.get("BASE_API") + f'/chatservice/chatbot-rag/{session_id}'

    response = requests.post(api_url, json=payload, headers=headers)
    if response.status_code == 200:
        response_data = response.json()
        return (response_data.get('result'))
    elif response.status_code == 401:
        return "Unauthorized"
    else:
        print("Failed")
        return None

def agent_api_call(payload, session_id, channel_id):
    
    global channel_access_token
    access_token = channel_access_token[channel_id]
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    print(payload)
    api_url = os.environ.get("BASE_API") + f'/chatservice/chatbot-agent-v2/{session_id}'
    
    response = requests.post(api_url, json=payload, headers=headers)
    if response.status_code == 200:
        response_data = response.json()
        return (response_data["result"])
    elif response.status_code == 401:
        return "Unauthorized"
    else:
        print("Failed")
        return None


def get_vds_list(channel_id):
    global channel_access_token
    access_token = channel_access_token[channel_id]
    try:
        print("API called")
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        api_url = os.environ.get("BASE_API") + f'/vdsservice/vds/list?page=1&size=30'

        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            response_data = response.json()
            print(response_data)
            return(response_data.get('results'))
        elif response.status_code == 401:
            print("Unauthorized")
            return "Unauthorized"
        else:
            print("Failed")
            return None
    except Exception as e:
        print(e)
        return None

def get_agent_list(channel_id):
    global channel_access_token
    access_token = channel_access_token[channel_id]
    try:
        print("API called")
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        api_url = os.environ.get("BASE_API") + f'/chatservice/list-channels'

        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            response_data = response.json()
            result_list = response_data.get('results')
            agents = []
            for result in result_list:
                result_obj = {
                    "channel_name": result["channel_name"],
                    "team_id": result["team_id"]
                }
                agents.append(result_obj)
            print(agents)
            return(agents)
        elif response.status_code == 401:
            print("Unauthorized")
            return "Unauthorized"
        else:
            print("Failed")
            return None
    except Exception as e:
        print(e)
        return None


def create_table_string(data_points_str: str):
    try:
        column_names = list(data_points_str.keys())
        col_data_list = []
        for col in column_names:
            data = list(data_points_str[col].values())
            col_data_list.append(data)
        table_data = list(zip(*col_data_list))
        table_string = "```" + tabulate(table_data, headers=column_names, tablefmt='fancy_grid') + "```"
        return table_string
    except Exception as e:
        print(f"Error creating table: {e}")
        return None

def create_graph(data, user_id):
    try:
        print("Figure Data")
        now_local = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{user_id}_{now_local}.jpg"
        figure_dict = json.loads(data)
        data = figure_dict['data']
        layout = figure_dict['layout']
        fig = go.Figure(data=data, layout=layout)
        print("figure created:")
        image_data = pio.to_image(fig, format='jpg', engine="orca", scale=1)
        print("image_data created")
        with open(f"./images/{filename}", 'wb') as f:
            f.write(image_data)
        return filename
    except Exception as e:
        print(f"Error creating graph: {e}")
        return None

def create_structured_response_block(response_string, user_id):
    response_block = []
    if response_string["metadata"]["figure"] != "":
        image_filename = create_graph(response_string["metadata"]["figure"], user_id)
        base_url = os.environ.get("BASE_FLASK_APP_URL")
        if image_filename:
            graph_section = {
                "type": "image",
                    "title": {
                        "type": "plain_text",
                        "text": "Graph:"
                    },
                    "image_url": f"{base_url}/share/{image_filename}",
                    "alt_text": "graph"
            }
            response_block.append(graph_section)

    if response_string["metadata"]["data_points"] != "" and response_string["metadata"]["data_points"] != {}:
        data_points_str = json.loads(response_string["metadata"]["data_points"])
        table_string = create_table_string(data_points_str)
        if table_string != None:
            table_section = {
                "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": table_string,
                    } 
            }
            response_block.append(table_section)
    
    if response_string["content"] != []:
        data_insight = response_string["content"]
        insight_string = ""
        for insight in data_insight:
            insight_string = insight_string + insight + "\n\n"
        insight_section = {
            "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "```" + insight_string + "```",
                } 
        }
        response_block.append(insight_section)
    
    return response_block

def append_to_json(data, value):
  try:
    with open("feedback_data.json") as f:  # Open in append mode
      existing_data = json.load(f)

    updated = False
    for object in existing_data:
        if object["user_id"] == data["user_id"] and object["channel_id"] == data["channel_id"] and object["ts"] == data["ts"]:
            object[value] = data[value]
            json_string = json.dumps(existing_data)
            print(json_string)
            with open("feedback_data.json", 'w') as json_file:
                json_file.write(json_string)
                updated = True
    print(updated)
    if not updated:
        existing_data.append(data)
        with open("feedback_data.json", 'w') as json_file:
            json.dump(existing_data, json_file, 
                            indent=4,  
                            separators=(',',': '))
    
    print(f"Feedback appended to 'feedback_data.json' successfully!")
  except OSError as e:
    print(f"Error opening file 'feedback_data.json': {e}")

def get_rating_block(ts, choice):
    if choice == "none":
        rating_block = [
            {
                    "type": "actions",
                    "block_id": f"{ts}",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "👍 Happy"
                            },
                            "value": "Thumbs Up",
                            "action_id": "thumbs_up"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "👎 Not Happy"
                            },
                            "value": "Thumbs Down",
                            "action_id": "thumbs_down"
                        }
                    ]
                }   
        ]
    elif choice == "thumbs_up":
        rating_block = [
            {
                    "type": "actions",
                    "block_id": f"{ts}",
                    "elements": [
                        {
                            "type": "button",
                            "style": "primary",
                            "text": {
                                "type": "plain_text",
                                "text": "👍 Happy"
                            },
                            "value": "Thumbs Up",
                            "action_id": "thumbs_up"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "👎 Not Happy"
                            },
                            "value": "Thumbs Down",
                            "action_id": "thumbs_down"
                        }
                    ]
                }   
        ]
    else:
        rating_block = [
            {
                    "type": "actions",
                    "block_id": f"{ts}",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "👍 Happy"
                            },
                            "value": "Thumbs Up",
                            "action_id": "thumbs_up"
                        },
                        {
                            "type": "button",
                            "style": "danger",
                            "text": {
                                "type": "plain_text",
                                "text": "👎 Not Happy"
                            },
                            "value": "Thumbs Down",
                            "action_id": "thumbs_down"
                        }
                    ]
                }   
        ]
        

    return rating_block

def send_query_block(input, channel_id, slack_client):
    query_block = [
        {
                "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": "Do you want to see the query used to get this response?",
                    } 
        },
        {
                    "type": "actions",
                    "block_id": "query_block",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Yes"
                            },
                            "value": input,
                            "action_id": "show_query"
                        }
                    ]
        }   
    ]
    slack_client.chat_postMessage(channel=channel_id, blocks=query_block)

def get_rag_response_text(response_string):
    response_text = response_string["content"]
    if response_string["metadata"]["references"] != []:
        response_text = response_text + "\n\n\nReferences:\n\n"
        # for reference in response_string["metadata"]["references"]:
        #     print(reference)
        #     link = reference["source"]
        #     page = reference["page"]
        #     response_text = response_text + f"<{link}> (page {page})" + "\n\n"
        response_text = response_text + "<https://www.example.com/Test Document.pdf> (page 1) \n\n"
    if response_string["metadata"]["safeguard"] != {}:
        if response_string["metadata"]["safeguard"]["input_validation"] != []  or response_string["metadata"]["safeguard"]["output_validation"] != []:
            response_text = response_text + "\n\nSafeguard Checks:\n\n"
            if response_string["metadata"]["safeguard"]["input_validation"] != []:
                response_text = response_text + "Input Validation:\n\n"
                for input_validation in response_string["metadata"]["safeguard"]["input_validation"]:
                    policy = input_validation["policy"]
                    if input_validation["validation_passed"] == True:
                        response_text = response_text + f"✔️ {policy}" + "\n"
                    else:
                        response_text = response_text + f"❌ {policy}" + "\n"
            if response_string["metadata"]["safeguard"]["output_validation"] != []:
                response_text = response_text + "\nOutput Validation:\n\n"
                for output_validation in response_string["metadata"]["safeguard"]["output_validation"]:
                    policy = output_validation["policy"]
                    if output_validation["validation_passed"] == True:
                        response_text = response_text + f"✔️ {policy}" + "\n"
                    else:
                        response_text = response_text + f"❌ {policy}" + "\n"
    return response_text

def get_agent_response_block(response_string):
    response_block = []
    if response_string["content"] != "":
        content_section = {
            "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": response_string["content"],
                } 
        }
        response_block.append(content_section)
        response_block.append(
                    {
                        "type": "divider"
                    }
                )
    if response_string["metadata"] != {}:
        for key in response_string["metadata"].keys():
            if key == "references" and response_string["metadata"]["references"] != []:
                response_text = "References:\n\n"
                for reference in response_string["metadata"]["references"]:
                    print(reference)
                    link = reference["source"]
                    page = reference["page"]
                    response_text = response_text + f"<{link}> (page {page})" + "\n\n"
                reference_section = {
                    "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": response_text,
                        } 
                }
                response_block.append(reference_section)
                response_block.append(
                    {
                        "type": "divider"
                    }
                )
            elif isinstance(response_string["metadata"][key], str):
                value = response_string["metadata"][key]
                changed_key = key.replace("_", " ").title()
                response_text = f"*{changed_key}*:" + "\n\n" + f"{value}" + "\n\n"
                key_section = {
                    "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": response_text,
                        } 
                }
                response_block.append(key_section)
                response_block.append(
                    {
                        "type": "divider"
                    }
                )

            elif isinstance(response_string["metadata"][key], bool):
                value = response_string["metadata"][key]
                changed_key = key.replace("_", " ").title()
                if value == True:
                    response_text = f"*{changed_key}*: ✔️ True" + "\n\n"
                else:
                    response_text = f"*{changed_key}*: ❌ False" + "\n\n"
                key_section = {
                    "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": response_text,
                        } 
                }
                response_block.append(key_section)
                response_block.append(
                    {
                        "type": "divider"
                    }
                )
        
    return response_block

def display_agent_response(question, team_id, session_id, channel_id, ts, verbose):
    try:
        is_completed = False
        block_count = 0
        current_charecter_count = 0
        current_block_text = ""

        payload = {
            "team_id": team_id,
            "question": question
        }

        response = agent_api_call(payload, session_id, channel_id)

        if response == "Unauthorized":
            update_message(channel_id, ts, "text", "Login token has expired. Please login again using `/start username password`")

        elif response is not None:
            if verbose:
                update_message(channel_id, ts, "text", "*Verbose:* \n")
                message_response = slack_client.chat_postMessage(channel=channel_id, text="Getting Verbose...")
                ts = message_response["ts"]
            
            while not is_completed:
                if verbose:
                    remaining_text = response["run_logs"][(block_count * 2000) + current_charecter_count:]
                    remaining_text = remaining_text.replace("```", "'")
                
                    print("\n\n\nResponse: \n" + str(response) + "\n")
                    print("\nRemaining Text Count: \n" + str(len(remaining_text)))
                    print("\nResponse Text Count: \n" + str(len(response["run_logs"])) + "\n\n\n")

                    while len(remaining_text) > 0:
                        print("\n\n\nCurrent Character Count: \n" + str(len(current_block_text)) + "\n\n\n")
                        if current_charecter_count < 2000:
                            if current_charecter_count + len(remaining_text) <= 2000:
                                current_block_text += remaining_text
                                remaining_text = ""
                            else: 
                                ending_index = 2000 - current_charecter_count
                                current_block_text += remaining_text[:ending_index]
                                print("\n\n\nEnding Index Count: \n" + str(ending_index) + "\n\n\n")
                                remaining_text = remaining_text[ending_index:]
                            current_charecter_count = len(current_block_text)
                            print("\n\n\nCurrent Character Count: \n" + str(len(current_block_text)) + "\n\n\n")
                            print("\n\n\nRemaining Character Count: \n" + str(len(remaining_text)) + "\n\n\n")
                            update_message(channel_id, ts, "block", get_verbose_block(current_block_text))
                            print("Updated Block")
                            
                        if current_charecter_count == 2000:
                            print("\n\n\nCurrent Character Count: \n" + str(current_charecter_count) + "\n\n\n")
                            if len(remaining_text) >= 2000:
                                current_block_text = remaining_text[:2000]
                                remaining_text = remaining_text[2000:]
                                message_response = slack_client.chat_postMessage(channel=channel_id, blocks=get_verbose_block(current_block_text))
                                ts = message_response["ts"]
                                current_charecter_count = 0
                                current_block_text = ""
                            else:
                                current_block_text = remaining_text
                                remaining_text = ""
                                message_response = slack_client.chat_postMessage(channel=channel_id, blocks=get_verbose_block(current_block_text))
                                ts = message_response["ts"]
                                current_charecter_count = len(current_block_text)
                            block_count += 1

                if response["content"] != "":
                    print("\n\nResponse Content: " + response["content"])
                    response_block = []
                    content_section = {
                        "type": "section",
                        "text": {
                            "type": "plain_text",
                            "text": "\n\n\nResponse ✅: \n\n" + response["content"],
                        }
                    }
                    response_block.append(content_section)
                    response_block.append({"type": "divider"})
                    
                    if response["metadata"]:
                        for key, value in response["metadata"].items():
                            if key == "references":
                                if len(value) != 0:
                                    response_text = "References:\n\n"
                                    for reference in value:
                                        link = reference["source"]
                                        page = reference["page"]
                                        response_text += f"<{link}> (page {page})\n\n"
                                    reference_section = {
                                        "type": "section",
                                        "text": {
                                            "type": "mrkdwn",
                                            "text": response_text,
                                        }
                                    }
                                    response_block.append(reference_section)
                                    response_block.append({"type": "divider"})
                            else:
                                changed_key = key.replace("_", " ").title()
                                response_text = " "
                                if isinstance(value, str) and value != "":
                                    response_text = f"*{changed_key}*:\n\n{value}\n\n"
                                    key_section = {
                                        "type": "section",
                                        "text": {
                                            "type": "mrkdwn",
                                            "text": response_text,
                                        }
                                    }
                                    response_block.append(key_section)
                                    response_block.append({"type": "divider"})
                                elif isinstance(value, bool):
                                    response_text = f"*{changed_key}*: {'✔️ True' if value else '❌ False'}\n\n"
                                    key_section = {
                                        "type": "section",
                                        "text": {
                                            "type": "mrkdwn",
                                            "text": response_text,
                                        }
                                    }
                                    response_block.append(key_section)
                                    response_block.append({"type": "divider"})

                    slack_client.chat_postMessage(channel=channel_id, blocks=response_block)
                    is_completed = True

                else:
                    time.sleep(1)
                    new_payload = {
                        "run_id": response["run_id"],
                        "verbose": verbose
                    }
                    response = agent_api_call(new_payload, session_id, channel_id)
                    
                    if response is None:
                        update_message(channel_id, ts, "text", "There was some error while fetching the answer!")
                        is_completed = True

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        update_message(channel_id, ts, "text", "An error occurred while processing the request.")

def get_verbose_block(text):
    block = [
        {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "```" + text + "```",
        }
    }
    ]
    return block


def get_initial_block(channel_id):
    initial_blocks= [
    {
        "type": "section",
        "text": {
            "type": "plain_text",
            "text": "Select your chat agent: \n\n",
        }
    },
    {
        "type": "actions",
        "block_id": "agent_selection",
        "elements": [
            {
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select Agent"
                },
                "options": [],
                "action_id": "selected_agent"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Select"
                },
                "value": "select_agent",
                "action_id": "select_agent"
            }
        ]
    }
    ]
    agent_options = []
    agents = get_agent_list(channel_id)
    for agent in agents:
        text = agent.get("channel_name")
        id = agent.get("team_id")
        option = {
                    "text": {
                        "type": "plain_text",
                        "text": f"{text}"
                    },
                    "value": f"{id}"
                }
        agent_options.append(option)
    initial_blocks[1]["elements"][0]["options"] = agent_options
        

    return initial_blocks

def get_select_vds_block(senario, channel_id):
    try:
        vds_options = []

        select_vds_block = [
                {
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": "Select your VDS: \n\n"
                    }
                },
                {
                    "type": "actions",
                    "block_id": "vds_select",
                    "elements": [
                        {
                            "type": "static_select",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Select VDS"
                            },
                            "options": [],
                            "action_id": "selected_vds"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Select"
                            },
                            "value": senario,
                            "action_id": "select_vds"
                        }
                    ]
                }
            ]
            
        vds_data = get_vds_list(channel_id)
        if vds_data == "Unauthorized":
            return "Unauthorized"
        elif vds_data != None:
            for vds in vds_data:
                print("VDS:")
                print(vds)
                title = vds.get("vds_name")
                id = vds.get("vds_id")
                option = {
                    "text": {
                        "type": "plain_text",
                        "text": f"{title} ({id})"
                    },
                    "value": f"{id}"
                }
                vds_options.append(option)

            print("VDS OPTIONS: ")
            print(vds_options)

            select_vds_block[1]["elements"][0]["options"] = vds_options

            # print("VDS FINAL DATA: ")
            # print(select_vds_block)

            return select_vds_block
        else:
            return None
    except Exception as e:
        print(e)
        return None

def get_feedback_block():
    feedback_block = [
		{
			"type": "input",
			"element": {
				"type": "plain_text_input",
				"action_id": "feedback_text"
			},
			"label": {
				"type": "plain_text",
				"text": "Please give us your feedback!"
			}
		},
		{
			"type": "actions",
			"elements": [
				{
					"type": "button",
					"text": {
						"type": "plain_text",
						"text": "Submit"
					},
					"value": "submit_feedback",
					"action_id": "submit_feedback"
				}
			]
		}
	]

    return feedback_block

slack_token = os.environ.get("SLACK_BOT_TOKEN")

def download_file_with_consent(download_url, filename):
    try:
        headers = {"Authorization": f"Bearer {slack_token}"} 
        response = requests.get(download_url, stream=True, headers=headers)
        response.raise_for_status()

        with open(f'./files/{filename}', 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)

        return filename
    except requests.exceptions.RequestException as e:
        print(f"Error downloading file: {e}")
        return None
    
def upload_file_to_azure(blob_name: str):
    try:
        blob_service_client = BlobServiceClient.from_connection_string(os.getenv("CONNECTION_STRING"))
        blob_client = blob_service_client.get_blob_client(container="slack-files", blob=blob_name)
        with open(f'./files/{blob_name}', 'rb') as file:
            file_content = file.read()
            blob_upload_result = blob_client.upload_blob(file_content, overwrite=True)
            print(blob_upload_result) 
        os.remove(f'./files/{blob_name}')
    except Exception as e:
        print(f"Error uploading file: {e}")

def update_message(channel_id, ts, choice, reply):
    if choice == "text":
        slack_client.chat_update(channel=channel_id, ts=ts, text=reply)
    else:
        slack_client.chat_update(channel=channel_id, ts=ts, blocks=reply)

divider_block = [
		{
			"type": "divider"
		}
	]