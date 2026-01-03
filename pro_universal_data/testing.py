import requests
# your API secret from (Tools -> API Keys) page


chat = {
    "secret": "5fcfa485601c097cbf2b9050c51cd2be63b64b1f",
    "account": "1727953656c81e728d9d4c2f636f067f89cc14862c66fe7af8796e0",
    "recipient": "+918639700518",
    "type": "text",
    "message": "Hello World!"
}

print(chat)

r = requests.post(url="https://connect2chat.com/api/send/whatsapp", params=chat)

# do something with response object
result = r.json()
print(result)
print('end')

