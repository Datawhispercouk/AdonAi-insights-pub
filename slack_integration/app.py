from flask import Flask, request, Response, send_file
from slackeventsapi import SlackEventAdapter
import os
from threading import Thread
from slack_sdk import WebClient
import json
from dotenv import load_dotenv
from utils import getSessionID, structured_api_call, rag_api_call, agent_api_call, create_structured_response_block, append_to_json, get_rating_block, send_query_block, get_rag_response_text, get_agent_response_block, get_initial_block, get_feedback_block, get_select_vds_block, signin, get_user_info, download_file_with_consent, upload_file_to_azure, update_message, display_agent_response

load_dotenv('.env')

channel_chosen_agent = {}
channel_chosen_team_id = {}
channel_session_id = {}
channel_vds = {}
channel_verbose_status = {}
question_count = 0

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("FLASK_APP_SECRET_KEY")

SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
slack_token = os.environ.get("SLACK_BOT_TOKEN")
user_token = os.environ.get("USER_TOKEN")
slack_client = WebClient(slack_token)
user_client = WebClient(user_token)

slack_events_adapter = SlackEventAdapter(
    SLACK_SIGNING_SECRET, "/slack/events", app
)

bot_id = slack_client.api_call("auth.test")["user_id"]

@app.route('/slack/session/start', methods=['POST'])
def handle_start_session():
    data = request.form
    print(data)
    channel_id = data.get("channel_id")
    text = data.get('text')
    words = text.split()
    if len(words) == 2:
        def handle_login():
            login_data = signin(words[0], words[1], channel_id)
            if login_data == "Invalid Username or password":
                slack_client.chat_postMessage(channel=channel_id, text="Invalid Username or password! Try again")
            elif login_data == "Couldn't get User Info":
                slack_client.chat_postMessage(channel=channel_id, text="Couldn't get User Info! Try again")
            else:
                channel_vds[channel_id] = login_data[0]
                slack_client.chat_postMessage(channel=channel_id, text=f"Welcome `{login_data[1]}`, you have logged In successfully!🎉 Currently Using {login_data[2]} VDS.")
                if question_count != 0:
                    slack_client.chat_postMessage(channel=channel_id, text=f"I have answered {question_count} questions successfully so far. How can I help you?")
                initial_blocks = get_initial_block(channel_id)
                slack_client.chat_postMessage(channel=channel_id, blocks=initial_blocks)
                slack_client.chat_postMessage(channel=channel_id, blocks=divider_block)
        thread = Thread(target=handle_login)
        thread.start()
    else:
        slack_client.chat_postMessage(channel=channel_id, text="`/start` command format error. Sample format: `/start username password`")
    return Response(), 200

@app.route('/slack/vds-change', methods=['POST'])
def handle_vds_change():
    try:
        data = request.form
        channel_id = data.get("channel_id")
        current_vds = channel_vds.get(channel_id)
        if current_vds != None:
            response = slack_client.chat_postMessage(channel=channel_id, text="Getting list of VDS's available")
            slack_client.chat_postMessage(channel=channel_id, blocks=divider_block)
            def handle_vds_change_list_load(channel_id, ts):
                vds_change_block = get_select_vds_block("vds_change", channel_id)
                if vds_change_block == "Unauthorized":
                    update_message(channel_id, ts, "text", "Login token has expired. Please Login again using `/start username password`")
                elif vds_change_block != None:
                    update_message(channel_id, ts, "block", vds_change_block)
                else:
                    update_message(channel_id, ts, "text", "There was an error while fetching VDS List")
            thread = Thread(target=handle_vds_change_list_load, args=(channel_id, response["ts"]))
            thread.start()
        else:
            slack_client.chat_postMessage(channel=channel_id, text="Currently no session is active. Please choose an API and create a session using command `/start username password`")
            slack_client.chat_postMessage(channel=channel_id, blocks=divider_block)
        return Response(), 200
    except Exception as e:
        print(e)
        return Response(), 200

