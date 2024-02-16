import requests
import json


APIKey  = ""              # API Key and host provided by dw
Host = "http://endpoint_from_dw.com"



def get_access_token():
    """Get the access token and refresh token from the API

    Returns:
         dict : The access token and refresh token in a dictionary
    """
    url = f"{Host}/machine/token"

    payload = json.dumps({
        "MachineId": "",  # Created MachineID and password
        "Password": "",
        "APIKey": APIKey
    })
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    if response.status_code != 200:
        return None

    return response.json()  # Returns the access token and refresh token


def createsession(access_token : str): 
    """Create a session for chatbot

    Args:
        access_token (str): The access token generated from the API /machine/token

    Returns:
        str: The session_id for the chatbot
    """
    url = f"{Host}/session/createsession"

    payload = {}
    headers = {
        'Authorization': f"Bearer {access_token}"
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    if response.status_code != 200:
        return None

    session_id = response.json().get("session_id")
    if session_id:
        print(session_id)
        return session_id
    else:
        return None


def chat(session_id :str, access_token:str, question:str):
    """ Ask questions to the chatbot

    Args:
        session_id (str): session_id which is generated from createsession
        access_token (str): access token generated from the API /machine/token
        question (str): question to be asked to the chatbot

    Returns:
        str: The answer to the question from the chatbot
    """
    url = f"{Host}/chatservice/chatbot/{session_id}"

    payload = json.dumps({
        "question": question
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {access_token}"
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    if response.status_code != 200:
        return None

    result = response.json().get("result", {}).get("result", {}).get("text")
    return result



def main():
    # Usage example:
    tokens = get_access_token()                         # Get access token to authenticate
    access_token = tokens["access_token"]

    if access_token:
        session_id = createsession(access_token)        # Create a session for chatbot

        if session_id:
            result = chat(session_id, access_token, "Your question here")    # Send question to chatbot

            if result is not None:
                print(result)
            else:
                print("Error in chat function")
        else:
            print("Error in createsession function")
    else:
        print("Error in get_access_token function")


# sample workflow
if __name__ == '__main__':
    main()