# -*-coding:Utf-8 -*

# Logiciel écrit par FreePostPas pour Unlimited-Tracker

import os
from gennfo import *
from gentorrent import *
from tkinter import *
from tkinter import filedialog

application = Tk()
application.title("Seed A Video")

class Interface(Frame):

	def __init__(self, fenetre, **kwargs):
		Frame.__init__(self, fenetre, width=768, height=576, **kwargs)
		self.pack(fill=BOTH)

		self.labelAnnounce = Label(self, text="Entrez l'announce de votre tracker")
		self.labelAnnounce.grid(column=1, row=2)

		self.announce = StringVar()
		self.ligne_announce = Entry(self, textvariable=self.announce, width=30)
		self.ligne_announce.grid(column=1,row=3)

		self.boutonValider = Button(self, text="Choisir un fichier et générez les fichiers", command=self.execution)
		self.boutonValider.grid(column=1,row=4)

	def execution(self):
		print("Choix du fichier")
		self.fichier = filedialog.askopenfilename()
		print("Fait")

		#Generation du torrent
		print("Generation des metadonnées du torrent")
		self.filename = str.encode(self.fichier)
		self.infoname = self.filename + b'.torrent'

		self.announce = [[str.encode(self.announce.get())]]

		print("Enregistrement des métadonnées dans le .torrent")
		with open(self.infoname, "wb") as infofile:
			torrent = Metainfo(self.filename, announce=self.announce, private=True)
			infofile.write(bencode(torrent))
		print("Fait")

		# Generation du NFO
		gen_nfo(self.fichier)

		print("\nGénération des fichiers .nfo et .torrent terminés.")
		print("Logiciel écrit par FreePostPas.")

		print("Vous pouvez fermer les fenêtres")
	

interface = Interface(application)
interface.mainloop()