@app.route('/slack/agent-change', methods=['POST'])
def handle_agent_change():
    try:
        data = request.form
        channel_id = data.get("channel_id")
        current_agent = channel_chosen_agent.get(channel_id)
        if current_agent != None:
            response = slack_client.chat_postMessage(channel=channel_id, text="Getting list of Agents available")
            slack_client.chat_postMessage(channel=channel_id, blocks=divider_block)
            def handle_agent_change_list_load(channel_id, ts):
                agent_change_block = get_initial_block(channel_id)
                if agent_change_block == "Unauthorized":
                    update_message(channel_id, ts, "text", "Login token has expired. Please Login again using `/start username password`")
                elif agent_change_block != None:
                    update_message(channel_id, ts, "block", agent_change_block)
                else:
                    update_message(channel_id, ts, "text", "There was an error while fetching Agents List")
            thread = Thread(target=handle_agent_change_list_load, args=(channel_id, response["ts"]))
            thread.start()
        else:
            slack_client.chat_postMessage(channel=channel_id, text="Currently no session is active. Please choose an API and create a session using command `/start username password`")
            slack_client.chat_postMessage(channel=channel_id, blocks=divider_block)
        return Response(), 200
    except Exception as e:
        print(e)
        return Response(), 200

@app.route('/slack/session/start-private', methods=['POST'])
def handle_start_private_session():
    data = request.form
    user_id = data.get("user_id")
    channel_id = data.get("channel_id")
    slack_client.chat_postMessage(channel=channel_id, text=f"Hey <@{user_id}>, Check your private channel to start the session")
    slack_client.chat_postMessage(channel=channel_id, blocks=divider_block)
    slack_client.chat_postMessage(channel=user_id, text=f"Hey <@{user_id}>, Start by Logging in using command `/start username password`")
    slack_client.chat_postMessage(channel=user_id, blocks=divider_block)
    return Response(), 200

@app.route('/slack/session/exit', methods=['POST'])
def handle_exit_session():
    data = request.form
    channel_id = data.get("channel_id")
    if channel_chosen_agent.get(channel_id):
        channel_chosen_agent.pop(channel_id, None)
        channel_session_id.pop(channel_id, None)
        channel_vds.pop(channel_id, None)
        slack_client.chat_postMessage(channel=channel_id, text="Chat session closed")
        feedback_block = get_feedback_block()
        response = slack_client.chat_postMessage(channel=channel_id, blocks=feedback_block)
        rating_block = get_rating_block(response["ts"], "none")
        slack_client.chat_postMessage(channel=channel_id, blocks=rating_block)
        slack_client.chat_postMessage(channel=channel_id, blocks=divider_block)
    else:
        slack_client.chat_postMessage(channel=channel_id, text="Currently no session is active. Please choose an API and create a session using command '/start'.")
        slack_client.chat_postMessage(channel=channel_id, blocks=divider_block)
    return Response(), 200

@app.route('/slack/info', methods=['POST'])
def handle_info():
    try:
        data = request.form
        channel_id = data.get("channel_id")
        current_vds = channel_vds.get(channel_id)
        if current_vds != None:
            agent = channel_chosen_agent.get(channel_id)
            session_id = channel_session_id.get(channel_id)
            
            user_data = get_user_info(channel_id)
            print(user_data)

            response_text = "*Information about the current status of the ChatBot:*\n"
            response_text += "*Company:* " + user_data["CustomerName"] + "\n"
            response_text += "*Division:* " + user_data["Division"]["DivisionName"] + "\n"
            response_text += "*Username:* " + user_data["UserName"] + "\n"
            response_text += "*Current VDS:* " + current_vds + "\n"
            response_text += "*Channel:* " + agent + "\n"
            response_text += "*Session ID:* " + session_id
            
            slack_client.chat_postMessage(channel=channel_id, text=response_text)
            slack_client.chat_postMessage(channel=channel_id, blocks=divider_block)
        else:
            slack_client.chat_postMessage(channel=channel_id, text="There is no user logged in or session created. Login and create a chat session using command `/start username password`")
            slack_client.chat_postMessage(channel=channel_id, blocks=divider_block)
        return Response(), 200
    except Exception as e:
        print(e)
        return Response(), 200

