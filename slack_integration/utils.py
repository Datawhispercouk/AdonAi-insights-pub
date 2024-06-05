from tabulate import tabulate
import plotly.graph_objs as go
import plotly.io as pio
import json
import os
from dotenv import load_dotenv
import requests
from datetime import datetime

load_dotenv('.env')

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
    
def get_vds_list(channel_id):
    global channel_access_token
    access_token = channel_access_token[channel_id]
    try:
        print("API called")
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        api_url = os.environ.get("BASE_API") + f'/vdsservice/vds/list'

        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            response_data = response.json()
            return(response_data.get('results'))
        elif response.status_code == 401:
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
    if response_string["figure"] != "":
        image_filename = create_graph(response_string["figure"], user_id)
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

    if response_string["data_points"] != "" and response_string["data_points"] != {}:
        data_points_str = json.loads(response_string["data_points"])
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
    
    if response_string["insights"] != []:
        data_insight = response_string["insights"]
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
    response_text = response_string["result"]["text"]
    if response_string["result"]["metadata"] != []:
        response_text = response_text + "\n\n\nReferences:\n\n"
        for reference in response_string["result"]["metadata"]:
            print(reference)
            link = reference["source"]
            page = reference["page"]
            response_text = response_text + f"{link} (page {page})" + "\n\n"
    if response_string["result"]["safeguard"] != {}:
        response_text = response_text + "\n\nSafeguard Checks:\n\nInput Validation:\n\n"
        for input_validation in response_string["result"]["safeguard"]["input_validation"]:
            policy = input_validation["policy"]
            if input_validation["validation_passed"] == True:
                response_text = response_text + f"✔️ {policy}" + "\n"
            else:
                response_text = response_text + f"❌ {policy}" + "\n"
        response_text = response_text + "\nOutput Validation:\n\n"
        for output_validation in response_string["result"]["safeguard"]["output_validation"]:
            policy = output_validation["policy"]
            if output_validation["validation_passed"] == True:
                response_text = response_text + f"✔️ {policy}" + "\n"
            else:
                response_text = response_text + f"❌ {policy}" + "\n"
    return response_text

def get_initial_block():
    initial_blocks= [
    {
        "type": "section",
        "text": {
            "type": "plain_text",
            "text": "Select your chat channel: \n\n",
        }
    },
    {
        "type": "actions",
        "block_id": "channel_selection",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Structured Channel"
                },
                "value": "Structured Channel",
                "action_id": "structured_channel"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "RAG Channel"
                },
                "value": "RAG Channel",
                "action_id": "rag_channel"
            }
        ]
    }
    ]

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
                title = vds.get("title")
                id = vds.get("id")
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