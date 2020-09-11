import requests
import asyncio
import websockets
import logging
import json
logger = logging.getLogger('websockets')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

async def receiveMessage(closing,closed):
    uri = "ws://10.0.0.26:13314/api/subscriptions"
    async with websockets.connect(uri) as websocket:
        request = json.dumps({"messageType":"Subscription","subscription":{"type":"Event","action":"Subscribe"}})

        await websocket.send(request)

        response = await websocket.recv()
        jsonResponse = json.loads(response)
        if jsonResponse["subscription"]["returnValue"] == "OK":
            while not closing.is_set():
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    jsonResponse = json.loads(response)
                    logger.info(f"{jsonResponse}")
                except asyncio.TimeoutError as e:
                    logger.debug(f"Timeout!")

    closed.set()

async def main():
    r = requests.get('http://10.0.0.26:13314/api/device/info')
    logger.debug(f"{r.text}")

    closing = asyncio.Event()
    closed = asyncio.Event()

    logger.debug(f"Starting IR receiver task")
    subscriptionTask = asyncio.create_task(receiveMessage(closing,closed))

    sleepTime = 10.0
    logger.debug(f"Sleeping for {sleepTime}s, zzz...")
    await asyncio.sleep(sleepTime)

    logger.debug(f"Closing..")
    closing.set()
    await closed.wait()

    logger.debug(f"Everything closed!")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except Exception as e:
        pass
    finally:
        loop.close()