@app.route('/slack/question', methods=['POST'])
def handle_question():
    data = request.form
    def handle_timeout():
        channel_id = data.get("channel_id")
        user_id = data.get("user_id")
        chosen_api = channel_chosen_agent.get(channel_id)
        if not chosen_api:
            slack_client.chat_postMessage(channel=channel_id, text="Please choose an API and create a session using command '/start'.")
            slack_client.chat_postMessage(channel=channel_id, blocks=divider_block)
        else:
            question = data.get('text')
            slack_client.chat_postMessage(channel=channel_id, text=f"Question: {question}")
            response = slack_client.chat_postMessage(channel=channel_id, text=f"Wait ⏳, Let me think 🧠and come with best response for you 🤖")
            slack_client.chat_postMessage(channel=channel_id, blocks=divider_block)
            session_id = channel_session_id.get(channel_id)

            def handle_reply(channel_id, user_id, chosen_api, question, session_id, ts):
                global question_count
                if chosen_api == "Analytics":
                    response_string = structured_api_call(question, session_id, channel_id)
                    if response_string == "Unauthorized":
                        update_message(channel_id, ts, "text", "Login token has expired. Please Login again using `/start username password`")
                    elif response_string != None:
                        response_block = create_structured_response_block(response_string, user_id)
                        update_message(channel_id, ts, "block", response_block)
                        send_query_block(response_string["metadata"]["input"], channel_id, slack_client)
                        question_count += 1
                    else:
                        update_message(channel_id, ts, "text", "There was some error while fetching the answer!")
                elif chosen_api == "Rag":
                    response_string = rag_api_call(question, session_id, channel_id)
                    if response_string == "Unauthorized":
                        update_message(channel_id, ts, "text", "Login token has expired. Please Login again using `/start username password`")
                    elif response_string != None:
                        response_text = get_rag_response_text(response_string)
                        update_message(channel_id, ts, "text", "```" + response_text + "```")
                        question_count += 1
                    else:
                        update_message(channel_id, ts, "text", "There was some error while fetching the answer!")
                else:
                    # response_string = agent_api_call(question, channel_chosen_team_id.get(channel_id), session_id, channel_id)
                    # if response_string == "Unauthorized":
                    #     update_message(channel_id, ts, "text", "Login token has expired. Please Login again using `/start username password`")
                    # elif response_string != None:
                    #     response_block = get_agent_response_block(response_string)
                    #     update_message(channel_id, ts, "block", response_block)
                    # else:
                    #     update_message(channel_id, ts, "text", "There was some error while fetching the answer!")

                    display_agent_response(question, channel_chosen_team_id.get(channel_id), session_id, channel_id, ts, channel_verbose_status[channel_id])

            thread = Thread(target=handle_reply, args=(channel_id, user_id, chosen_api, question, session_id, response["ts"]))
            thread.start()

    thread = Thread(target=handle_timeout)
    thread.start()
    return Response(), 200

@app.route('/slack/verbose', methods=['POST'])
def handle_verbose_status():
    data = request.form
    def handle_timeout():
        channel_id = data.get("channel_id")
        status = data.get('text')
        if status.lower() == "on":
            channel_verbose_status[channel_id] = True
            slack_client.chat_postMessage(channel=channel_id, text = "Verbose is turned ON")
        elif status.lower() == "off":
            channel_verbose_status[channel_id] = False
            slack_client.chat_postMessage(channel=channel_id, text = "Verbose is turned OFF")
        else:
            slack_client.chat_postMessage(channel=channel_id, text = "Send `/verbose ON` to turn it on and `/verbose OFF` to turn it off")

    thread = Thread(target=handle_timeout)
    thread.start()
    return Response(), 200

