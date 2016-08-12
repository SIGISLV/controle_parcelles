# -*- coding: utf-8 -*-
import json
from qgis.core import QgsFeature

def mappingFeature(feature=QgsFeature):
    """
    create json from QgsFeature
    :param feature:
    :return: dict of feature attributes
    """
    geom = feature.geometry()
    fields = [field.name() for field in feature.fields()]
    properties=dict(zip(fields, feature.attributes()))
    return {'type': feature,
            'properties': properties,
            'geometry':geom}

def mappingGeometry(feature=QgsFeature):
    """
    create json of Wkb of geometry
    :param geometry:
    :return: json of geometry
    """
    geo = feature.geometry().exportToGeoJSON(precision=17)
    return json.loads(geo)

def compLayAttr(l1=list(), l2=list()):
    """
    Il compare les deux listes en paramètre et détecte les éléments non intersectant dans les deux sens.
    contient les identifiants qui sont dans L2 et pas dans L1.
    :param (list) l1: est la liste des identifiants de l'année antérieure (n-1)
    :param (list) l2: est la liste des identifiants de l'année actuelle (n)
    :return (tuple) : les identifiants de l1 qui n'ont pas de correspondance en l2 et les identifiant l2 qui ne sont pas dans l1
    """
    # on crée une liste de compréhension avec condition des entités de l1 qui ne sont pas dans l2
    return [feat for feat in l1 if feat not in l2]