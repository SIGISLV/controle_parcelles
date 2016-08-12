# -*- coding: utf-8 -*-
"""
***************************************************************************
    ControleParcelle.py
    ---------------------
    Date                 : Juillet 2016
    Copyright            : (C) 2016 by Lewis Villierme
    Email                : lewisvillierme at gmail dot com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Lewis Villierme'
__date__ = 'Juillet 2016'
__copyright__ = '(C) 2016, Lewis Villierme'

import os
import errno
import tempfile

from PyQt4.QtCore import QVariant

from qgis.core import QgsMapLayerRegistry, QgsVectorLayer, QgsField, QgsGeometry, QgsFeature, QgsVectorDataProvider

from fonctions.tools import findLayerByName
from fonctions.att_fx import mappingFeature, compLayAttr
from fonctions.geotraiments import creerIndiceSpatial, Relation, IntersectSurface, SpatialIndexor


def creer_dossier(path=""):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
    except WindowsError as w:
        print "le chemin du répertoire est incorrecte :\n{}".format(w)


def creer_feature(geom=QgsGeometry, *args):
    """
    Creer une entité avec les champs passer en paramètre
    :param geom:
    :param fields:
    :return:
    """
    feat = QgsFeature()
    feat.setGeometry(geom)
    feat.setAttributes([value for value in args])
    return feat


def maj_feature(feature, **kwargs):
    """
    met à jour la
    :param feature:
    :param kargs:
    :return:
    """
    for field_name, attr_value in kwargs.items():
        feature[field_name] = "{}, {}".format(feature[field_name], attr_value)
    return feature


class ArchiveLayer():
    def __init__(self, layer=QgsVectorLayer, annee=0):
        self.layer = layer
        self.annee = annee
        self.__pr__ = layer.dataProvider()
        self.__no_ident__ = {}
        self.__moved__ = {}
        self.__division__ = {}
        self.__union__ = {}
        self.__to_dp__ = {}
        self.__from_dp__ = {}
        self.__rename__ = {}
        self.__log_path__ = ""
        self.__all_dict__ = {"sans identifiant" : self.__no_ident__, "déplacé" : self.__moved__,
                             "unis" : self.__union__, "divisé" : self.__division__,
                             "renommé" : self.__rename__, "passé au domaine public" : self.__from_dp__,
                             "venue du domaine public" : self.__to_dp__}

    def getStat(self):
        """
        calcul le nombre d'entite détecter et retourne une liste de string
        :return:
        """
        line=""
        lstat=[]
        for nom, d in self.__all_dict__.items():
            line = "{} : {}".format(nom, len(d))
            lstat.append(line)
        return lstat

    def writeLog(self, path):
        """
        Ecrit un fichier de log
        :return:
        """
        logHead = """\n
        Résumé statistique de la comparaison de parcelles
        \n
        """
        os.chdir(path)
        # récupérer toutes les informations sur les entités
        with open("log.log", mode='w') as log:
            log.write(logHead)
            for stat in self.getStat():
                log.write("{} \n".format(stat))
        return os.path.join(path, "log.log")

    def getAllFeatures(self):
        """
        Récupère toutes les entités de chaque dictionnaire
        :return: liste de toutes les entités
        """
        allFeatures=[]
        for name, d in self.__all_dict__.items():
            for ident, feature in d:
                allFeatures.append(feature)
        return allFeatures

    def importFeature(self, import_layer=QgsVectorLayer):
        """
        importe les données dans la couche donnée en paramètre.
        :return:
        """
        caps = import_layer.dataProvider().capabilities()
        # on récupère les anciennes entités
        features = self.__pr__.getFeatures()
        # on étends la liste aux entités détecter
        features.extend(self.getAllFeatures())
        # on utilise le provider pour la mise à jour
        exp_layer_pr = import_layer.dataProvider()
        # on ajoute toutes les entités si c'est possible.
        if caps & QgsVectorDataProvider.AddFeatures:
            exp_layer_pr.addFeatures(features)
        # on met à jour la couche
            import_layer.updateExtents()
        else:
            print "impossible de mettre à jour {}".format(import_layer.name())
        return import_layer

    def __format_feature__(self, feat, ident, dict={}):
        """
        Une méthode qui format les entités
        :param kwargs:
        :return:
        """
        feat["annee"] = self.annee

        if len(ident)==12:
            feat["num"] = int(ident[8:])
            feat["ident"] = ident
        else:
            feat["num"] = None
            feat["ident"] = None

        dict.pop("ident")

        # on cherche les autres nom de champs
        for field_name, value in dict.items():
            try:
                feat[field_name]=value
            except KeyError as e:
                pass
        return feat

    def __add_feature__(self, ident="", feature=QgsFeature, dict_to_add={}, **kwargs):
        """
        Une focntion generique pour l'ajout d'une entité qui soit présente ou non dans le dictionnaire de donnée
        :param kargs:
        :return:
        """
        feature = self.__format_feature__(feature, ident, kwargs)
        # si la variable "value" est passé en paramètre alors on demande une mise à jour
        if kwargs["modify"]:
            # on recupère toute les valeurs de kargs pour plus de lisibilité
            attr = kwargs["attribute"]
            value = kwargs["value"]
            # on récupère l'ancienne valeur de l'entité
            old_value = dict_to_add[ident][attr]
            # met à jour l'entité
            dict_to_add[ident][attr] = "{},{}".format(old_value, value)
        # on ajoute tout simplement une entrée au dictionnaire
        else:
            dict_to_add[ident] = feature
        return self

    def addNoIdent(self, feature):
        """
        Ajoute les entités au dictionnaire des entité qui n'ont pas d'identifiants
        :param feature:
        :return:
        """
        self.__add_feature__(feature=feature, dict_to_add=self.__no_ident__,
                             ident="")

    def addMoved(self, feature, ident):
        """
        Ajoute les entités qui ont bougé.
        :param feature: (QgsFeature) c'est l'entité qui a bougé
        :param ident: (string) représente l'identifiant de l'entité
        :param resultat: (string) les
        :param modify:
        :return:
        """
        self.__add_feature__(feature=feature, dict_to_add=self.__moved__,
                                 ident=ident,
                                 cause="Deplacer",
                                 modify=False)

    def addDivision(self, feature, ident, resultat):
        """
        Ajoute l'entité mère de la division à la couche archive
        :param feature:
        :param ident:
        :return:
        """
        if ident in self.__division__: modify=True
        self.__add_feature__(feature=feature, ident=ident, dict_to_add=self.__division__,
                             resultat=resultat,
                             cause="Division",
                             modify=modify)

    def addUnion(self, feature, ident, resultat):
        """
        Ajoute l'entité fille de l'union à la couche archive
        :param feature:
        :param ident:
        :param resultat:
        :return:
        """
        self.__add_feature__(ident=ident, feature=feature, dict_to_add=self.__union__,
                             resultat=resultat,
                             cause="Union")

    def addRename(self, feature, ident, resultat):
        """
        Ajoute l'entité qui a été renommé à la couche archive
        :param feature:
        :param ident:
        :param resultat:
        :return:
        """
        self.__add_feature__(ident=ident, feature=feature, dict_to_add=self.__rename__,
                             cause="Renommer",
                             resultat=resultat)

    def addToDP(self, feature, ident):
        """
        Ajoute les entités qui sont passé au DP
        :param feature:
        :param ident:
        :return:
        """
        self.__add_feature__(ident=ident, feature=feature, dict_to_add=self.___to_dp__,
                             cause="DP")
    def addFromDP(self, feature, ident):
        """
        Ecrit dans le fichier de log qu'elle est apparut
        :param feature:
        :param ident:
        :return:
        """
        # ecrire les services log
        self.__add_feature__(ident=ident, feature=feature, dict_to_add=self.__from_dp__)

def main(layer_ref=QgsVectorLayer, annee="", layer_comp=QgsVectorLayer, arch_layer=QgsVectorLayer):
    """

    :param layer_ref:
    :param annee:
    :param layer_comp:
    :param output:
    :return:
    """
    # créer une class ArchiveLayer
    archi_layer = ArchiveLayer(arch_layer)

    # On créer le dossier temp
    temp_folder = tempfile.mkdtemp(prefix="ctrlParcelles")


    # on récupère les features.
    l1_features = layer_ref.dataProvider().getFeatures()
    l2_features = layer_comp.dataProvider().getFeatures()
    lyr_out_vpr = output.dataProvider()

    # On récupère la liste des parcelles avec en clé l'identifiant de la parcelle.
    l1_json = {mappingFeature(feature)['properties']['ident']: mappingFeature(feature) for feature in l1_features}
    l2_json = {mappingFeature(feature)['properties']['ident']: mappingFeature(feature) for feature in l2_features}

    # controle 1 : On cherche une entité qui n'a pas d'identifiant.
    list_no_ident =[]
    for json in [l1_json, l2_json]:
        for ident, feat in json:
            if len(ident)!=12:
                no_id_feat = creer_feature(feat.geometry(),
                                           num=None,
                                           cause='identifiant manquant',
                                           ident=None, resultat=None,
                                           annee=annee)
                list_no_ident.append(no_id_feat)
    # On ajoute à la classe archilayer les entités qui n'ont pas d'identifiant
    archi_layer.addNoIdent(list_no_ident)

    # On créer les listes de valeurs pour comparer les valeurs
    # de layer_old à layer_new
    l1_ident = [feature['properties']['ident'] for feature in l1_json.values()]
    l2_ident = [feature['properties']['ident'] for feature in l2_json.values()]

    # on cherche les attributs qui n'intersectent pas
    l1_l2_non_intersect = compLayAttr(l1_ident, l2_ident)
    l2_l1_non_intersect = compLayAttr(l2_ident, l1_ident)

    # on cherche les entités qui sont disponible dans l'année n-1 et pas dans l'année n
    # création d'indice spatial
    index_spatial = SpatialIndexor(layer_comp)
    index_spatial.InsertFeature()
    # on utilise un dictionnaire pour retrouver une entité par son identifiant.
    list_union_division={}
    # on cherche les parcelles n-1 qui intersectent avec les parcelles n
    for ident in sorted(l1_l2_non_intersect):
        f1 = l1_json[ident]
        hits = index_spatial.getCandidats(f1)
        for f2 in hits:
            if f1.geometry().buffer(0.1).contains(f2.geometry()):
                if ident not in list_union_division:
                    feat = creer_feature(f1.geometry(),
                                         num=int(ident[8:]),
                                         cause="Division",
                                         ident=ident,
                                         resultat=mappingFeature(f2)['properties']['ident'],
                                         annee=annee)
                    list_union_division[ident] = feature
                elif ident in list_union_division:
                    list_union_division[ident] = maj_feature(list_union_division[ident])
                rel = "F1 contient F2"

            elif f2.geometry().buffer(0.1).contains(f1.geometry()):
                feat = creer_feature(f1.geometry(),
                                     num=int(ident[8:]),
                                     cause="Union",
                                     ident=ident,
                                     resultat=mappingFeature(f2)['properties']['ident'],
                                     annee=annee)
                rel = "F2 contient F1"

if __name__=="__console__":
    layer_ref = findLayerByName("pci_parcelle_2015_PDC")
    layer_comp = findLayerByName("pci_parcelle_2016_PDC")
    output = QgsVectorLayer(r'c:\temp\test', "parcelle_archive", "ogr")
    main(layer_ref=layer_ref, annee=2013, layer_comp=layer_comp, archive_layer=output)