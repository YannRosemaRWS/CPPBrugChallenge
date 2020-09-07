# import requests
import asyncio
import websockets
import logging
import json
logger = logging.getLogger('websockets')
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

# r = requests.get('http://10.0.0.26/api/device/info')

async def hello():
    uri = "ws://10.0.0.26:13314/api/subscriptions"
    async with websockets.connect(uri) as websocket:
        request = json.dumps({"messageType":"Subscription","subscription":{"type":"Event","action":"Subscribe"}})

        await websocket.send(request)

        response = await websocket.recv()
        jsonResponse = json.loads(response)
        if jsonResponse["subscription"]["returnValue"] == "OK":
            while True:
                response = await websocket.recv()
                jsonResponse = json.loads(response)
                print(f"{jsonResponse}")

asyncio.get_event_loop().run_until_complete(hello())
# asyncio.get_event_loop().run_forever()