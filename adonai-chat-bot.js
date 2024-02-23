/**
 * Represents a Chat module that interacts with a chatbot API.
 * @param {string} apiKey - The API key used for authentication.
 * @param {string} host - The host URL of the chatbot API.
 * @param {string} machineId - The ID of the machine.
 * @param {string} machinePassword - The password of the machine.
 * @returns {Object} An object containing the `ask` method to interact with the chatbot.
 */
(function (apiKey, host, machineId, machinePassword) {
  const _apiKey = apiKey;
  const _host = host;

  /**
   * Retrieves an access token from the chatbot API.
   * @returns {Promise<string>} A promise that resolves with the access token.
   */
  async function getAccessToken() {
    try {
      const url = `${_host}/machine/token`;
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          APIKey: _apiKey,
          MachineId: machineId,
          Password: machinePassword
        })
      });

      if (!response.ok) {
        throw new Error('Failed to get access token');
      }

      return response.json();
    } catch (error) {
      console.error('Error in getAccessToken:', error);
      throw error;
    }
  }

  /**
   * Creates a session with the chatbot API.
   * @returns {Promise<{access_token: string, session_id: string}>} A promise that resolves with an object containing the access token and session ID.
   */
  async function createSession() {
    try {
      const { access_token } = await getAccessToken();
      const url = `${_host}/session/createsession`;
      const response = await fetch(url, {
        method: 'POST',
        headers: { Authorization: `Bearer ${access_token}` },
        body: JSON.stringify({})
      });

      if (!response.ok) {
        throw new Error('Failed to create session');
      }

      const { session_id } = await response.json();
      return { access_token, session_id };
    } catch (error) {
      console.error('Error in createSession:', error);
      throw error;
    }
  }

  /**
   * Sends a question to the chatbot API and retrieves the response.
   * @param {string} question - The question to ask the chatbot.
   * @returns {Promise<Object>} A promise that resolves with the chatbot's response.
   */
  async function chat(question) {
    try {
      const { access_token, session_id } = await createSession();
      const url = `${_host}/chatservice/chatbot/${session_id}`;
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${access_token}`
        },
        body: JSON.stringify({ question })
      });

      if (!response.ok) {
        throw new Error('Failed to chat with chat bot');
      }

      return response.json();
    } catch (error) {
      console.error('Error in chat:', error);
      throw error;
    }
  }

  /**
   * Interacts with the chatbot by sending a question.
   * @param {string} question - The question to ask the chatbot.
   * @returns {Promise<Object>} A promise that resolves with the chatbot's response.
   */
  window.adonai = {
    ask: function (question) {
      return chat(question);
    }
  };
})('apiKey', 'host', 'machineId', 'machinePassword');
