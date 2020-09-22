import xml.etree.ElementTree as ET
import xmlschema
import pprint
import uuid as UUID
import cameratransform as ct
import numpy as np

class DataParseError(Exception):
    """Exception raised for XML data parsing errors.

    Attributes:
        element -- element for width the error occured
        message -- explanation of the error
    """

    def __init__(self,element,message):
        self.element = element
        self.message = message
        super().__init__('XML element ' +  element + ' raised: ' + self.message)

class Point(object):
    def __init__(self, x:float, y:float):
        super().__init__()
        self.x = x
        self.y = y

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, x):
        self._x = x

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, y):
        self._y = y

    def draw(self):
        pass

class Polygon(object):
    def __init__(self, points:list):
        self.points = points

    @property
    def points(self):
        return self._points

    @points.setter
    def points(self, points):
        self._points = points

    def draw(self):
        pass

class Rectangle(Polygon):
    def __init__(self, length:float, width:float, x:float, y:float):
        self.length = length
        self.width = width
        self.x = x
        self.y = y
        points = [(x, y), (x + width, y), (x, y + length), (x + width, y + length)]
        super().__init__(points)

    @property
    def length(self):
        return self._length

    @length.setter
    def length(self, length):
        if length < 0:
            raise ValueError('Length cannot be smaller than 0.')
        else:
            self._length = length

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, width):
        if width < 0:
            raise ValueError('Width cannot be smaller than 0.')
        else:
            self._width = width

class Brug(Rectangle):
    def __init__(self, length:float, width:float, uuid:UUID.UUID, name:str = None):
        super().__init__(length, width, 0.0, 0.0)
        self.uuid = uuid
        self.name = name
        self.rijbanen = []

    @property
    def uuid(self):
        return self._uuid

    @uuid.setter
    def uuid(self, uuid):
        self._uuid = uuid
    
    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    def addRijbaan(self, rijbaan):
        self.rijbanen.append(rijbaan)

class Rijbaan(Rectangle):
    def __init__(self, brug:Brug, width:float, x:float, y:float, uuid:UUID.UUID):
        super().__init__(brug.length, width, x, y)
        self.uuid = uuid
        self.rijstroken = []
    
    @property
    def uuid(self):
        return self._uuid

    @uuid.setter
    def uuid(self, uuid):
        self._uuid = uuid

    def addRijstrook(self, rijstrook):
        self.rijstroken.append(rijstrook)

class Rijstrook(Rectangle):
    def __init__(self, rijbaan:Rijbaan, width:float, x:float, y:float, uuid:UUID.UUID, trafficType:str):
        super().__init__(rijbaan.length, width, x, y)
        self.uuid = uuid
        self.trafficType = trafficType
    
    @property
    def uuid(self):
        return self._uuid

    @uuid.setter
    def uuid(self, uuid):
        self._uuid = uuid

    @property
    def trafficType(self):
        return self._trafficType

    @trafficType.setter
    def trafficType(self, trafficType):
        self._trafficType = trafficType

def parseBrugData(brugSchema:xmlschema.XMLSchema, brugConfig:str):
    # Get dictionary
    brugConfigDict = brugSchema.to_dict(brugConfig)

    # Rijbaan breedte check
    totaleBrugBreedte = 0
    for rijbaan in brugConfigDict['rijbaan']:
        totaleBrugBreedte += rijbaan['@breedte']
        totaleRijbaanBreedte = 0
        for rijstrook in rijbaan['rijstrook']:
            totaleRijbaanBreedte += rijstrook['@breedte']
        if totaleRijbaanBreedte > rijbaan['@breedte']:
            raise DataParseError(rijbaan['@uuid'], 'Som rijstrook breedtes groter dan rijbaan breedte.')
    if totaleBrugBreedte > brugConfigDict['@breedte']:
        raise DataParseError(brugConfigDict['@uuid'], 'Som rijbaan breedtes groter dan brug breedte.')

    # Objecten aan maken
    # Brug object
    brug = Brug(brugConfigDict['@lengte'],brugConfigDict['@breedte'],brugConfigDict['@uuid'],brugConfigDict['@naam'])
    # Rijbanen aanmaken
    for rijbaan in brugConfigDict['rijbaan']:
        rb = Rijbaan(brug,rijbaan['@breedte'],0,sum(x.width for x in brug.rijbanen),rijbaan['@uuid'])
        brug.addRijbaan(rb)
        # Rijstroken aanmaken
        for rijstrook in rijbaan['rijstrook']:
            rb.addRijstrook(Rijstrook(rb,rijstrook['@breedte'],0,sum(x.width for x in rb.rijstroken)+rb.y,rijstrook['@uuid'],rijstrook['@verkeersSoort']))
    return brug

