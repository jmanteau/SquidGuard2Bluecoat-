#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
 Convert UT1 blacklist for use with Bluecoat
 Auteur: Julien Manteau <jmanteau@gmail.com>

"""
# import nécessaire
import logging
import logging.handlers
import os
# import
import sys, time
import urllib
import tarfile
import traceback


# variables globales
nomScript = os.path.basename(sys.argv[0].replace(".py", ""))
PATH_LOG = os.path.join(os.getcwd(), "log")
if not os.path.isdir(PATH_LOG):
    os.makedirs(PATH_LOG)
release = "1"

URL_BLACKLIST = "http://cri.univ-tlse1.fr/blacklists/download/blacklists.tar.gz"
BLACKLIST_FOLDER = "."


def download(url, folder=os.getcwd(), journal=None):
    try:
        location = os.path.join(folder, url.split('/')[-1])
        if os.path.isfile(location):
            timefile = os.path.getmtime(location)
            curtime = time.mktime(time.localtime())
            timediff = float(curtime) - float(timefile)
            hours_elapsed = timediff / (60.0 * 60)
            if journal:
                journal.info("Fichier accédé il y a %f h" % hours_elapsed)
            if hours_elapsed > 30:
                urllib.urlretrieve(url, location)
                return location
            else:
                if journal:
                    journal.info(
                        "Blacklist MAJ il y a moins de 24h (%f h). Utilisation de la copie locale" % hours_elapsed)
                return location
        else:
            urllib.urlretrieve(url, location)
            return location
    except:
        traceback.print_exc(file=sys.stdout)
        return False


class SquidACLupdate:
    def __init__(self, journal):
        self.journal = journal

    def create_blacklist(self):

        self.journal.info("Lancement de la création des BLs")

        # fichier de destination au format BL Bluecoat   
        name = "blacklistBC.txt"
        self.journal.info("Création de %s" % name)
        destination = open(os.path.join(BLACKLIST_FOLDER, name), 'wb')

        domainsalreadyseen = set()

        #on parcourt les categories de la BL par dossier
        for categorie in os.listdir(os.path.join(os.getcwd(), "blacklists")):
            dircategorie = os.path.join(os.getcwd(), "blacklists", categorie)

            # est une categorie de blacklist
            if os.path.isdir(dircategorie):
                self.journal.info("Ajout de categorie %s" % categorie)
                # entete de categorie bluecoat
                destination.write("define category UT1_%s\n" % categorie)

                # on traite les urls
                blurl = os.path.join(os.getcwd(), "blacklists", categorie, "urls")
                if os.path.isfile(blurl):
                    self.addtoblacklistURL(blurl, destination, domainsalreadyseen)

                # puis les domains
                bldomain = os.path.join(os.getcwd(), "blacklists", categorie, "domains")
                if os.path.isfile(bldomain):
                    self.addtoblacklistDomain(bldomain, destination, domainsalreadyseen)

                destination.write("end \n \n")
        destination.close()

        self.journal.info("Création des blacklist finies")

    def addtoblacklistURL(self, file_univ, file_dest, domainsalreadyseen):
        listeurl = open(file_univ, 'rb').readlines()
        listeurlok = set()
        del_char = ["..", "&", "="]
        #on parcourt les urls pour les valider
        for url in listeurl:
            # on tronque après le ? (chaine apres ignorée par BC)
            urlok = url.strip().split("?")[0]

            # on n'ajoute pas les url contenant les char interdits
            found = False
            for c in del_char:
                if (urlok.find(c) == -1):
                    found = True
            if not found:
                listeurlok.add(urlok)

        # on ecrit la liste validee     
        for line in listeurlok:
            file_dest.write(line + "\n")


    def addtoblacklistDomain(self, file_univ, file_dest, domainsalreadyseen):

        listeurl = open(file_univ, 'rb').readlines()
        listeurlok = set()

        #on parcourt les domainss pour les valider      
        for url in listeurl:
            urlok = url.strip().split("/")[0]
            # on enleve les deux points(URL invalide)
            # on enleve les tld (bloque par BC)
            # domaine inconnu dans les autres categories
            if (urlok.find("..") == -1) and (urlok.find(".") != -1) and (not urlok in domainsalreadyseen):
                listeurlok.add(urlok)
                # on ajoute dans les domaines deja vu (premiere categorie vue prime)
                domainsalreadyseen.add(urlok)

        # on ecrit la liste validee   
        for line in listeurlok:
            file_dest.write(line + "\n")

    def run(self):
        self.journal.debug("Debut de la mise à jour")
        self.journal.info("Téléchargement du fichier %s" % URL_BLACKLIST)
        location = download(URL_BLACKLIST, journal=self.journal)
        if location:
            if not os.path.isdir(BLACKLIST_FOLDER):
                self.journal.debug("Création du dossier des blacklists %s" % BLACKLIST_FOLDER)
                os.makedirs(BLACKLIST_FOLDER)

            bltar = tarfile.open(location, "r:gz")
            bltar.extractall()

            self.create_blacklist()

        else:
            self.journal.critical("Récupération des blacklists échouées")


class Journal:
    ###############################################################################
    def __init__(self, level):
        self.journal = logging.getLogger("%s" % nomScript)
        self.journal.setLevel(level)
        # create console handler and sElementTree level to debug
        ch = logging.StreamHandler()
        ch.setLevel(level)
        # create formatter
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        # add formatter to ch
        ch.setFormatter(formatter)
        # add ch to logger
        self.journal.addHandler(ch)

        self.journal = logging.getLogger("%s" % nomScript)
        self.journal.setLevel(level)
        # Add the log message handler to the logger
        pathlog = PATH_LOG
        if not os.path.exists(pathlog):
            os.makedirs(pathlog)
        LOG_FILENAME = os.path.join(pathlog, nomScript + ".log")
        handler = logging.handlers.RotatingFileHandler(
            LOG_FILENAME, maxBytes=200000, backupCount=5)
        formatter2 = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter2)
        self.journal.addHandler(handler)

        self.journal.info("Release %s de %s" % (release, nomScript))

    def sElementTreeLevel(self, level):
        self.journal.sElementTreeLevel(level)

    def info(self, message):
        self.journal.info(message)

    def debug(self, message):
        self.journal.debug(message)

    def warn(self, message):
        self.journal.warn(message)

    def critical(self, message):
        self.journal.critical(message)

    def error(self, message):
        self.journal.error(message)

        # Rappel
        #journal.debug("debug message")
        #journal.info("info message")
        #journal.warn("warn message")
        #journal.error("error message")
        #journal.critical("critical message")


###############################################################################
#Fonction principale
def main():
    # level = logging.INFO

    level = logging.DEBUG
    journal = Journal(level)
    sq = SquidACLupdate(journal)
    sq.run()


if __name__ == "__main__":
    main()
