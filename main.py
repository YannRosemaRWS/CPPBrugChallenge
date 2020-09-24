# import requests
# import asyncio
import websocket
import logging
import json

logger = logging.getLogger('websockets')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

def on_message(ws, message):
    logger.debug(f"Message received: {message}")
    # print(f"{message}")

def on_open(ws):
    logger.debug(f"Opening websocket")
    logger.debug(f"Creating request")
    request = json.dumps({"messageType":"Subscription","subscription":{"type":"Event","action":"Subscribe"}})
    logger.debug(f"Sending request: {request}")
    ws.send(request)

if __name__ == "__main__":
    ws = websocket.WebSocketApp('ws://10.0.0.26:13314/api/subscriptions', on_message = on_message,on_open=on_open)
    ws.run_forever()
