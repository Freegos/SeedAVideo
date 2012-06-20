# -*-coding:Utf-8 -*

# Logiciel écrit par FreePostPas pour Unlimited-Tracker

import os
from MediaInfoDLL3 import *

def gen_nfo(fichier):

	MI = MediaInfo()

	print("Ouverture du fichier par la DLL MediaInfo")
	MI.Open(fichier)
	print("Fait")

	MI.Option_Static("Complete")

	print("Récupération des informations pour le NFO")
	# Chemin du fichier
	FileName = MI.GetI(Stream.General, 0, 46)
<<<<<<< HEAD
	FileName = FileName.split("\\")
	Filename = Filename.reverse()
	Filename = Filename.index()

=======
	FileName = FileName.split("/")
	Morceau = len(FileName)
	Morceau = Morceau - 1
	FileName = FileName[Morceau]
>>>>>>> origin/dev
	# Format video du fichier
	FormatVideo = MI.Get(Stream.General, 0, "Format")
	# Résolution
	Width = MI.Get(Stream.Video, 0, "Width")
	Height = MI.Get(Stream.Video, 0, "Height")
	Resolution = str(Width) + " * " + str(Height)
	# FrameRate
	FrameRate = MI.Get(Stream.Video, 0, "FrameRate")
	# BitRate
	BitRate = MI.Get(Stream.Video, 0, "BitRate")
	# Durée
	Duree = MI.Get(Stream.Video, 0, "Duration/String1")
	# Standard
	standard = MI.Get(Stream.Video, 0, "Standard")
	# Taille du fichier
	FileSize = MI.Get(Stream.General, 0, "FileSize")
	FileSize = int(FileSize) / 1000000
	# Format audio du fichier
	FormatAudio = MI.Get(Stream.Audio, 0, "Format")
	# Nombre de cannaux audio
	Channel = MI.Get(Stream.Audio, 0, "Channel(s)")
	# Sampling Rate
	SamplingRate = MI.Get(Stream.Audio, 0, "SamplingRate")
	print("Fait")

	MI.Close()

	# Création du fichier NFO
	fichier = fichier + ".nfo"
	print("Création du fichier .nfo")
	nfo = open(fichier, "w")
	print("Fait")

	contenuNFO = "Name ......................: " + FileName + "\nVideo Codec ...............: " + FormatVideo + "\nVideo Resolution ..........: " + Resolution + "\nFrame Rate ................: " + str(FrameRate) + " fps\nBitrate ...................: " + str(BitRate) + " bps\nRuntime ...................: " + Duree + "\nStandard ..................: " + standard + "\nSize ......................: " + str(FileSize) + "Mo\nAudio Codec ...............: " + FormatAudio + "\nSampling rate .............: " + str(SamplingRate) + " Hz\n\nNFO généré avec SeedYoursVideos"

	print("Ecriture dans le fichier .nfo")
	nfo.write(contenuNFO)
	print("Fait")

	print("Fermeture du fichier .nfo")
	nfo.close()
	print("Fait")