@slack_events_adapter.on("message")
def handle_message(event_data):
    def send_reply(value):     
        global question_count
        event = value["event"]
        print(event)
        if event.get("subtype") is None or event.get("subtype") == "file_share":
            channel_type = event.get("channel_type")
            if event["user"] == bot_id:
                return Response(status=200)
            elif channel_type == "im":   
                message_text = event["text"]
                channel_id = event["channel"]
                user_id = event["user"]
                chosen_api = channel_chosen_agent.get(channel_id)
                if not chosen_api:
                        slack_client.chat_postMessage(channel=channel_id, text="Please choose an API and create a session using command '/start'.")
                        slack_client.chat_postMessage(channel=channel_id, blocks=divider_block)
                else:
                        if event.get("subtype") == "file_share":
                            response = slack_client.chat_postMessage(channel=channel_id, text="File is being uploaded 📤. Please wait!")
                            slack_client.chat_postMessage(channel=channel_id, blocks=divider_block)
                            ts = response["ts"]
                            session_id = channel_session_id.get(channel_id)
                            file_url = event["files"][0]["url_private_download"]
                            print(file_url)
                            filename = event["files"][0]["name"]
                            print(filename)
                            filename = download_file_with_consent(file_url, filename)
                            upload_file_to_azure(filename)
                            # response_string = agent_api_call(f'https://filestoragerag.blob.core.windows.net/slack-files/{filename}', channel_chosen_team_id.get(channel_id), session_id, channel_id)
                            # if response_string == "Unauthorized":
                            #     update_message(channel_id, ts, "text", "Login token has expired. Please Login again using `/start username password`")
                            # elif response_string != None:
                            #     response_block = get_agent_response_block(response_string)
                            #     update_message(channel_id, ts, "block", response_block)
                            # else:
                            #     update_message(channel_id, ts, "text", "There was some error while fetching the answer!")
                            display_agent_response(f'https://filestoragerag.blob.core.windows.net/slack-files/{filename}',channel_chosen_team_id.get(channel_id), session_id, channel_id, ts, channel_verbose_status[channel_id])
                        else:
                            response = slack_client.chat_postMessage(channel=channel_id, text=f"Wait ⏳, Let me think 🧠and come with best response for you 🤖")
                            slack_client.chat_postMessage(channel=channel_id, blocks=divider_block)
                            ts = response["ts"]
                            session_id = channel_session_id.get(channel_id)
                            if chosen_api == "Analytics Assistant":
                                response_string = structured_api_call(message_text, session_id, channel_id)
                                if response_string == "Unauthorized":
                                    update_message(channel_id, ts, "text", "Login token has expired. Please Login again using `/start username password`")
                                elif response_string != None:
                                    response_block = create_structured_response_block(response_string, user_id)
                                    update_message(channel_id, ts, "block", response_block)
                                    send_query_block(response_string["metadata"]["input"], channel_id, slack_client)
                                    question_count += 1
                                else:
                                    update_message(channel_id, ts, "text", "There was some error while fetching the answer!")
                            elif chosen_api == "Search Document Assistant":
                                response_string = rag_api_call(message_text, session_id, channel_id)
                                if response_string == "Unauthorized":
                                    update_message(channel_id, ts, "text", "Login token has expired. Please Login again using `/start username password`")
                                elif response_string != None:
                                    response_text = get_rag_response_text(response_string)
                                    update_message(channel_id, ts, "text", "```" + response_text + "```")
                                    question_count += 1
                                else:
                                    update_message(channel_id, ts, "text", "There was some error while fetching the answer!")
                            else:
                                # response_string = agent_api_call(message_text, channel_chosen_team_id.get(channel_id), session_id, channel_id)
                                # if response_string == "Unauthorized":
                                #     update_message(channel_id, ts, "text", "Login token has expired. Please Login again using `/start username password`")
                                # elif response_string != None:
                                #     response_block = get_agent_response_block(response_string)
                                #     update_message(channel_id, ts, "block", response_block)
                                # else:
                                #     update_message(channel_id, ts, "text", "There was some error while fetching the answer!")
                                display_agent_response(message_text, channel_chosen_team_id.get(channel_id), session_id, channel_id, ts, channel_verbose_status[channel_id])


    thread = Thread(target=send_reply, kwargs={"value": event_data})
    thread.start()
    return Response(status=200)

