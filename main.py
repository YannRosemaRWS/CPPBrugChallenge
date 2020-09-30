import logging
import json
import config
import xmlschema
import asyncio
import websockets
import numpy as np

logger = logging.getLogger('detectie')
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


class DetectionFrame(object):
    def __init__(self, baseID: int, numDetections: int, maxNumDetections: int):
        super().__init__()
        self.baseID = baseID
        self.numDetections = numDetections
        self.detections = []

    @property
    def baseID(self):
        return self._baseID

    @baseID.setter
    def baseID(self, b):
        self._baseID = b

    @property
    def numDetections(self):
        return self._numDetections

    @numDetections.setter
    def numDetections(self, n):
        self._numDetections = n


async def showShape(shape):
    global detectionShapes, lock, detectionUsers
    async with lock:
        if isinstance(shape, list):
            detectionShapes.extend(shape)
        else:
            detectionShapes.append(shape)
        logger.debug(f"Detection IDs: {[x.objectId for x in detectionShapes]}")
        message = json.dumps([shape.toJSON() for shape in detectionShapes])
        try:
            await asyncio.wait([user.send(message) for user in detectionUsers])
        except ValueError as e:
            logger.debug(f"No clients registered for detection.")


async def removeShape(objectId: dict, redraw:bool = True):
    global detectionShapes, lock, detectionUsers
    async with lock:
        if "id" not in objectId.keys():
            detectionShapes = [
                detection for detection in detectionShapes if detection.objectId["type"] != objectId["type"]]
        else:
            detectionShapes = [detection for detection in detectionShapes if detection.objectId["type"]
                               != objectId["type"] or detection.objectId["id"] != objectId["id"]]

        logger.debug(f"Detection IDs: {[x.objectId for x in detectionShapes]}")
        message = json.dumps([shape.toJSON() for shape in detectionShapes])
        if redraw:
            try:
                await asyncio.wait([user.send(message) for user in detectionUsers])
            except ValueError as e:
                logger.debug(f"No clients registered for detection.")


async def main():
    global start_server
    canWebsocketFuture = asyncio.ensure_future(canWebsocket())
    # irWebsocketFuture = asyncio.ensure_future(irWebsocket())
    # websocketFuture = asyncio.ensure_future(start_server)

    done, pending = await asyncio.wait([canWebsocketFuture], return_when=asyncio.FIRST_COMPLETED)

    for task in pending:
        task.cancel()


async def irWebsocket():
    global irCamera
    uri = "ws://10.0.0.26:13314/api/subscriptions"
    async with websockets.connect(uri) as ws:
        logger.debug(f"Opening websocket")
        logger.debug(f"Creating request")
        request = json.dumps({"messageType": "Subscription", "subscription": {
            "type": "Event", "action": "Subscribe"}})
        logger.debug(f"Sending request: {request}")
        await ws.send(request)
        message = await ws.recv()
        logger.debug(f"Request response: {message}")
        jsonMessage = json.loads(message)
        if jsonMessage["subscription"]["returnValue"] == "OK":
            while True:
                message = await ws.recv()
                logger.debug(f"Message received: {message}")
                jsonMessage = json.loads(message)
                if jsonMessage["type"] == "PedestrianPresence":
                    for detectionZone in irCamera.detectionZones:
                        if detectionZone.zoneId == int(jsonMessage["zoneId"]):
                            if jsonMessage["state"] == "Begin":
                                shapeSpace = np.flip(irCamera.shapeToSpace(detectionZone)[:,0:2],1)
                                polygonSpace = config.Polygon(list(tuple(x) for x in shapeSpace), objectId={
                                    "type": "ir", "id": detectionZone.zoneId})
                                await showShape(polygonSpace)
                            elif jsonMessage["state"] == "End":
                                objectId = {"type": "ir",
                                            "id": detectionZone.zoneId}
                                await removeShape(objectId)


