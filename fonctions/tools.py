# -*- coding: utf-8 -*-
from qgis.core import QgsVectorLayer, QgsSpatialIndex, QgsMapLayerRegistry

def findLayerByName(layers=dict, name=""):
    """
    une fonction qui permet de récupérer les couches par leur nom.
    :param name: le nom de la couche
    :return : on renvoie la classe QgsVectorLayer.
    """
    # mapLayers renvoie un dictionnaire des couches
    if not layers : layers = QgsMapLayerRegistry.instance().mapLayers()
    # on récupère la clé et la valeur
    for k,v in layers.items():
        # si le paramètre de nom est dans la valeur k
        if name in k:
            # alors on affecte la valeur à name
            name = k
    # On vérifie que la couche existe si oui on la retourne
    return layers[name]

def createMemoLayer(type="", crs=4326, name="", fields={"id":"integer"}, index="no"):
    """
    Créer une couche en mémoire en fonction des paramètres
    :param type (string): c'est le type de geometrie "point", "linestring",
                          "polygon", "multipoint","multilinestring","multipolygon"
    :param crs (int): systeme de projection CRS
    :param fields (dict): {nom_champ : type_champ(longueur)} field=name : type(length,precision)
                                                            types : "integer", "double", "string(length)"
    :param name (string): C'est le nom de la couche qui apparaitra dans la légende
    :param index (string): indique si on créer un indice spatial
    :return (QgsVectorLayer): on retourene un objet QgsVectorLayer
    """
    # on créer l'uri et on ajoute tous les champs
    uri="%s?crs=epsg:%s"%(type,crs)
    for key, value in fields.items():
        uri="%s&field=%s:%s"%(uri,key, value)
    uri="%s&index=%s"%(uri,index)
    # on créer l'objet QgsVectorLayer
    memLayer = QgsVectorLayer(uri, name, "memory")
    return memLayer

def resolveFieldIndex(layer, attr):
    """This method takes an object and returns the index field it
    refers to in a layer. If the passed object is an integer, it
    returns the same integer value. If the passed value is not an
    integer, it returns the field whose name is the string
    representation of the passed object.

    Ir raises an exception if the int value is larger than the number
    of fields, or if the passed object does not correspond to any
    field.
    """
    if isinstance(attr, int):
        return attr
    else:
        index = layer.fieldNameIndex(unicode(attr))
        if index == -1:
            raise ValueError('Wrong field name')
        return index


def values(layer=QgsVectorLayer, *attributes):
    """Returns the values in the attributes table of a vector layer,
    for the passed fields.

    Field can be passed as field names or as zero-based field indices.
    Returns a dict of lists, with the passed field identifiers as keys.
    It considers the existing selection.

    It assummes fields are numeric or contain values that can be parsed
    to a number.
    """
    ret = {}
    for attr in attributes:
        index = resolveFieldIndex(layer, attr)
        values = []
        feats = layer.getFeatures()
        for feature in feats:
            try:
                v = float(feature.attributes()[index])
                values.append(v)
            except:
                values.append(None)
        ret[attr] = values
    return ret

def spatialindex(layer=QgsVectorLayer):
    """Creates a spatial index for the passed vector layer.
    """
    idx = QgsSpatialIndex()
    for ft in layer.getFeatures():
        idx.insertFeature(ft)
    return idx