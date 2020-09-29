import websocket
import logging
import json
import config
import xmlschema
import asyncio
import websockets

logger = logging.getLogger('detectie')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


async def showShape(shape: config.Polygon):
    global detectionShapes, lock
    async with lock:
        detectionShapes.append(shape)
        logger.debug(f"Detection IDs: {[x.objectId for x in detectionShapes]}")


async def removeShape(objectId: dict):
    global detectionShapes, lock
    async with lock:
        if "id" not in objectId.keys():
            detectionShapes = [
                detection for detection in detectionShapes if detection.objectId["type"] != objectId["type"]]
        else:
            detectionShapes = [detection for detection in detectionShapes if detection.objectId["type"]
                               != objectId["type"] or detection.objectId["id"] != objectId["id"]]

        logger.debug(f"Detection IDs: {[x.objectId for x in detectionShapes]}")


async def main():
    canWebsocketFuture = asyncio.ensure_future(canWebsocket())
    irWebsocketFuture = asyncio.ensure_future(irWebsocket())

    done, pending = await asyncio.wait([canWebsocketFuture, irWebsocketFuture], return_when=asyncio.FIRST_COMPLETED)

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
                                shapeSpace = irCamera.shapeToSpace(
                                    detectionZone)
                                polygonSpace = config.Polygon(list(tuple(x) for x in shapeSpace), objectId={
                                    "type": "ir", "id": detectionZone.zoneId})
                                await showShape(polygonSpace)
                            elif jsonMessage["state"] == "End":
                                objectId = {"type": "ir",
                                            "id": detectionZone.zoneId}
                                await removeShape(objectId)


async def canWebsocket():
    global frameIDs, segmentIDs, lidars
    uri = "ws://192.168.1.58:8765"
    async with websockets.connect(uri) as ws:
        while True:
            message = await ws.recv()
            logger.debug(f"Message received: {message}")
            jsonMessage = json.loads(message)
            dataBytes = bytearray.fromhex(jsonMessage["data"])
            if jsonMessage["arbitration_id"] in frameIDs:
                # Frame message
                numDetections = int.from_bytes(dataBytes[0:1], 'little')
                objectId = {"type": str(jsonMessage["arbitration_id"]-1)}
                await removeShape(objectId)
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
                                channel, distance)
                            polygonSpace.objectId = {"type": str(
                                lidar.baseFrameIdTx), "id": channel}
                            await showShape(polygonSpace)

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

    logger.info(f"Start program...")
    asyncio.get_event_loop().run_until_complete(main())