async def canWebsocket():
    global frameIDs, segmentIDs, lidars
    uri = "ws://192.168.1.100:8765"
    detectionFrame = None
    async with websockets.connect(uri) as ws:
        while True:
            message = await ws.recv()
            logger.debug(f"Message received: {message}")
            jsonMessage = json.loads(message)
            dataBytes = bytearray.fromhex(jsonMessage["data"])
            if jsonMessage["arbitration_id"] in frameIDs:
                # Frame message
                numDetections = int.from_bytes(dataBytes[0:1], 'little')
                detectionFrame = DetectionFrame(
                    jsonMessage["arbitration_id"]-1, numDetections, 8)
                objectId = {"type": str(jsonMessage["arbitration_id"]-1)}
                await removeShape(objectId, False)
            elif jsonMessage["arbitration_id"] in segmentIDs:
                # Segment message
                # distance
                distance = int.from_bytes(dataBytes[0:2], 'little')
                # valid
                valid = int.from_bytes(dataBytes[4:6], 'little')
                # channel number
                channel = int.from_bytes(dataBytes[6:8], 'little')
                if valid == 1:
                    for lidar in lidars:
                        if lidar.baseFrameIdTx == jsonMessage["arbitration_id"]-2:
                            polygonSpace = lidar.beamToCartesian(
                                channel, distance/100)
                            polygonSpace.objectId = {"type": str(
                                lidar.baseFrameIdTx), "id": channel}
                            if detectionFrame is not None:
                                detectionFrame.detections.append(polygonSpace)
                else: 
                    if detectionFrame is not None:
                        detectionFrame.detections.append(None)
                if detectionFrame is not None:
                    if detectionFrame.numDetections == len(detectionFrame.detections):
                        await showShape([detection for detection in detectionFrame.detections if detection is not None])


async def register(websocket):
    global detectionUsers
    detectionUsers.add(websocket)
    # await notify_users()


async def unregister(websocket):
    global detectionUsers
    try:
        detectionUsers.remove(websocket)
    except Exception:
        pass
    # await notify_users()


async def handler(websocket, path):
    global brug
    await websocket.send(json.dumps([brug.toJSON()]))
    try:
        async for message in websocket:
            data = json.loads(message)
            if data["action"] == "register":
                await register(websocket)
            elif data["action"] == "unregister":
                await unregister(websocket)
            else:
                logging.error(f"unsupported event: {data}")
    finally:
        await unregister(websocket)

if __name__ == "__main__":
    logger.info(f"Start config...")
    brugSchema = xmlschema.XMLSchema('Brug.xsd')
    brugConfig = 'brugConfig.xml'
    if brugSchema.is_valid(brugConfig):
        try:
            brug = config.parseBrugData(brugSchema, brugConfig)
            logger.debug(f"Brug config done!")
        except config.DataParseError as e:
            logger.error(f"Brug config error: {e}")
    else:
        logger.error(f"Brug config invalid!")

    # irSchema = xmlschema.XMLSchema('IR.xsd')
    try:
        irCamera = config.parseIRData('irConfig.xml', (320, 240))
        logger.debug(f"Brug config done!")
    except Exception as e:
        logger.error(f"IR config error: {e}")

    lidarSchema = xmlschema.XMLSchema('Lidar.xsd')
    lidarConfig = 'lidarConfig.xml'
    if lidarSchema.is_valid(lidarConfig):
        try:
            lidars = config.parseLidarData(lidarSchema, lidarConfig)
            logger.debug(f"Lidar config succesful!")
        except Exception as e:
            logger.error(f"Lidar config error: {e}")
    else:
        logger.error(f"Lidar config invalid!")

    logger.info(f"All config done!")

    frameIDs = []
    segmentIDs = []
    for lidar in lidars:
        frameIDs.append(lidar.baseFrameIdTx+1)
        segmentIDs.append(lidar.baseFrameIdTx+2)

    detectionShapes = []
    lock = asyncio.Lock()

    detectionUsers = set()

    start_server = websockets.serve(handler, "0.0.0.0", 6789)

    canWebsocketFuture = asyncio.ensure_future(canWebsocket())
    irWebsocketFuture = asyncio.ensure_future(irWebsocket())

    logger.info(f"Start program...")
    # asyncio.get_event_loop().run_until_complete(main())
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