class IRCamera(Point):
    def __init__(self, x: float, y: float, cameraId: str, cam: ct.Camera):
        super().__init__(x, y)
        self.cam = cam
        self.cameraId = cameraId
        self.detectionZones = []

    @property
    def cam(self):
        return self._cam

    @cam.setter
    def cam(self,cam):
        self._cam = cam

    @property
    def cameraId(self):
        return self._cameraId

    @cameraId.setter
    def cameraId(self,cameraId):
        self._cameraId = cameraId

    def addDetectionZone(self, detectionZone):
        if len(detectionZone.points) == 0:
            detectionZone.points = self.cam.spaceFromImage(np.array(detectionZone.shapePx))
        self.detectionZones.append(detectionZone)

class IRDetectionZone(Polygon):
    def __init__(self, shapePx: list, mode: dict, zoneId: str, shape: list = []):
        super().__init__(shape)
        self.shapePx = shapePx
        self.mode = mode
        self.zoneId = zoneId

    @property
    def shapePx(self):
        return self._shapePx

    @shapePx.setter
    def shapePx(self, shapePx):
        self._shapePx = shapePx

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, mode):
        self._mode = mode

    @property
    def zoneId(self):
        return self._zoneId

    @zoneId.setter
    def zoneId(self, zoneId):
        self._zoneId = zoneId

def parseIRData(configFile: str, frameSize: tuple):
    # Parse xml
    tree = ET.parse(configFile)
    root = tree.getroot()
    # Find ressrouces
    TiltSensorCalibration = root.find('TiltSensorCalibration')
    Parameters = TiltSensorCalibration.find('Parameters')
    CameraHeight = float(TiltSensorCalibration.get('CameraHeight'))
    TiltAngle = float(Parameters.get('TiltAngle'))
    RollAngle = float(Parameters.get('RollAngle'))
    PanAngle = float(Parameters.get('PanAngle'))
    CcdWidth = float(Parameters.get('CcdWidth'))
    CcdHeight = float(Parameters.get('CcdHeight'))
    FocalDistance = float(Parameters.get('FocalDistance'))
    # Create camera object
    cam = ct.Camera(ct.RectilinearProjection(focallength_mm=FocalDistance,
                                        sensor_width_mm=CcdWidth*1000,
                                        sensor_height_mm=CcdHeight*1000,
                                        image_width_px=frameSize[0],
                                        image_height_px=frameSize[1],),
            ct.SpatialOrientation(elevation_m=CameraHeight,
                                    tilt_deg=90.0-TiltAngle,
                                    roll_deg=RollAngle,
                                    heading_deg=PanAngle))
    # Get unique camera name
    cameraName = root.find('General').find('CameraName').get('Value')
    # Create IRCamera object
    irCamera = IRCamera(0,0,cameraName,cam)
    # Find detection zones
    PedestrianPresence = root.find('PedestrianPresence')
    if PedestrianPresence is not None:
        Zones = PedestrianPresence.find('PedestrianPresence').find('Zones')
        for Zone in Zones.iter('Zone'):
            points = Zone.find('Shape').findall('Point')
            shape = list(tuple(int(value) for value in point.attrib.values()) for point in points)
            mode = Zone.find('DetectionMode').attrib
            # Create IRDetectionZone
            irDetectionZone = IRDetectionZone(shape, mode, Zone.get('ZoneId'))
            # Add zone to IRCamera
            irCamera.addDetectionZone(irDetectionZone)

    return irCamera


if __name__ == "__main__":
    

    brugSchema = xmlschema.XMLSchema('Brug.xsd')
    brugConfig = 'brugConfig.xml'
    if brugSchema.is_valid(brugConfig):
        brug = parseBrugData(brugSchema,brugConfig)
    
    # irSchema = xmlschema.XMLSchema('IR.xsd')
    irCamera = parseIRData('irConfig.xml',(320,240))

    lidarSchema = xmlschema.XMLSchema('Lidar.xsd')
    lidarSchema.is_valid('lidarConfig.xml')

