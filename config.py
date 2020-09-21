import xml.etree.ElementTree as ET
import xmlschema
import pprint
import uuid as UUID

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

class Drawable:
    def __init__(self, length:float, width:float, x:float, y:float):
        self.length = length
        self.width = width
        self.x = x
        self.y = y

    @property
    def length(self):
        return self._length

    @length.setter
    def length(self, length):
        if length <= 0:
            raise ValueError('Length cannot be smaller or equal to 0.')
        else:
            self._length = length

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, width):
        if width <= 0:
            raise ValueError('Width cannot be smaller or equal to 0.')
        else:
            self._width = width

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

class Brug(Drawable):
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

class Rijbaan(Drawable):
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

class Rijstrook(Drawable):
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

if __name__ == "__main__":
    tree = ET.parse('config.xml')
    root = tree.getroot()

    # for child in root:
    #     print(child.tag, child.attrib)

    brugSchema = xmlschema.XMLSchema('Brug.xsd')
    brugConfig = 'brugConfig.xml'
    if brugSchema.is_valid(brugConfig):
        brug = parseBrugData(brugSchema,brugConfig)
        # bruigConfigDict = brugSchema.to_dict('brugConfig.xml')
    # irSchema = xmlschema.XMLSchema('IR.xsd')
    lidarSchema = xmlschema.XMLSchema('Lidar.xsd')
    lidarSchema.is_valid('lidarConfig.xml')

    TiltSensorCalibration = root.find('TiltSensorCalibration')
    Parameters = TiltSensorCalibration.find('Parameters')
    CameraHeight = float(TiltSensorCalibration.get('CameraHeight'))
    TiltAngle = float(Parameters.get('TiltAngle'))
    RollAngle = float(Parameters.get('RollAngle'))
    CcdWidth = float(Parameters.get('CcdWidth'))
    CcdHeight = float(Parameters.get('CcdHeight'))
    FocalDistance = float(Parameters.get('FocalDistance'))