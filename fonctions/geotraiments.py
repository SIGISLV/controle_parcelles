# -*- coding: utf-8 -*-

from shapely import speedups
if speedups.available: speedups.enable()
from shapely.geometry import shape
from shapely.wkb import loads
from shapely.wkt import loads as wktLoads
from shapely.ops import unary_union

from PyQt4.QtCore import QVariant
from PyQt4.QtGui import QColor


from qgis.core import QgsFeature, QgsMapLayerRegistry, QgsVectorLayer, QgsSpatialIndex, QgsMapLayer, QGis, QgsGeometry,\
                      QgsFeatureRequest, QgsField, QgsVectorDataProvider
from qgis.utils import iface

from fonctions.tools import findLayerByName
from fonctions.att_fx import mappingFeature, compLayAttr

import timeit
import uuid

def __qgsFeatureToShapeFeature__(feature=QgsFeature):
    """
    Convertit la classe QgsFeature en classe shapely Shape
    :param feature QgsFeature:
    :return: Shape
    """
    shp = shape(wktLoads(feature.geometry().exportToWkt()))
    return shp

def selectFeatureByAttributs(layer=QgsVectorLayer, field="", value=""):
    """
    Applique une selection par expression sur une couche et renvoie la liste des entités
    :param layer:
    :param exp:
    :return: a list of feature from the expression
    """
    # on construit l'expression
    exp = "\"%s\" LIKE '%s'".encode()%(field.encode(),"%"+value+"%".encode())
    # On met en place l'expression

    # on créer la liste des entités
    list_features = [feature for feature in layer.getFeatures(QgsFeatureRequest().setFilterExpression(exp))]
    # On vide l'expression
    layer.setSubsetString("")
    return list_features

def extractAsSingle(geom=QgsFeature):
    """
    Extrait les géométries multiples d'une couche.
    :param geom: une classe Qgis
    :return:
    """
    multiGeom = QgsGeometry()
    geometries = []
    if geom.type() == QGis.Point:
        if geom.isMultipart():
            multiGeom = geom.asMultiPoint()
            for i in multiGeom:
                geometries.append(QgsGeometry().fromPoint(i))
        else:
            geometries.append(geom)
    elif geom.type() == QGis.Line:
        if geom.isMultipart():
            multiGeom = geom.asMultiPolyline()
            for i in multiGeom:
                geometries.append(QgsGeometry().fromPolyline(i))
        else:
            geometries.append(geom)
    elif geom.type() == QGis.Polygon:
        if geom.isMultipart():
            multiGeom = geom.asMultiPolygon()
            for i in multiGeom:
                geometries.append(QgsGeometry().fromPolygon(i))
        else:
            geometries.append(geom)
    return geometries

def duplicateInMemory(layer, newName='', addToRegistry=False, addOldFeatures=False):
    """Return a memory copy of a layer

    layer: QgsVectorLayer that shall be copied to memory.
    new_name: The name of the copied layer.
    add_to_registry: if True, the new layer will be added to the QgsMapRegistry

    Returns an in-memory copy of a layer.
    """
    if newName is '':
        newName = layer.name() + ' (Memory)'

    if layer.type() == QgsMapLayer.VectorLayer:
        geomType = layer.geometryType()
        if geomType == QGis.Point:
            strType = 'Point'
        elif geomType == QGis.Line:
            strType = 'Line'
        elif geomType == QGis.Polygon:
            strType = 'Polygon'
        else:
            raise RuntimeError('Layer is whether Point nor Line nor Polygon')
    else:
        raise RuntimeError('Layer is not a VectorLayer')

    crs = layer.crs().authid().lower()
    myUuid = unicode(uuid.uuid4())
    uri = '%s?crs=%s&index=yes&uuid=%s' % (strType, crs, myUuid)
    memLayer = QgsVectorLayer(uri, newName, 'memory')
    memProvider = memLayer.dataProvider()

    provider = layer.dataProvider()
    fields = provider.fields().toList()
    memProvider.addAttributes(fields)
    memLayer.updateFields()

    if addOldFeatures:
        for ft in provider.getFeatures():
            memProvider.addFeatures([ft])

    if addToRegistry:
        if memLayer.isValid():
            QgsMapLayerRegistry.instance().addMapLayer(memLayer)
        else:
            raise RuntimeError('Layer invalid')

    return memLayer

