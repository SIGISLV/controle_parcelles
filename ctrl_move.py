# -*- coding: utf-8 -*-

from qgis.core import *
from fonctions.tools import findLayerByName
from fonctions.geotraiments import mergeVectorLayer
from fonctions.att_fx import compLayAttr, mappingFeature


# Test récupération d'une couche à partir de son nom
layers = QgsMapLayerRegistry.instance().mapLayers()
layer1 = findLayerByName(layers, "parcelles_2015")
layer2 = findLayerByName(layers, "parcelles_2016")

# on sélectione une partie de la couche
layer1.setSubsetString("\"ident\" LIKE '%ZC%' OR \"ident\" LIKE '%BB%' OR \"ident\" LIKE '%AB%' OR \"ident\" LIKE '%AD%' OR \"ident\" LIKE '%AC%'")
layer2.setSubsetString("\"ident\" LIKE '%BY%' OR \"ident\" LIKE '%BB%' OR \"ident\" LIKE '%CA% OR \"ident\" LIKE '%BZ%")

# on récupère la liste des entités qui ont changées
# on récupère les features.
l1_features = layer1.dataProvider().getFeatures()
l2_features = layer2.dataProvider().getFeatures()

# On récupère les valeurs au format json dans un dictionnaire
l1_json = {mappingFeature(feature)['properties']['ident']: mappingFeature(feature) for feature in l1_features}
l2_json = {mappingFeature(feature)['properties']['ident']: mappingFeature(feature) for feature in l2_features}

# On créer les listes de valeurs pour comparer les valeurs
# de layer1 à layer2
l1_ident = [feature['properties']['ident'] for feature in l1_json.values()]
l2_ident = [feature['properties']['ident'] for feature in l2_json.values()]

# on cherche les attributs qui n'intersectent pas.
l1_l2_non_intersect = compLayAttr(l1_ident, l2_ident)
l2_l1_non_intersect = compLayAttr(l2_ident, l1_ident)

# fusion des parcelles entre elles en utilisant shapely
layer_p2015_fusion_mem = mergeVectorLayer(layer1, fusion_field= "section", fusion=True, out_layer_name="parcel_fusion_2015")
layer_p2016_fusion_mem = mergeVectorLayer(layer2, fusion=True, fusion_field= "section", out_layer_name="parcel_fusion_2016")

# QgsMapLayerRegistry.instance().addMapLayers([layer_p2015_fusion_mem, layer_p2016_fusion_mem])
print "End"
