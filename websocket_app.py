import websockets
import asyncio
import logging
import can
import json

logger = logging.getLogger('canbus')
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


async def consumer(message):
    pass


async def producer():
    global reader
    canMsg = await reader.get_message()
    canDict = dict([attr, getattr(canMsg, attr)] for attr in dir(canMsg) if not attr.startswith('_'))
    canDict['data'] = canDict['data'].hex()
    del canDict['equals']
    jsonMsg = json.dumps(canDict)
    return jsonMsg


async def consumer_handler(websocket:websockets.WebSocketServerProtocol, path):
    async for message in websocket:
        logger.debug(f"Recieved from websocket: {message}")
        await consumer(message)

async def producer_handler(websocket, path):
    while True:
        message = await producer()
        logger.debug(f"Sending over websocket: {message}")
        await websocket.send(message)


async def handler(websocket, path):
    global bus, reader

    startMsg = can.Message(data=bytearray(
        [3, 0, 0, 0, 0, 0, 0, 0]), arbitration_id=1856, is_extended_id=False)
    bus.send(startMsg)
    startMsgResponse = await reader.get_message()
    logger.info(f"Start message response from CAN: {startMsgResponse}")

    consumer_task = asyncio.ensure_future(
        consumer_handler(websocket, path))
    producer_task = asyncio.ensure_future(
        producer_handler(websocket, path))
    done, pending = await asyncio.wait(
        [consumer_task, producer_task],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()

    stopMsg = can.Message(data=bytearray(
        [1, 0, 0, 0, 0, 0, 0, 0]), arbitration_id=1856, is_extended_id=False)
    bus.send(stopMsg)
    stopMsgResponse = await reader.get_message()
    logger.info(f"Stop message response from CAN: {stopMsgResponse}")

def debug_can_message(msg):
    logger.debug(f"Recieved from CAN: {msg}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    bus = can.interface.Bus(bustype='seeedstudio', channel='/dev/ttyUSB0',
                            bitrate=1000000, baudrate=2000000, frame_type='STD', operation_mode='normal')

    reader = can.AsyncBufferedReader()
    notifier = can.Notifier(bus, [reader, debug_can_message], loop=loop)

    start_server = websockets.serve(handler, "0.0.0.0", 8765)

    loop.run_until_complete(start_server)
    loop.run_forever()
