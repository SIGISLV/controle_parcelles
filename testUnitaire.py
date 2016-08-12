# -*- coding: utf-8 -*-

from qgis.core import *
from fonctions.tools import findLayerByName
from fonctions.att_fx import mappingFeature, compLayAttr
from fonctions.geotraiments import creerIndiceSpatial, Relation, IntersectSurface

# test 1
# On récupère la couche à partir de son nom
layers = QgsMapLayerRegistry.instance().mapLayers()
layer1 = findLayerByName(layers, "pci_parcelle_2015_PDC")
layer2 = findLayerByName(layers, "pci_parcelle_2016_PDC")

# on sélectione une partie de la couche
layer1.setSubsetString("\"ident\" LIKE '%AI%'")
layer2.setSubsetString("\"ident\" LIKE '%AI%' OR \"ident\" LIKE '%BL%'")

# on récupère les features.
l1_features = layer1.dataProvider().getFeatures()
l2_features = layer2.dataProvider().getFeatures()

# On récupère les valeurs au format json dans un dictionnaire
l1_json = {mappingFeature(feature)['properties']['ident']:mappingFeature(feature) for feature in l1_features}
l2_json = {mappingFeature(feature)['properties']['ident']:mappingFeature(feature) for feature in l2_features}

# On créer les listes de valeurs pour comparer les valeurs
# de layer1 à layer2
l1_ident = [feature['properties']['ident'] for feature in l1_json.values()]
l2_ident = [feature['properties']['ident'] for feature in l2_json.values()]

# on cherche les attributs qui n'intersectent pas
l1_l2_non_intersect = compLayAttr(l1_ident, l2_ident)
l2_l1_non_intersect = compLayAttr(l2_ident, l1_ident)

print ("""la liste des parcelles qui sont dans l1 et pas dans l2 : %s \nla liste des parcelles qui sont dans l2 et pas /
dans l1 : %s""" %(l1_l2_non_intersect, l2_l1_non_intersect))

# une liste à vider pour comparer
l2l1ni_to_pop =[f for f in l2_l1_non_intersect]

# création d'indice spatial
index, dict_layer_index = creerIndiceSpatial(layer2)

# on cherche les parcelles n-1 qui intersectent avec les parcelles n
for ident in sorted(l1_l2_non_intersect):
    # print l1_json
    hits = index.intersects(l1_json[ident]['type'].geometry().boundingBox())
    hitsIdent=[mappingFeature(dict_layer_index[h])['properties']['ident'] for h in hits]
    for hit in sorted(hits):
        f1 = l1_json[ident]['type']
        f2 = dict_layer_index[hit]
        f1_ident = ident
        f2_ident = mappingFeature(f2)['properties']['ident']
        f1f2area = IntersectSurface(feat1=f1, feat2=f2)
        f2f1area = IntersectSurface(feat1=f2, feat2=f1)

        # on regarde dans les deux sens
        # Es ce que F1 contient F2
        relf1f2 = Relation(feat1=f1, feat2=f2)
        # Es ce que F2 contient F1
        relf2f1 = Relation(feat1=f2, feat2=f1)

        # On test si F1 contient F2
        if relf1f2:
             rel = "F1 contient F2"
             try:
                idx = l2l1ni_to_pop.index(f2_ident)
                l2l1ni_to_pop.pop(idx)
             except ValueError:
                print ("%s est deja detecter"%f2_ident)

        # On test si F2 contient F1
        elif relf2f1:
             rel = "F2 contient F1"
             try:
                idx = l2l1ni_to_pop.index(f2_ident)
                l2l1ni_to_pop.pop(idx)
             except ValueError:
                 print ("%s est deja detecter"%f2_ident)
        else:
             rel = "F1 et F2 ne se touchent pas"

        if relf2f1 or relf1f2:
             print ("F1 : %s F2 : %s F1/F2 : %s"%(f1_ident, f2_ident, rel))

l1,l2 = compLayAttr(l2_l1_non_intersect, l2l1ni_to_pop)
print ("l1 (longueur):%s \n l2(longueur):%s"%(len(l2_l1_non_intersect), len(l2l1ni_to_pop)))