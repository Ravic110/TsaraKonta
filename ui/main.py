"""
Interface principale de l'application comptable
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import sys
import os

# Ajout du chemin parent pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import CONFIG
from models.data import DataManager, PCGManager
from utils.formatters import format_montant
from utils.logging_config import get_app_logger
from .dialogs import DialogueLigne
from .etat_resultat import CompteResultatNatureWindow
from .etat_resultat_fonction import CompteResultatFonctionWindow
from .bilan_actif import BilanActifWindow
from .bilan_passif import BilanPassifWindow
from .flux_tresorerie_direct import FluxTresorerieDirectWindow
from .flux_tresorerie_indirect import FluxTresorerieIndirectWindow
from .ratios import RatioResultatNatureWindow, RatioResultatFonctionWindow, RatioBilanWindow
from .settings import SettingsWindow
from .invoice_ocr import extract_invoice_data_from_file

logger = get_app_logger(__name__)


class ComptabiliteApp(tk.Frame):
    """Application principale de gestion comptable"""
    
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.master = parent
        self.fichier_excel = "LivreCompta.xlsx"
        self.df = None
        self.pcg_comptes, self.pcg_numeros, self.pcg_dict = [], [], {}
        
        self.creer_menu()
        self.creer_interface()
        self.charger_pcg()
        self.charger_donnees()
    
    # ==================== MENUS ====================
    def creer_menu(self):
        """Crée la barre de menu"""
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)
        
        menubar.add_cascade(label="Fichier", menu=self.creer_menu_fichier())
        menubar.add_cascade(label="États Financiers", menu=self.creer_menu_etats())
        menubar.add_cascade(label="Ratio", menu=self.creer_menu_ratios())
    
    def creer_menu_fichier(self):
        """Crée le menu Fichier"""
        menu = tk.Menu(self.master, tearoff=0)
        # Paramétrage (entête société)
        menu.add_command(label="Paramétrage", command=lambda: SettingsWindow(self.master))
        # Ouvrir le dossier d'exports
        def _ouvrir_exports_folder():
            folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'EtatFiFolder', 'exports')
            os.makedirs(folder, exist_ok=True)
            try:
                os.startfile(folder)
            except Exception:
                messagebox.showinfo('Info', f'Emplacement: {folder}')
        menu.add_command(label="Ouvrir dossier exports", command=_ouvrir_exports_folder)
        menu.add_command(label="Scanner facture (OCR)", command=self.scanner_facture_ocr)
        menu.add_command(label="Charger Excel", command=self.charger_fichier)
        menu.add_command(label="Sauvegarder", command=self.sauvegarder)
        menu.add_separator()
        menu.add_command(label="Quitter", command=self.master.quit)
        return menu
    
    def creer_menu_etats(self):
        """Crée le menu États Financiers"""
        menu = tk.Menu(self.master, tearoff=0)
        for etat in CONFIG['etats_financiers']:
            menu.add_command(label=etat, command=lambda e=etat: self.afficher_etat(e))
        menu.add_separator()
        menu.add_cascade(label="Grand Livre", menu=self.creer_menu_grand_livre())
        return menu

    def creer_menu_grand_livre(self):
        """Crée le sous-menu Grand Livre"""
        menu = tk.Menu(self.master, tearoff=0)
        menu.add_command(label="Grand Livre comptable", command=self.afficher_grand_livre)
        return menu

    def creer_menu_ratios(self):
        """Crée le menu Ratios"""
        menu = tk.Menu(self.master, tearoff=0)
        menu.add_command(
            label="Ratio Compte de résultat par nature",
            command=lambda: self.afficher_ratio("Ratio Compte de résultat par nature")
        )
        menu.add_command(
            label="Ration compte de résultat par fonction",
            command=lambda: self.afficher_ratio("Ration compte de résultat par fonction")
        )
        menu.add_command(
            label="Ratio Bilan",
            command=lambda: self.afficher_ratio("Ratio Bilan")
        )
        return menu
    
    # ==================== INTERFACE ====================
    def creer_interface(self):
        """Crée l'interface principale"""
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.creer_barre_recherche(main_frame)
        self.creer_treeview(main_frame)
        self.creer_boutons(main_frame)
        self.creer_stats(main_frame)
    
    def creer_barre_recherche(self, parent):
        """Crée la barre de recherche"""
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_frame, text="Rechercher:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.search_entry.bind('<KeyRelease>', self.filtrer_donnees)
        
        ttk.Button(search_frame, text="Actualiser", command=self.charger_donnees).pack(side=tk.LEFT)
    
    def creer_treeview(self, parent):
        """Crée le tableau de visualisation des données"""
        columns = CONFIG['colonnes_journal']
        self.tree = ttk.Treeview(parent, columns=columns, show='headings', height=20)
        
        for col in columns:
            self.tree.heading(col, text=col)
            width = CONFIG['largeurs_colonnes'].get(col, 80)
            anchor = tk.E if col in ['MontantDébit', 'MontantCrédit'] else tk.W
            self.tree.column(col, width=width, anchor=anchor)
        
        v_scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def creer_boutons(self, parent):
        """Crée les boutons d'action"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(side=tk.RIGHT, padx=(10, 0))
        
        actions = [
            ("Ajouter", self.ajouter_ligne),
            ("Importer facture", self.scanner_facture_ocr),
            ("Modifier", self.modifier_ligne),
            ("Supprimer", self.supprimer_ligne),
            ("Balance", self.afficher_balance)
        ]
        
        for text, cmd in actions:
            ttk.Button(button_frame, text=text, command=cmd).pack(pady=5, fill=tk.X)
    
    def creer_stats(self, parent):
        """Crée le panneau de statistiques"""
        stats_frame = ttk.LabelFrame(parent, text="Résumé du journal", padding="10")
        stats_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(14, 0))
        
        self.total_debit = tk.StringVar(value="Total des débits: 0,00")
        self.total_credit = tk.StringVar(value="Total des crédits: 0,00")
        self.solde_final = tk.StringVar(value="Solde: 0,00")
        
        resume_row = ttk.Frame(stats_frame)
        resume_row.pack(fill=tk.X, pady=(4, 2))
        resume_row.columnconfigure(0, weight=1)
        resume_row.columnconfigure(1, weight=1)
        resume_row.columnconfigure(2, weight=1)

        ttk.Label(resume_row, textvariable=self.total_debit, font=('Segoe UI', 10, 'bold'), anchor='w').grid(row=0, column=0, sticky='ew', padx=(8, 8))
        ttk.Label(resume_row, textvariable=self.total_credit, font=('Segoe UI', 10, 'bold'), anchor='center').grid(row=0, column=1, sticky='ew', padx=(8, 8))
        ttk.Label(resume_row, textvariable=self.solde_final, font=('Segoe UI', 10, 'bold'), anchor='e').grid(row=0, column=2, sticky='ew', padx=(8, 8))
    
    # ==================== GESTION DONNÉES ====================
    def charger_pcg(self):
        """Charge le Plan Comptable Général"""
        self.pcg_comptes, self.pcg_numeros, self.pcg_dict = PCGManager.charger_pcg(self.fichier_excel)
    
    def charger_donnees(self):
        """Charge les données du journal"""
        self.df = DataManager.charger_feuille(self.fichier_excel, CONFIG['feuille_journal'])
        
        if self.df is None:
            self.df = pd.DataFrame(columns=CONFIG['colonnes_journal'])
            self.sauvegarder()
        
        # Ajouter colonnes manquantes
        for col in CONFIG['colonnes_journal']:
            if col not in self.df.columns:
                self.df[col] = 0.0 if col in ['MontantDébit', 'MontantCrédit'] else ''
        
        self.afficher_donnees(self.df)
        self.mettre_a_jour_stats()
    
    def sauvegarder(self):
        """Sauvegarde les données dans Excel"""
        DataManager.sauvegarder_df(self.df, self.fichier_excel, CONFIG['feuille_journal'])
    
    def afficher_donnees(self, df):
        """Affiche les données dans le tableau"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for _, row in df.iterrows():
            values = (
                row.get('Date', ''),
                row.get('Libellé', ''),
                row.get('DateValeur', ''),
                format_montant(row.get('MontantDébit', 0)),
                format_montant(row.get('MontantCrédit', 0)),
                row.get('CompteDébit', ''),
                row.get('CompteCrédit', ''),
                row.get('Année', '')
            )
            self.tree.insert('', tk.END, values=values)
    
    def filtrer_donnees(self, event=None):
        """Filtre les données selon la recherche"""
        if self.df is not None:
            recherche = self.search_var.get().lower()
            df_filtre = self.df[self.df.astype(str).apply(
                lambda x: x.str.contains(recherche, na=False).any(), axis=1)]
            self.afficher_donnees(df_filtre)
    
    def mettre_a_jour_stats(self):
        """Met à jour les statistiques"""
        if self.df is not None:
            total_debit = self.df['MontantDébit'].sum()
            total_credit = self.df['MontantCrédit'].sum()
            solde = total_debit - total_credit
            
            self.total_debit.set(f"Total des débits: {format_montant(total_debit)}")
            self.total_credit.set(f"Total des crédits: {format_montant(total_credit)}")
            self.solde_final.set(f"Solde: {format_montant(solde)}")
    
    # ==================== ACTIONS ====================
    def ajouter_ligne(self):
        """Ouvre le dialogue pour ajouter une ligne"""
        self.ouvrir_dialogue(True)
    
    def modifier_ligne(self):
        """Ouvre le dialogue pour modifier une ligne"""
        selection = self.tree.selection()
        if selection:
            index = self.tree.index(selection[0])
            donnees = self.tree.item(selection[0])['values']
            self.ouvrir_dialogue(False, index, donnees)
        else:
            messagebox.showwarning("Attention", "Sélectionnez une écriture")
    
    def supprimer_ligne(self):
        """Supprime la ligne sélectionnée"""
        selection = self.tree.selection()
        if selection and messagebox.askyesno("Confirmer", "Supprimer l'écriture?"):
            index = self.tree.index(selection[0])
            self.df = self.df.drop(index).reset_index(drop=True)
            self.sauvegarder()
            self.charger_donnees()
    
    def ouvrir_dialogue(self, ajout, index=None, donnees=None):
        """Ouvre le dialogue d'édition"""
        dialogue = DialogueLigne(self.master, self.df, self.pcg_comptes, self.pcg_numeros, ajout, index, donnees)
        self.master.wait_window(dialogue)
        
        if dialogue.resultat:
            self.df = dialogue.df_modifie
            self.afficher_donnees(self.df)
            self.mettre_a_jour_stats()
            self.sauvegarder()
    
    def charger_fichier(self):
        """Ouvre un dialogue pour charger un fichier Excel"""
        fichier = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")])
        if fichier:
            self.fichier_excel = fichier
            self.charger_pcg()
            self.charger_donnees()

    def _load_invoice_preview_image(self, path: str, max_size=(640, 820)):
        """Construit une image Tk pour la previsualisation facture (image/PDF)."""
        ext = os.path.splitext(path.lower())[1]
        pil_image = None
        try:
            if ext == ".pdf":
                try:
                    import pypdfium2 as pdfium  # type: ignore
                except Exception:
                    return None, "Apercu PDF indisponible (pypdfium2 manquant)."
                pdf = pdfium.PdfDocument(path)
                if len(pdf) == 0:
                    pdf.close()
                    return None, "PDF vide."
                page = pdf[0]
                bitmap = page.render(scale=1.5)
                pil_image = bitmap.to_pil().convert("RGB")
                page.close()
                pdf.close()
            else:
                from PIL import Image  # type: ignore
                with Image.open(path) as image:
                    pil_image = image.convert("RGB").copy()
        except Exception as exc:
            return None, f"Apercu indisponible: {exc}"

        if pil_image is None:
            return None, "Apercu indisponible."

        pil_image.thumbnail(max_size)
        try:
            from PIL import ImageTk  # type: ignore
            return ImageTk.PhotoImage(pil_image), None
        except Exception as exc:
            return None, f"Apercu indisponible (ImageTk): {exc}"

    def _demander_confirmation_previsualisation(self, path: str, data: dict) -> bool:
        """Affiche une previsualisation facture et demande confirmation d'import."""
        modal = tk.Toplevel(self.master)
        modal.title("Previsualisation facture OCR")
        modal.geometry("980x700")
        modal.transient(self.master)
        modal.grab_set()

        result = {"confirm": False}

        ttk.Label(
            modal,
            text=f"Fichier: {os.path.basename(path)}",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 4))
        ttk.Label(modal, text=path).pack(anchor="w", padx=12, pady=(0, 10))

        body = ttk.Frame(modal, padding=(10, 0, 10, 10))
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=2)
        body.columnconfigure(1, weight=3)
        body.rowconfigure(0, weight=1)

        preview_frame = ttk.LabelFrame(body, text="Apercu facture")
        preview_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        preview_img, preview_error = self._load_invoice_preview_image(path)
        if preview_img is not None:
            image_label = ttk.Label(preview_frame, image=preview_img)
            image_label.image = preview_img
            image_label.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        else:
            ttk.Label(
                preview_frame,
                text=preview_error or "Apercu indisponible.",
                foreground="gray",
                anchor="center",
                justify=tk.CENTER,
            ).pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        details_frame = ttk.LabelFrame(body, text="Donnees detectees")
        details_frame.grid(row=0, column=1, sticky="nsew")
        details_frame.columnconfigure(1, weight=1)
        champs = [
            ("Date", data.get("date", "")),
            ("Date valeur", data.get("date_valeur", "")),
            ("Montant debit", format_montant(float(data.get("montant_debit", 0.0) or 0.0))),
            ("Libelle", data.get("libelle", "")),
            ("Compte debit", data.get("compte_debit", "")),
            ("Compte credit", data.get("compte_credit", "")),
            ("Annee", data.get("annee", "")),
        ]
        for idx, (label, value) in enumerate(champs):
            ttk.Label(details_frame, text=f"{label}:", font=("Segoe UI", 9, "bold")).grid(
                row=idx, column=0, sticky="nw", padx=(10, 6), pady=(6, 0)
            )
            ttk.Label(details_frame, text=str(value), wraplength=430, justify=tk.LEFT).grid(
                row=idx, column=1, sticky="nw", padx=(0, 10), pady=(6, 0)
            )

        ttk.Label(details_frame, text="Texte OCR:", font=("Segoe UI", 9, "bold")).grid(
            row=len(champs), column=0, sticky="nw", padx=(10, 6), pady=(10, 0)
        )
        ocr_text = tk.Text(details_frame, height=16, wrap=tk.WORD)
        ocr_text.grid(row=len(champs), column=1, sticky="nsew", padx=(0, 10), pady=(10, 10))
        details_frame.rowconfigure(len(champs), weight=1)
        ocr_text.insert("1.0", data.get("ocr_text", "") or "")
        ocr_text.config(state=tk.DISABLED)

        btn_row = ttk.Frame(modal, padding=(10, 0, 10, 10))
        btn_row.pack(fill=tk.X)

        def _annuler():
            result["confirm"] = False
            modal.destroy()

        def _importer():
            result["confirm"] = True
            modal.destroy()

        ttk.Button(btn_row, text="Annuler", command=_annuler).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(btn_row, text="Importer l'ecriture", command=_importer).pack(side=tk.RIGHT)

        modal.protocol("WM_DELETE_WINDOW", _annuler)
        self.master.wait_window(modal)
        return result["confirm"]

    def scanner_facture_ocr(self):
        """Scanne une facture (image/PDF) et pre-remplit une ecriture."""
        path = filedialog.askopenfilename(
            title="Selectionner une facture a scanner",
            filetypes=[
                ("Factures", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp *.pdf"),
                ("Images", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp"),
                ("PDF", "*.pdf"),
            ],
        )
        if not path:
            return

        logger.info("Demande import facture OCR: %s", path)
        try:
            data = extract_invoice_data_from_file(path)
        except FileNotFoundError:
            logger.error("Import facture annule: fichier introuvable.")
            messagebox.showerror("OCR facture", "Fichier introuvable.")
            return
        except ValueError as exc:
            logger.warning("OCR facture parse incomplet: %s", exc)
            messagebox.showerror(
                "OCR facture",
                f"Le texte OCR a ete lu, mais l'analyse a echoue:\n{exc}\n\n"
                "Consultez les logs: EtatFiFolder/logs/app.log",
            )
            return
        except RuntimeError as exc:
            logger.error("OCR facture indisponible: %s", exc)
            messagebox.showerror(
                "OCR facture",
                f"Service OCR non disponible:\n{exc}\n\n"
                "Vous pouvez installer EasyOCR: pip install easyocr\n"
                "Consultez les logs: EtatFiFolder/logs/app.log",
            )
            return
        except Exception as exc:
            logger.exception("Erreur inattendue OCR facture.")
            messagebox.showerror(
                "OCR facture",
                f"Impossible de scanner la facture:\n{exc}\n\n"
                "Pre-requis:\n- pip install -r requirements.txt\n\n"
                "Option fallback systeme:\n"
                "- installer Tesseract OCR sur la machine\n\n"
                "Consultez les logs: EtatFiFolder/logs/app.log",
            )
            return

        if not self._demander_confirmation_previsualisation(path, data):
            logger.info("Import facture annule par utilisateur apres previsualisation.")
            return

        montant = float(data.get("montant_debit", 0.0) or 0.0)
        montant_str = format_montant(montant).replace(".", ",")
        donnees = [
            data.get("date", ""),
            data.get("libelle", "Facture OCR"),
            data.get("date_valeur", ""),
            montant_str,
            format_montant(0.0).replace(".", ","),
            data.get("compte_debit", "607"),
            data.get("compte_credit", "401"),
            data.get("annee", ""),
        ]

        self.ouvrir_dialogue(True, donnees=donnees)
        logger.info("Facture OCR importee avec succes: montant=%s libelle=%s", montant, data.get("libelle", ""))
    
    def afficher_balance(self):
        """Affiche la balance du journal"""
        if self.df is not None:
            balance_debit = self.df.groupby('CompteDébit')['MontantDébit'].sum()
            balance_credit = self.df.groupby('CompteCrédit')['MontantCrédit'].sum()
            balance = pd.DataFrame({'Débit': balance_debit, 'Crédit': balance_credit}).fillna(0)
            messagebox.showinfo("Balance Journal", balance.to_string())
    
    def afficher_etat(self, type_etat):
        """Affiche un état financier"""
        if type_etat == "Bilan actif":
            BilanActifWindow(self.master, self.df)
            return

        if type_etat == "Bilan passif":
            BilanPassifWindow(self.master, self.df)
            return

        # Ouvrir la fenêtre dédiée pour le Compte de résultat par nature
        if type_etat == "Compte de résultat par nature":
            CompteResultatNatureWindow(self.master, self.df, self.pcg_dict)
            return

        if type_etat == "Compte de résultat par fonction":
            CompteResultatFonctionWindow(self.master, self.df)
            return

        if type_etat == "Tableau de flux de trésorerie (méthode directe)":
            FluxTresorerieDirectWindow(self.master)
            return

        if type_etat == "Tableau de flux de trésorerie (méthode indirecte)":
            FluxTresorerieIndirectWindow(self.master)
            return

        messagebox.showinfo("États", f"État '{type_etat}' en développement")

    def afficher_grand_livre(self):
        """Affiche le grand livre comptable sommaire par compte"""
        if self.df is None or self.df.empty:
            messagebox.showinfo("Grand Livre", "Aucune donnée disponible")
            return

        debit = self.df.groupby('CompteDébit')['MontantDébit'].sum()
        credit = self.df.groupby('CompteCrédit')['MontantCrédit'].sum()
        comptes = sorted(set(list(debit.index) + list(credit.index)))

        ledger = pd.DataFrame(index=comptes, columns=['Débit', 'Crédit']).fillna(0)
        for c in comptes:
            ledger.at[c, 'Débit'] = float(debit.get(c, 0))
            ledger.at[c, 'Crédit'] = float(credit.get(c, 0))
        ledger['Solde'] = ledger['Débit'] - ledger['Crédit']

        # Calcul des totaux pour la balance générale
        totaux = ledger[['Débit', 'Crédit', 'Solde']].sum()
        total_debit = float(totaux['Débit'])
        total_credit = float(totaux['Crédit'])
        total_solde = float(totaux['Solde'])

        win = tk.Toplevel(self.master)
        win.title("Grand Livre Comptable")
        win.geometry("800x500")

        # Affichage de la balance générale en en-tête
        header = ttk.Frame(win, padding=6)
        header.pack(fill=tk.X)
        ttk.Label(header, text=f"Total Débit: {format_montant(total_debit)}").pack(side=tk.LEFT, padx=(10,5))
        ttk.Label(header, text=f"Total Crédit: {format_montant(total_credit)}").pack(side=tk.LEFT, padx=(10,5))
        ttk.Label(header, text=f"Total Solde: {format_montant(total_solde)}").pack(side=tk.LEFT, padx=(10,5))

        # Bouton d'export
        btn_frame = ttk.Frame(win, padding=6)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(btn_frame, text="Exporter en Excel", command=lambda: self.exporter_grand_livre(ledger)).pack(side=tk.LEFT, padx=5)

        cols = ('Compte', 'Débit', 'Crédit', 'Solde')
        tree = ttk.Treeview(win, columns=cols, show='headings')
        for col in cols:
            tree.heading(col, text=col)
            anchor = tk.E if col in ['Débit', 'Crédit', 'Solde'] else tk.W
            tree.column(col, width=180, anchor=anchor)

        for compte, row in ledger.iterrows():
            tree.insert('', tk.END, values=(compte,
                                            format_montant(row['Débit']),
                                            format_montant(row['Crédit']),
                                            format_montant(row['Solde'])))

        vsb = ttk.Scrollbar(win, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

    def afficher_ratio(self, type_ratio):
        """Affiche la fenêtre de ratios demandée."""
        if type_ratio == "Ratio Compte de résultat par nature":
            RatioResultatNatureWindow(self.master, self.df)
            return

        if type_ratio in ["Ration compte de résultat par fonction", "Ratio compte de résultat par fonction"]:
            RatioResultatFonctionWindow(self.master, self.df)
            return

        if type_ratio == "Ratio Bilan":
            RatioBilanWindow(self.master, self.df)
            return

        messagebox.showinfo("Ratios", f"{type_ratio} indisponible")

    def exporter_grand_livre(self, ledger_df):
        """Exporte le grand livre en Excel dans LivreCompta.xlsx feuille 'GrandLivre'"""
        try:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            excel_file = os.path.join(base_dir, 'EtatFiFolder', 'LivreCompta.xlsx')
            os.makedirs(os.path.dirname(excel_file), exist_ok=True)

            # Réinitialiser l'index pour que 'Compte' devienne une colonne
            export_df = ledger_df.reset_index()
            export_df.rename(columns={'index': 'Compte'}, inplace=True)

            # Vérifier si le fichier existe
            if os.path.exists(excel_file):
                # Charger le fichier existant
                with pd.ExcelWriter(excel_file, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                    export_df.to_excel(writer, sheet_name='GrandLivre', index=False)
            else:
                # Créer un nouveau fichier
                export_df.to_excel(excel_file, sheet_name='GrandLivre', index=False)

            messagebox.showinfo("Export réussi", f"Grand Livre exporté dans:\n{excel_file}\nFeuille: GrandLivre")
        except PermissionError:
            messagebox.showerror("Erreur", "FERMEZ EXCEL avant d'exporter !")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'export: {str(e)}")