def mergeVectorLayer(layer=QgsVectorLayer, fusion_field="", fusion=False, out_layer_name="Test"):
    """
    fusionne les entités entre elles en fonction (ou pas) d'un champ de fusion.
    :param
        layer (QgsVectorLayer) : la couche Qgis à partir de la laquelle sera fait la fusion.
        fusion_field (string) : le champ sur lequel se basera la fusion.
        fusion (boolean) : faire ou pas la fusion.
        out_layer_name (string) : le nom de la couche en sortie

    :return out_layer (QgsVectorLayer memory) : une couche en mémoire de la fusion.
    """
    # On duplique la couche d'entrée pour créer une couche avec les mêmes champs mais pas les entités.
    out_layer = duplicateInMemory(layer, out_layer_name, addToRegistry=False, addOldFeatures=False)
    # c'est notre fournisseur de données
    vpr_out_layer = out_layer.dataProvider()
    # On récupère les noms des champs
    vpr_out_fields = vpr_out_layer.fields()
    # la liste des entités qui recevra les entités
    list_features_to_add = []
    # le dictionnaire pour la fusion
    feature_fusion_list = {}

    # Faire des listes des valeurs servant à la fusion.
    if fusion:
        set_id = set([mappingFeature(feature)['properties'][fusion_field] for feature in layer.getFeatures()])
        for i in set_id:
            feature_fusion_list[i]=selectFeatureByAttributs(layer, fusion_field, i)
    if not fusion:
        feature_fusion_list[0]=vpr_out_layer.getFeatures()

    # On parcours les dictionnaire en récupérant les valeurs et les clés
    for key, list_fusion in feature_fusion_list.items():
        # On fusion les entités qui ont été transformer en wkb.
        # La fusion est rapide elle dépend de shapely
        union_geom = unary_union([loads(feature.geometry().asWkb()) for feature in list_fusion])
        # on recupère les géométries pour qgis.
        union_qgs_geometry = QgsGeometry().fromWkt(union_geom.wkt)
        # extraire toute les parties du polygon
        geom = extractAsSingle(union_qgs_geometry)
        for g in geom:
            feat = QgsFeature(vpr_out_fields)
            feat.setGeometry(g)
            if fusion:
                feat[fusion_field]=key
            list_features_to_add.append(feat)

    # On met à jour la couche avec les nouvelles entités
    vpr_out_layer.addFeatures(list_features_to_add)
    out_layer.updateExtents()

    # On supprime le data provider
    del vpr_out_layer
    # On retourne la couche
    return out_layer

def creerIndiceSpatial(layer=QgsVectorLayer):
    """
    créer un indice spatial sur la couche donnée en pramètre.
    :param layer (QgsVectorlayer): La couche qui sera indexée
    :return (tuple): La classe d'indice spatiale et le dictionnaire
    """
    # on récupère tous les attributs des features
    all_attrs = layer.pendingAllAttributesList()
    # on sélectionne tous les entités
    layer.select(all_attrs)
    # On créé le dictionnaire avec les attributs
    all_features = {feature.id():feature for feature in layer.getFeatures()}
    # on instancie l'objet d'indice spatiale de Qgis
    idx = QgsSpatialIndex()
    # on insère toute les entités
    for feature in all_features.values():
        idx.insertFeature(feature)
    # on retourne les éléments
    return idx, all_features

class SpatialIndexor():
    def __init__(self, layer=QgsVectorLayer):
        """
        contructeur de la classe.
        :param layer: La couche vecteur sur laquelle sera calculer notre indice spatiale.
        """
        self.__dict_idx_feat__={feature.id():feature for feature in layer.dataProvider().getFeatures()}
        self.__spatial_idx__ = QgsSpatialIndex()

    def InsertFeature(self):
        """
        Ajoute les features à l'index spatial
        :return: MAJ de __spatial_idx__
        """
        for key, feature in self.__dict_idx_feat__.items():
            self.__spatial_idx__.insertFeature(feature)
        return self

    def __calculDistSurf__(self,feat1=QgsFeature, feat2=QgsFeature):
        """
        Calcul la distance surfacique entre 2 entité
        :param feat1: entité 1
        :param feat2: entité 2
        :return: un indice entre 0 et 1. 0 : il sont similaire. 1 : ils sont différents
        """
        surface_intersection = feat1.geometry().intersection(feat2.geometry()).area()
        surface_union = feat1.geometry().combine(feat2.geometry()).area()
        return 1-surface_intersection/surface_union

    def getBestCandidat(self, feature=QgsFeature):
        """
        Cherche à partir des features qui sont dans la bbox.
        :return: une liste de candidats
        """
        # on met en place les variable qui nous aideront à choisir le meilleur candidat
        best_hit = None
        old_ds = 1

        # on créer la liste des candidatas
        hits = self.getCandidats(feature)
        # on parcours la liste des candidats
        for hit in hits:
            new_ds = self.__calculDistSurf__(feature, hit)
            # on cherche la distance surfacique la plus proche de 0
            if new_ds < old_ds:
                best_hit = hit
                old_ds = new_ds
        return best_hit

    def getCandidats(self, feature=QgsFeature):
        """
        Cherche à partir des features qui sont dans la bbox ceux qui touchent la
        :return: une liste de candidats
        """
        # on met en place les variable qui nous aideront à choisir le meilleur candidat
        candidats =[]

        # on créer la liste des candidats
        hits = self.__spatial_idx__.intersects(feature.geometry().boundingBox())
        # on parcours la liste des candidats
        for hit in hits:
            # on cherche son
            hit_feat = self.__dict_idx_feat__[hit]
            if feature.geometry().touches(hit_feat):
                candidats.append(hit_feat)
        return candidats