@app.route('/slack/interactions', methods=['POST'])
def slack_interactions():
    try:
        global question_count
        payload = json.loads(request.form['payload'])
        # print(payload)
        action_type = payload["actions"][0]["type"]
        print(action_type)
        if payload['type'] == 'block_actions' and action_type == "button":
            channel_id = payload['container']['channel_id']
            value = payload['actions'][0]['value']
            ts = payload['container']['message_ts']
            if value == "submit_feedback":
                for block in payload['message']['blocks']:
                    if block['type'] == 'input' and block['element']['action_id'] == 'feedback_text':
                        data = {
                            "user_id": payload['user']['id'],
                            "channel_id": payload['channel']['id'],
                            "ts": payload['message']['ts'],
                            "feedback_text": payload['state']['values'][block['block_id']]['feedback_text']['value'],
                            "reaction":""
                        }
                        append_to_json(data, "feedback_text")
                update_message(channel_id, ts, "text", "Thank you for your feedback!")
            elif value == "Thumbs Up":
                updated_block = get_rating_block(payload['message']['blocks'][0]["block_id"],"thumbs_up")
                update_message(channel_id, ts, "block", updated_block)
                data = {
                            "user_id": payload['user']['id'],
                            "channel_id": payload['channel']['id'],
                            "ts": payload['message']['blocks'][0]["block_id"],
                            "feedback_text": "",
                            "reaction":"positive"
                        }
                append_to_json(data, "reaction")

            elif value == "Thumbs Down":
                updated_block = get_rating_block(payload['message']['blocks'][0]["block_id"],"thumbs_down")
                update_message(channel_id, ts, "block", updated_block)
                data = {
                            "user_id": payload['user']['id'],
                            "channel_id": payload['channel']['id'],
                            "ts": payload['message']['blocks'][0]["block_id"],
                            "feedback_text": "",
                            "reaction":"negative"
                        }
                append_to_json(data, "reaction")
            elif payload['actions'][0]['action_id'] == "show_query":
                update_text = "The query used to get this response is: \n\n" + value
                update_block = [
                    {
                    "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": update_text,
                        } 
                    },
                ]
                update_message(channel_id, ts, "block", update_block)
            elif payload['actions'][0]['action_id'] == "select_vds":
                vds_id = payload["state"]["values"]["vds_select"]["selected_vds"]["selected_option"]["value"]
                vds_text = payload["state"]["values"]["vds_select"]["selected_vds"]["selected_option"]["text"]["text"]
                channel_vds[channel_id] = vds_id
                print("Set VDS: " + channel_vds.get(channel_id))
                channel_chosen_agent.pop(channel_id, None)
                channel_session_id.pop(channel_id, None)
                update_message(channel_id, ts, "text", f"Selected VDS: {vds_text}")
                initial_block = get_initial_block(channel_id)
                if question_count != 0:
                    slack_client.chat_postMessage(channel=channel_id, text=f"I have answered {question_count} questions successfully so far. How can I help you?")
                slack_client.chat_postMessage(channel=channel_id, blocks=initial_block)
            elif payload['actions'][0]['action_id'] == "select_agent":
                print("Agent selected")
                vds = channel_vds[channel_id]
                session_id = getSessionID(vds, channel_id)
                agent_team_id = payload["state"]["values"]["agent_selection"]["selected_agent"]["selected_option"]["value"]
                agent_name = payload["state"]["values"]["agent_selection"]["selected_agent"]["selected_option"]["text"]["text"]
                channel_chosen_agent[channel_id] = agent_name
                channel_chosen_team_id[channel_id] = agent_team_id
                channel_session_id[channel_id] = session_id
                channel_verbose_status[channel_id] = False
                update_message(channel_id, ts, "text", f"You have opted for {agent_name}! Verbose is currently OFF! Use command `/verbose ON` to turn it on!")
        return Response(status=200)
    except Exception as e:
        print(e)
        slack_client.chat_postMessage(channel=json.loads(request.form['payload'])['container']['channel_id'], text="There was an error while accessing the API")
        return Response(status=500)

@app.route('/share/<filename>')
def share_file(filename):
  file_path = f"./images/{filename}"
  try:
    return send_file(file_path, as_attachment=True)
  except FileNotFoundError:
    return "File not found", 404
  
# @app.route('/upload', methods=['POST'])
# def upload_file():
#     file = request.files['file']
#     if file and file.filename:
#         filename = secure_filename(file.filename)
#         file.save(f"./files/{filename}")
#         return f"File '{filename}' uploaded successfully!", 200
#     else:
#         return "No file selected for upload.", 404



divider_block = [
		{
			"type": "divider"
		}
	]
if __name__ == "__main__":
  app.run(debug=True,port=3000)