
# Slack Chat App

This multi-channel chatbot lets you choose between two AI assistants: a structured channel providing informative answers with tables, graphs, and text, or a conversational channel offering text-based responses and maintaining a chat history for context.




## Setup - Flask App

1. (Optional step) Create a new python environment using python or conda. 

To create using python on Windows run the below command:

```
python -m venv venv
.\venv\Scripts\activate
```

2. Install the libraries required using `requirements.txt` file using the command:

```
pip install -r requirements.txt
```
3. Install `orca` for plotly to convert graphs to images using the command:

```
conda install orca
```

4. Create a .env file and add the following sensitive credentials in it:

```
SLACK_SIGNING_SECRET=<YOUR SLACK SECRET SIGNING KEY>
SLACK_BOT_TOKEN=<YOU SLACK APP BOT USER OAUTH TOKEN>
USERNAME=<API LOGIN USERNAME>
PASSWORD=<API LOGIN PASSWORD>
BASE_API=<BASE URL OF APIs>
ACCESS_TOKEN=<ACCESS TOKEN OBTAINED AFTER LOGGING IN TO THE API>
VDS_ID=<YOUR VDS ID>
BASE_FLASK_APP_URL=<YOUR FLASK APP BASE URL>
FLASK_APP_SECRET_KEY=<YOUR SECRET KEY>
```

5. Run the Flask App using the command:

```
python .\app.py
```


## Setup - Slack Chat App

### Create App

 1. Go to [Slack API](https://api.slack.com/) and navigate to `Your Apps` page.
 2. On the Your Apps page, select **Create New App**.
 3. Select **From scratch**.
 4. Enter your **App Name**.
 5. Select the **Workspace** where you'll be using your app.
 6. Select **Create App**.

 ### OAuth and Permissions
 Next, add scope to your app. Scopes give your app permission to perform actions, such as posting messages in your workspace.


 1. Within **OAuth & Permissions**, scroll down to **Scopes**.
 2. Under **Bot Token Scopes**, select **Add an OAuth Scope**.
 3. Add the following scopes:
- chat:write
- commands
- im:history
- channels:history

 ### Install and Authorize the app
 1. Return to the **Basic Information** section of the app management page.
 2. Install your app by selecting the **Install to Workspace** button.
 3. You'll now be sent through the Slack OAuth flow. Select **Allow** on the following screen.

 ### Configure Event Listening
 Slack apps listen and respond to events through Event APIs. Enable Events and subscribe to bot events.


 1. Select **Event Subscriptions** and toggle **Enable Events** to ON.
 2. Within **Subscribe to bot events**, select **Add Bot User Event**
 3. Subscribe to the following events:
- message.channels
- message.im
4. Next, set the **Request URL** to:
```
<YOUR FLASK SERVER BASE URL>/slack/events
```

Note that you'll need to implement your own server to host the flask app for this step.

5. Click on **Save Changes** and **Reinstall the App**

### Slash Commands
 Next, add slash commands to your app. Slash commands allow users to invoke your app by typing a string into the message composer box. 


 1. Within **Slash Commands**, click on **Create new command**.
 2. Under **Bot Token Scopes**, select **Add an OAuth Scope**.
 3. Add `/start` command:
- Command: `/start`
- Request URL: `<Your FLASK SERVER BASE URL>/slack/session/start`
- Short Description: `Start an API channel session`

Click on **Save**

4. Add `/exit` command:
- Command: `/exit`
- Request URL: `<Your FLASK SERVER BASE URL>/slack/session/exit`
- Short Description: `End an API channel session`

Click on **Save**

5. Add `/start-private` command:
- Command: `/start-private`
- Request URL: `<Your FLASK SERVER BASE URL>/slack/session/start-private`
- Short Description: `Start a private API channel session`

Click on **Save**

6. Add `/question` command:
- Command: `/question`
- Request URL: `<Your FLASK SERVER BASE URL>/slack/question`
- Short Description: `Ask question to the channel API`

Click on **Save**

To allow users to send Slash commands and messages from the messages tab of the Chat App:

Within **App Home**, toggle **Message Tab** to ON and click on the **Allow users to send Slash commands and messages from the messages tab** radio button.

 ### Interactivitiy
 Slack apps listen and respond to events through Event APIs. Enable Events and subscribe to bot events.


 1. Within **Interactivity & Shortcuts**, toggle **Interactivity** to ON
2. Next, set the **Request URL** to:
```
<YOUR FLASK SERVER BASE URL>/slack/interactions
```
3. Click on **Save Changes**

Note that you'll need to implement your own server to host the flask app for this step.


 ### Start a conversation
 The Chat App is configured and ready to use. 


 1. Open your **Slack Workspace**
2. Under **Apps** on the conversations list, click on **Add apps**
3. Choose your App and start a conversation.
## Commands

- `/start` - Starts a new session and lets the user choose which channel (Structured or RAG) to use.
- `/question` - Once the session is started, this command is used to ask questions.

```
Example:
    /question How to setup wifi?
```
- `/exit` - Ends the current session.