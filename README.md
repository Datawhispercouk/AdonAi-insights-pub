# AdonAi-insights-pub 
![Logo](assets/adonai_logo.png)

This repo contains code snippets to enable you to use our APIs! 

## Releases
You can find the release documentation in the [wiki](https://github.com/Datawhispercouk/AdonAi-insights-pub/wiki/Releases)!  

## Setup - chatbot_api_wrappers.py
1. (Optional step) Create a new python environment using pipenv or conda. To create using conda run the below command: 

```
conda create -n env_name python=3.11.0 
conda activate env_name
```
You may choose not to create a environment since we need to install only 1 library.  
2. Install requests using ``` pip install requests```  
3. Get API Key, MachineID and Password from your system admin!  
4. Replace values in the `chatbot_api_wrappers.py`.  
5. You can import the fuctions to use them. You can also reference the `main()` to understad the flow of the functions. 

## Setup - adonai-chat-bot.js
1. Include the Chat module in the body of the HTML file:
```html
<script src="adonai-chat-bot.js"></script>
```

2. Get `apiKey`, `host`, `machineId`, and `machinePassword` from your system admin:
```javascript
(function (apiKey, host, machineId, machinePassword) {
  // ... rest of the module's code
})(apiKey, host, machineId, machinePassword);
```

3. Utilize it in React.js:
```jsx
import React, { useState } from 'react';

function App() {
  const [message, setMessage] = useState('');
  const [response, setResponse] = useState('');

  const handleSendMessage = async () => {
    try {
      const { result } = await window.adonai.ask(message);
      setResponse(result.result.text);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  return (
    <div>
      <h1>Chatbot App</h1>
      <div>
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Type your message..."
        />
        <button onClick={handleSendMessage}>Send</button>
      </div>
      <div>
        <p>Response: {response}</p>
      </div>
    </div>
  );
}

export default App;
```

4. OPTIONAL: Declare module globally:
```typescript jsx
declare global {
  interface Window {
    adonai: {
      ask: (question: string) => Promise<{
        status: number;
        result: {
          result: {
            question: string;
            chat_history: string;
            query: string;
            contexts: string;
            text: string;
          };
        };
      }>;
    };
  }
}
```
