import websocket
import logging
import json
import config
import xmlschema

logger = logging.getLogger('websockets')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


class DetectionFrame(object):
    def __init__(self, baseID: int, numDetections: int, maxNumDetections: int):
        super().__init__()
        self.baseID = baseID
        self.numDetections = numDetections
        self.detections = [None] * maxNumDetections

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


def on_message(ws, message):
    global detectionZones
    logger.debug(f"Message received: {message}")
    jsonMessage = json.loads(message)
    if jsonMessage["type"] == "PedestrianPresence":
        if jsonMessage["state"] == "Begin":
            detectionZones[int(jsonMessage["zondId"])-1] = True
        elif jsonMessage["state"] == "End":
            detectionZones[int(jsonMessage["zondId"])-1] = False


def on_open(ws):
    logger.debug(f"Opening websocket")
    logger.debug(f"Creating request")
    request = json.dumps({"messageType": "Subscription", "subscription": {
                         "type": "Event", "action": "Subscribe"}})
    logger.debug(f"Sending request: {request}")
    ws.send(request)


def canMessageParse(ws, message):
    global frameIDs, segmentIDs, detectionFrame, lidars
    # logger.debug(f"Message received: {message}")
    jsonMessage = json.loads(message)
    dataBytes = bytearray.fromhex(jsonMessage["data"])
    if jsonMessage["arbitration_id"] in frameIDs:
        numDetections = int.from_bytes(dataBytes[0:1], 'little')
        detectionFrame = DetectionFrame(
            jsonMessage["arbitration_id"]-1, numDetections, 8)
    elif jsonMessage["arbitration_id"] in segmentIDs:
        # distance
        distance = int.from_bytes(dataBytes[0:2], 'little')
        # valid
        valid = int.from_bytes(dataBytes[4:6], 'little')
        # channel number
        channel = int.from_bytes(dataBytes[6:8], 'little')
        if valid == 1:
            detectionFrame.detections[channel] = distance

            for lidar in lidars:
                if lidar.baseFrameIdTx == jsonMessage["arbitration_id"]-2:
                    logger.debug(f"{lidar.beamToCartesian(channel, distance).points}")
        else:
            detectionFrame.detections[channel] = -1
        if len(list(x for x in detectionFrame.detections if x is not None)) == detectionFrame.numDetections:
            logger.debug(
                f"{detectionFrame.baseID} : {detectionFrame.detections}")


if __name__ == "__main__":
    logger.debug(f"Start config...")
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

    logger.debug(f"All config done!")

    frameIDs = []
    segmentIDs = []
    for lidar in lidars:
        frameIDs.append(lidar.baseFrameIdTx+1)
        segmentIDs.append(lidar.baseFrameIdTx+2)

    detectionZones = [False]

    # baseFrameID = 1872
    detectionFrame = None

    # ws = websocket.WebSocketApp(
    #     'ws://10.0.0.26:13314/api/subscriptions', on_message=on_message, on_open=on_open)
    # ws.run_forever()

    wsCan = websocket.WebSocketApp(
        'ws://192.168.1.58:8765', on_message=canMessageParse)
    wsCan.run_forever()