def IntersectSurface(feat1=QgsFeature, feat2=QgsFeature):
    """
    opère une intersection spatiale entre les deux entités et calcul la surface commune aux deux entités.
    Cette valeur est calculée entre la première entité et la deuxième et non l'inverse
    :param feat1:
    :param feat2:
    :return: un réel de la surface qui intersecte
    """
    f1 = __qgsFeatureToShapeFeature__(feat1)
    f2 = __qgsFeatureToShapeFeature__(feat2)
    return f1.intersection(f2).area

def UnionSurface(feat1=QgsFeature, feat2=QgsFeature):
    """
    Calcule la surface total d'une union de deux entité
    :param feat1: entité 1
    :param feat2: entité 2
    :return: une superficie
    """
    f1= __qgsFeatureToShapeFeature__(feat1)
    f2=__qgsFeatureToShapeFeature__(feat2)
    return f1.union(f2).area

def CalculDistanceSurface(feat1=QgsFeature, feat2=QgsFeature):
    """
    Calcule la distance surfacique entre deux entité. Une distance proposé par
    :param feat1: entité qgis
    :param feat2: entité qgis
    :return: une distance surfacique entre deux entité tend vers 0 similaire tend vers 1 différent
    """
    return 1-IntersectSurface(feat1, feat2)/UnionSurface(feat1, feat2)

def ControleMouvement(layer_ref, layer_comp):
    """
    Permet de dire si une entité à bouger ou changer. Il calcul notement la distance surfacique.
    :param layerRef: la couche de l'année n-1.
    :param layerComp: la couche de l'année actuelle.
    :return: Une liste des features qui ont bougés
    """
    # On créer la liste des entités qui ont bougé
    list_out = []
    # on créer le fournisseur d'entité
    vpr_layer_ref = layer_ref.dataProvider()
    caps = vpr_layer_ref.capabilities()
    if "statut" not in [field.name() for field in layer_ref.pendingFields()]:
        if caps & QgsVectorDataProvider.AddAttributes:
            vpr_layer_ref.addAttributes([QgsField("statut", QVariant.String)])
            layer_ref.updateFields()
        else:
            print "Impossible d'ajouter le champ status"

    # On créer l'indice spatial sur la couche de comparaisson
    ids_layer_comp = SpatialIndexor(layer_comp)
    ids_layer_comp.InsertFeature()

    # On parcours les entités de la couche année n-1
    for feature in vpr_layer_ref.getFeatures():
        # On cherche les candidats de l'entité
        candidat = ids_layer_comp.getBestCandidat(feature)
        # On calcul la distance surfacique si il n'est pas égale à 0 il a bougé
        if round(CalculDistanceSurface(feature, candidat), 3) > 0.01:
            print CalculDistanceSurface(feature, candidat)
            print("feat ref = {} et feat candidat = {}".format(feature.id()-1 ,candidat.id()-1))
            # On affecte au champ statut la valeur "déplacer"
            try:
                feature.setAttribute('statut',"deplacer")
            except KeyError:
                print "le champ status n'existe pas."
            list_out.append(feature)
    return list_out

def Relation(feat1=QgsFeature, feat2=QgsFeature, buffer=0.005):
    """
    Cherche à savoir quelle entité est contenue dans quelle entité
    :param feat1:
    :param feat2:
    :param buffer :
    :return: un réel de la surface qui intersecte
    """
    f1 = __qgsFeatureToShapeFeature__(feat1)
    f2 = __qgsFeatureToShapeFeature__(feat2)
    # On test si f1 contient f2
    f1cf2 = f1.buffer(buffer).contains(f2)
    return f1cf2

if __name__ == "__console__":
    # Test récupération d'une couche à partir de son nom
    layers = QgsMapLayerRegistry.instance().mapLayers()
    layer1 = findLayerByName(layers, "parcelles_2015")
    layer2 = findLayerByName(layers, "parcelles_2016")
    """
    # on sélectione une partie de la couche
    layer1.setSubsetString(
        "\"ident\" LIKE '%ZC%' OR \"ident\" LIKE '%BB%' OR \"ident\" LIKE '%AB%' OR \"ident\" LIKE '%AD%' OR \"ident\" LIKE '%AC%'")
    layer2.setSubsetString(
        "\"ident\" LIKE '%BY%' OR \"ident\" LIKE '%BB%' OR \"ident\" LIKE '%CA%' OR \"ident\" LIKE '%BZ%'")
    """
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
    layer_p2015_fusion_mem = mergeVectorLayer(layer1, fusion_field="section", fusion=True,
                                              out_layer_name="parcel_fusion_2015")
    layer_p2016_fusion_mem = mergeVectorLayer(layer2, fusion=True, fusion_field="section",
                                              out_layer_name="parcel_fusion_2016")

    QgsMapLayerRegistry.instance().addMapLayers([layer_p2015_fusion_mem, layer_p2016_fusion_mem])

    l_move = ControleMouvement(layer_p2015_fusion_mem, layer_p2016_fusion_mem)
    iface.mapCanvas().setSelectionColor(QColor("red"))
    layer_p2015_fusion_mem.setSelectedFeatures([feat.id() for feat in l_move])

    print "End"