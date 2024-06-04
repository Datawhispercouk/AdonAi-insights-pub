from flask import Flask, request, Response, send_file
from slackeventsapi import SlackEventAdapter
import os
from threading import Thread
from slack_sdk import WebClient
import json
from dotenv import load_dotenv
from utils import getSessionID, structured_api_call, rag_api_call, create_structured_response_block, append_to_json, get_rating_block, send_query_block, get_rag_response_text, get_initial_block, get_feedback_block, get_select_vds_block, signin, get_user_info

load_dotenv('.env')

channel_chosen_api = {}
channel_session_id = {}
channel_vds = {}
question_count = 0

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("FLASK_APP_SECRET_KEY")

SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
slack_token = os.environ.get("SLACK_BOT_TOKEN")

slack_client = WebClient(slack_token)

slack_events_adapter = SlackEventAdapter(
    SLACK_SIGNING_SECRET, "/slack/events", app
)

bot_id = slack_client.api_call("auth.test")["user_id"]

@app.route('/slack/session/start', methods=['POST'])
def handle_start_session():
    data = request.form
    channel_id = data.get("channel_id")
    text = data.get('text')
    words = text.split()
    if len(words) == 2:
        def handle_login():
            login_data = signin(words[0], words[1], channel_id)
            if login_data == None:
                slack_client.chat_postMessage(channel=channel_id, text="Login Failed! Try again ☹️")
            else:
                channel_vds[channel_id] = login_data[0]
                slack_client.chat_postMessage(channel=channel_id, text=f"Welcome `{login_data[1]}`, you have logged In successfully!🎉 Currently Using {login_data[2]} VDS.")
                if question_count != 0:
                    slack_client.chat_postMessage(channel=channel_id, text=f"I have answered {question_count} questions successfully so far. How can I help you?")
                initial_blocks = get_initial_block()
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
    if channel_chosen_api.get(channel_id):
        channel_chosen_api.pop(channel_id, None)
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
            agent = channel_chosen_api.get(channel_id)
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
        chosen_api = channel_chosen_api.get(channel_id)
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
                if chosen_api == "Structured Channel":
                    response_string = structured_api_call(question, session_id, channel_id)
                    if response_string == "Unauthorized":
                        update_message(channel_id, ts, "text", "Login token has expired. Please Login again using `/start username password`")
                    elif response_string != None:
                        response_block = create_structured_response_block(response_string, user_id)
                        update_message(channel_id, ts, "block", response_block)
                        send_query_block(response_string["input"], channel_id, slack_client)
                        question_count += 1
                    else:
                        update_message(channel_id, ts, "text", "There was some error while fetching the answer!")
                else:
                    response_string = rag_api_call(question, session_id, channel_id)
                    if response_string == "Unauthorized":
                        update_message(channel_id, ts, "text", "Login token has expired. Please Login again using `/start username password`")
                    elif response_string != None:
                        response_text = get_rag_response_text(response_string)
                        update_message(channel_id, ts, "text", "```" + response_text + "```")
                        question_count += 1
                    else:
                        update_message(channel_id, ts, "text", "There was some error while fetching the answer!")

            thread = Thread(target=handle_reply, args=(channel_id, user_id, chosen_api, question, session_id, response["ts"]))
            thread.start()

    thread = Thread(target=handle_timeout)
    thread.start()
    return Response(), 200

@slack_events_adapter.on("message")
def handle_message(event_data):
    def send_reply(value):     
        global question_count
        event = value["event"]
        if event.get("subtype") is None:
            channel_type = event.get("channel_type")
            if event["user"] == bot_id:
                return Response(status=200)
            elif channel_type == "im":   
                message_text = event["text"]
                channel_id = event["channel"]
                user_id = event["user"]
                chosen_api = channel_chosen_api.get(channel_id)
                if not chosen_api:
                        slack_client.chat_postMessage(channel=channel_id, text="Please choose an API and create a session using command '/start'.")
                        slack_client.chat_postMessage(channel=channel_id, blocks=divider_block)
                else:
                        response = slack_client.chat_postMessage(channel=channel_id, text=f"Wait ⏳, Let me think 🧠and come with best response for you 🤖")
                        slack_client.chat_postMessage(channel=channel_id, blocks=divider_block)
                        ts = response["ts"]
                        session_id = channel_session_id.get(channel_id)
                        if chosen_api == "Structured Channel":
                            response_string = structured_api_call(message_text, session_id, channel_id)
                            if response_string == "Unauthorized":
                                update_message(channel_id, ts, "text", "Login token has expired. Please Login again using `/start username password`")
                            elif response_string != None:
                                response_block = create_structured_response_block(response_string, user_id)
                                update_message(channel_id, ts, "block", response_block)
                                send_query_block(response_string["input"], channel_id, slack_client)
                                question_count += 1
                            else:
                                update_message(channel_id, ts, "text", "There was some error while fetching the answer!")
                        else:
                                response_string = rag_api_call(message_text, session_id, channel_id)
                                if response_string == "Unauthorized":
                                    update_message(channel_id, ts, "text", "Login token has expired. Please Login again using `/start username password`")
                                elif response_string != None:
                                    response_text = get_rag_response_text(response_string)
                                    update_message(channel_id, ts, "text", "```" + response_text + "```")
                                    question_count += 1
                                else:
                                    update_message(channel_id, ts, "text", "There was some error while fetching the answer!")

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
                channel_chosen_api.pop(channel_id, None)
                channel_session_id.pop(channel_id, None)
                update_message(channel_id, ts, "text", f"Selected VDS: {vds_text}")
                initial_block = get_initial_block()
                if question_count != 0:
                    slack_client.chat_postMessage(channel=channel_id, text=f"I have answered {question_count} questions successfully so far. How can I help you?")
                slack_client.chat_postMessage(channel=channel_id, blocks=initial_block)
            else:
                vds = channel_vds[channel_id]
                session_id = getSessionID(vds, channel_id)
                channel_chosen_api[channel_id] = value
                channel_session_id[channel_id] = session_id
                update_message(channel_id, ts, "text", f"You have opted for {value}!")
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
if __name__ == "__main__":
  app.run(debug=True,port=3000)