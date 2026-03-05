"""
Interface principale de l'application comptable
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import os
import json
from datetime import datetime

from config import CONFIG
from models.data import DataManager, PCGManager
from utils.formatters import format_montant, extraire_numero_compte, parse_montant
from utils.logging_config import get_app_logger
from utils.system import open_path
from .journal_dialogs import DialogueLigne
from .etat_resultat import CompteResultatNatureWindow
from .etat_resultat_fonction import CompteResultatFonctionWindow
from .bilan_actif import BilanActifWindow
from .bilan_passif import BilanPassifWindow
from .flux_tresorerie_direct import FluxTresorerieDirectWindow
from .flux_tresorerie_indirect import FluxTresorerieIndirectWindow
from .ratios import RatioResultatNatureWindow, RatioResultatFonctionWindow, RatioBilanWindow
from .settings import SettingsWindow, OperationTypesWindow, PCGWindow
from services.invoice_ocr import extract_invoice_data_from_file

logger = get_app_logger(__name__)
PRIMARY_COLOR = "#0B6E4F"
ACCENT_COLOR = "#1F8A70"
ROW_ALT_COLOR = "#F4FAF8"


class ComptabiliteApp(tk.Frame):
    """Application principale de gestion comptable"""
    
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.master = parent
        self.fichier_excel = DataManager.resolve_journal_file()
        self.df = None
        self.pcg_comptes, self.pcg_numeros, self.pcg_dict = [], [], {}
        self.status_var = tk.StringVar(value="Prêt")

        self._configure_styles()
        self.creer_menu()
        self.creer_interface()
        self._bind_shortcuts()
        self.charger_pcg()
        self.charger_donnees()

    def _configure_styles(self):
        """Applique un style visuel coherent pour l'ecran principal."""
        style = ttk.Style(self.master)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure("App.TFrame", background="#F7F9F8")
        style.configure("AppHeader.TLabel", font=("Segoe UI", 14, "bold"), foreground=PRIMARY_COLOR)
        style.configure("SubHeader.TLabel", foreground="#4A5A57")
        style.configure("Primary.TButton", font=("Segoe UI", 9, "bold"))
        style.configure("Treeview", rowheight=28)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _bind_shortcuts(self):
        self.master.bind("<Control-n>", lambda _e: self.ajouter_ligne())
        self.master.bind("<Control-s>", lambda _e: self.sauvegarder())
        self.master.bind("<Control-f>", lambda _e: self.search_entry.focus_set())
        self.master.bind("<Delete>", lambda _e: self.supprimer_ligne())
    
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
        menu.add_command(label="Gestion types d'opérations", command=lambda: OperationTypesWindow(self.master))
        menu.add_command(label="Gestion PCG", command=lambda: PCGWindow(self.master))
        # Ouvrir le dossier d'exports
        def _ouvrir_exports_folder():
            folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'EtatFiFolder', 'exports')
            os.makedirs(folder, exist_ok=True)
            if not open_path(folder):
                messagebox.showinfo('Info', f'Emplacement: {folder}')
        menu.add_command(label="Ouvrir dossier exports", command=_ouvrir_exports_folder)
        menu.add_command(label="Scanner facture (OCR)", command=self.scanner_facture_ocr)
        menu.add_command(label="Importer JSON OCR vers journal", command=self.importer_json_ocr_vers_journal)
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
        main_frame = ttk.Frame(self.master, padding="12", style="App.TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.creer_entete(main_frame)
        self.creer_barre_recherche(main_frame)
        content_frame = ttk.Frame(main_frame, style="App.TFrame")
        content_frame.pack(fill=tk.BOTH, expand=True)
        self.creer_treeview(content_frame)
        self.creer_boutons(content_frame)
        self.creer_stats(main_frame)
        self.creer_status_bar(main_frame)

    def creer_entete(self, parent):
        header = ttk.Frame(parent, style="App.TFrame")
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header, text="Journal comptable", style="AppHeader.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Raccourcis: Ctrl+N (ajouter), Ctrl+S (sauvegarder), Ctrl+F (rechercher), Suppr (supprimer)",
            style="SubHeader.TLabel",
        ).pack(anchor="w", pady=(2, 0))
    
    def creer_barre_recherche(self, parent):
        """Crée la barre de recherche"""
        search_frame = ttk.Frame(parent, style="App.TFrame")
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_frame, text="Rechercher:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.search_entry.bind('<KeyRelease>', self.filtrer_donnees)
        
        ttk.Button(search_frame, text="Actualiser", command=self.charger_donnees).pack(side=tk.LEFT)
        ttk.Button(search_frame, text="Effacer", command=self._reset_search).pack(side=tk.LEFT, padx=(6, 0))
    
    def creer_treeview(self, parent):
        """Crée le tableau de visualisation des données"""
        columns = CONFIG['colonnes_journal']
        self.tree = ttk.Treeview(parent, columns=columns, show='headings', height=20)
        self.tree.tag_configure("oddrow", background=ROW_ALT_COLOR)
        
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
        button_frame = ttk.Frame(parent, style="App.TFrame")
        button_frame.pack(side=tk.RIGHT, padx=(10, 0))

        ttk.Button(button_frame, text="Ajouter", style="Primary.TButton", command=self.ajouter_ligne).pack(pady=5, fill=tk.X)
        ttk.Button(button_frame, text="Importer facture", command=self.scanner_facture_ocr).pack(pady=5, fill=tk.X)
        ttk.Button(button_frame, text="Modifier", command=self.modifier_ligne).pack(pady=5, fill=tk.X)
        ttk.Button(button_frame, text="Supprimer", command=self.supprimer_ligne).pack(pady=5, fill=tk.X)
        ttk.Button(button_frame, text="Balance", command=self.afficher_balance).pack(pady=5, fill=tk.X)
    
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

    def creer_status_bar(self, parent):
        status = ttk.Label(parent, textvariable=self.status_var, anchor="w", style="SubHeader.TLabel")
        status.pack(fill=tk.X, pady=(8, 0))

    def _set_status(self, message: str):
        self.status_var.set(message)

    def _reset_search(self):
        self.search_var.set("")
        self.afficher_donnees(self.df if self.df is not None else pd.DataFrame(columns=CONFIG['colonnes_journal']))
    
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

        auto_imported, _auto_errors = self._import_pending_ocr_json(show_messages=False)
        self.afficher_donnees(self.df)
        self.mettre_a_jour_stats()
        suffix = f" | OCR auto-importés: {auto_imported}" if auto_imported else ""
        self._set_status(f"Fichier: {os.path.basename(self.fichier_excel)} | {len(self.df)} écritures{suffix}")
    
    def sauvegarder(self):
        """Sauvegarde les données dans Excel"""
        DataManager.sauvegarder_df(self.df, self.fichier_excel, CONFIG['feuille_journal'])
        self._set_status(f"Sauvegardé: {os.path.basename(self.fichier_excel)}")
    
    def afficher_donnees(self, df):
        """Affiche les données dans le tableau"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for idx, (_, row) in enumerate(df.iterrows()):
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
            tag = ("oddrow",) if idx % 2 else ()
            self.tree.insert('', tk.END, values=values, tags=tag)
        self._set_status(f"Affichage: {len(df)} ligne(s)")
    
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
        return dialogue.resultat

    def _enregistrer_ocr_import(self, source_path: str, parsed: dict):
        """Enregistre les metadonnees OCR dans la feuille OCR_Imports."""
        record = {
            "imported_at": datetime.now().isoformat(timespec="seconds"),
            "source_file": source_path,
            "invoice_number": parsed.get("invoice_number", ""),
            "supplier_name": parsed.get("supplier_name", ""),
            "invoice_subject": parsed.get("invoice_subject", ""),
            "date": parsed.get("date", ""),
            "date_valeur": parsed.get("date_valeur", ""),
            "type_operation": parsed.get("type_operation", ""),
            "libelle": parsed.get("libelle", ""),
            "montant_debit": float(parsed.get("montant_debit", 0.0) or 0.0),
            "montant_credit": float(parsed.get("montant_credit", 0.0) or 0.0),
            "montant_ht": parsed.get("montant_ht"),
            "montant_tva": parsed.get("montant_tva"),
            "montant_ttc": parsed.get("montant_ttc"),
            "currency": parsed.get("currency", ""),
            "compte_debit": parsed.get("compte_debit", ""),
            "compte_credit": parsed.get("compte_credit", ""),
            "annee": parsed.get("annee", ""),
            "confidence_score": parsed.get("confidence_score"),
            "needs_review": bool(parsed.get("needs_review", False)),
            "parse_warnings": " | ".join(parsed.get("parse_warnings") or []),
            "source_hint": parsed.get("source_hint", ""),
        }
        DataManager.append_row_to_sheet(self.fichier_excel, "OCR_Imports", record)
    
    def charger_fichier(self):
        """Ouvre un dialogue pour charger un fichier Excel"""
        fichier = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx")])
        if fichier:
            self.fichier_excel = fichier
            self.charger_pcg()
            self.charger_donnees()
            self._set_status(f"Fichier chargé: {os.path.basename(self.fichier_excel)}")

    def _load_invoice_preview_image(self, path: str, max_size=(420, 520)):
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

    def _demander_confirmation_previsualisation(self, path: str, data: dict) -> dict | None:
        """Affiche une previsualisation facture editable et renvoie les donnees confirmees."""
        modal = tk.Toplevel(self.master)
        modal.title("Previsualisation facture OCR")
        modal.geometry("860x540")
        modal.transient(self.master)
        modal.grab_set()

        result = {"confirmed_data": None}

        ttk.Label(
            modal,
            text=f"Fichier: {os.path.basename(path)}",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=12, pady=(10, 4))
        ttk.Label(modal, text=path).pack(anchor="w", padx=12, pady=(0, 10))

        body = ttk.Frame(modal, padding=(8, 0, 8, 6))
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
        confidence = float(data.get("confidence_score", 0.0) or 0.0)
        confidence_pct = int(confidence * 100)
        badge_color = "#B42318" if confidence_pct < 60 else "#B54708" if confidence_pct < 80 else "#027A48"
        ttk.Label(details_frame, text="Confiance OCR:", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w", padx=(10, 6), pady=(8, 0)
        )
        ttk.Label(details_frame, text=f"{confidence_pct}%", foreground=badge_color, font=("Segoe UI", 10, "bold")).grid(
            row=0, column=1, sticky="w", padx=(0, 10), pady=(8, 0)
        )
        bar = ttk.Progressbar(details_frame, orient="horizontal", mode="determinate", maximum=100, value=confidence_pct)
        bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(4, 8))

        form_frame = ttk.Frame(details_frame)
        form_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10)
        form_frame.columnconfigure(1, weight=1)

        form_vars = {
            "date": tk.StringVar(value=str(data.get("date", "") or "")),
            "date_valeur": tk.StringVar(value=str(data.get("date_valeur", "") or "")),
            "type_operation": tk.StringVar(value=""),
            "montant_debit": tk.StringVar(value=format_montant(float(data.get("montant_debit", 0.0) or 0.0))),
            "libelle": tk.StringVar(value=str(data.get("libelle", "") or "")),
            "compte_debit": tk.StringVar(value=str(data.get("compte_debit", "607") or "607")),
            "compte_credit": tk.StringVar(value=str(data.get("compte_credit", "401") or "401")),
            "annee": tk.StringVar(value=str(data.get("annee", "") or "")),
        }
        operation_types = DataManager.load_operation_types()
        operation_mapping = {
            item.get("type_operation", ""): item
            for item in operation_types
            if item.get("type_operation")
        }

        def _apply_operation_type(*_args):
            selected = form_vars["type_operation"].get().strip()
            if not selected:
                return
            mapped = operation_mapping.get(selected)
            if not mapped:
                return
            debit = str(mapped.get("debit", "") or "").strip()
            credit = str(mapped.get("credit", "") or "").strip()
            if debit:
                form_vars["compte_debit"].set(debit)
            if credit:
                form_vars["compte_credit"].set(credit)

        base_rows = [
            ("Date", "date"),
            ("Date valeur", "date_valeur"),
        ]
        row_idx = 0
        for label, key in base_rows:
            ttk.Label(form_frame, text=f"{label}:", font=("Segoe UI", 9, "bold")).grid(
                row=row_idx, column=0, sticky="w", pady=(2, 0), padx=(0, 6)
            )
            ttk.Entry(form_frame, textvariable=form_vars[key]).grid(row=row_idx, column=1, sticky="ew", pady=(2, 0))
            row_idx += 1

        ttk.Label(form_frame, text="Type operation:", font=("Segoe UI", 9, "bold")).grid(
            row=row_idx, column=0, sticky="w", pady=(2, 0), padx=(0, 6)
        )
        operation_values = [item["type_operation"] for item in operation_types]
        operation_combo = ttk.Combobox(
            form_frame,
            textvariable=form_vars["type_operation"],
            values=operation_values,
            state="readonly" if operation_values else "normal",
        )
        operation_combo.grid(row=row_idx, column=1, sticky="ew", pady=(2, 0))
        row_idx += 1

        remaining_rows = [
            ("Montant debit", "montant_debit"),
            ("Libelle", "libelle"),
            ("Compte debit", "compte_debit"),
            ("Compte credit", "compte_credit"),
            ("Annee", "annee"),
        ]
        compte_combos = {}
        for label, key in remaining_rows:
            ttk.Label(form_frame, text=f"{label}:", font=("Segoe UI", 9, "bold")).grid(
                row=row_idx, column=0, sticky="w", pady=(2, 0), padx=(0, 6)
            )
            if key in {"compte_debit", "compte_credit"}:
                compte_values = self.pcg_comptes if self.pcg_comptes else ["Saisir manuellement"]
                combo = ttk.Combobox(form_frame, textvariable=form_vars[key], values=compte_values)
                combo.grid(row=row_idx, column=1, sticky="ew", pady=(2, 0))
                compte_combos[key] = combo
            else:
                ttk.Entry(form_frame, textvariable=form_vars[key]).grid(row=row_idx, column=1, sticky="ew", pady=(2, 0))
            row_idx += 1

        def _filter_compte_options(key: str):
            combo = compte_combos.get(key)
            if not combo:
                return
            recherche = str(form_vars[key].get() or "").strip()
            if self.pcg_comptes and recherche:
                filtre = [c for c in self.pcg_comptes if recherche in c.split(" - ")[0]]
                combo["values"] = filtre if filtre else self.pcg_comptes
            else:
                combo["values"] = self.pcg_comptes if self.pcg_comptes else ["Saisir manuellement"]

        def _bind_compte_combo(key: str):
            combo = compte_combos.get(key)
            if not combo:
                return

            def _on_key_release(_event):
                _filter_compte_options(key)

            def _on_select(_event):
                selected = str(form_vars[key].get() or "")
                if " - " in selected:
                    form_vars[key].set(extraire_numero_compte(selected))

            combo.bind("<KeyRelease>", _on_key_release)
            combo.bind("<<ComboboxSelected>>", _on_select)

        _bind_compte_combo("compte_debit")
        _bind_compte_combo("compte_credit")

        initial_type = str(data.get("type_operation", "") or "").strip()
        if initial_type and initial_type in operation_mapping:
            form_vars["type_operation"].set(initial_type)
        elif operation_types:
            current_debit = str(form_vars["compte_debit"].get() or "").strip()
            current_credit = str(form_vars["compte_credit"].get() or "").strip()
            matched = next(
                (
                    item["type_operation"]
                    for item in operation_types
                    if str(item.get("debit", "")).strip() == current_debit
                    and str(item.get("credit", "")).strip() == current_credit
                ),
                operation_types[0]["type_operation"],
            )
            form_vars["type_operation"].set(matched)
        operation_combo.bind("<<ComboboxSelected>>", _apply_operation_type)
        _apply_operation_type()

        summary_parts = []
        if data.get("invoice_number"):
            summary_parts.append(f"N° {data.get('invoice_number')}")
        if data.get("currency"):
            summary_parts.append(f"Devise {data.get('currency')}")
        if data.get("montant_ht") is not None:
            summary_parts.append(f"HT {format_montant(float(data['montant_ht']))}")
        if data.get("montant_tva") is not None:
            summary_parts.append(f"TVA {format_montant(float(data['montant_tva']))}")
        if data.get("montant_ttc") is not None:
            summary_parts.append(f"TTC {format_montant(float(data['montant_ttc']))}")
        if summary_parts:
            ttk.Label(details_frame, text=" | ".join(summary_parts), foreground="#4A5A57").grid(
                row=3, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 2)
            )

        ttk.Label(details_frame, text="Texte OCR:", font=("Segoe UI", 9, "bold")).grid(
            row=4, column=0, sticky="w", padx=(10, 6), pady=(6, 0)
        )
        ocr_container = ttk.Frame(details_frame)
        ocr_container.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=10, pady=(4, 0))
        details_frame.rowconfigure(5, weight=1)

        ocr_text = tk.Text(ocr_container, height=6, wrap=tk.WORD)
        ocr_text.insert("1.0", data.get("ocr_text", "") or "")
        ocr_text.config(state=tk.DISABLED)
        ocr_scroll = ttk.Scrollbar(ocr_container, orient=tk.VERTICAL, command=ocr_text.yview)
        ocr_text.configure(yscrollcommand=ocr_scroll.set)
        ocr_visible = {"value": False}

        def _toggle_ocr_text():
            if ocr_visible["value"]:
                ocr_text.grid_forget()
                ocr_scroll.grid_forget()
                ocr_visible["value"] = False
                toggle_ocr_btn.config(text="Afficher texte OCR")
            else:
                ocr_text.grid(row=0, column=0, sticky="nsew")
                ocr_scroll.grid(row=0, column=1, sticky="ns")
                ocr_container.columnconfigure(0, weight=1)
                ocr_container.rowconfigure(0, weight=1)
                ocr_visible["value"] = True
                toggle_ocr_btn.config(text="Masquer texte OCR")

        def _copy_ocr_text():
            self.master.clipboard_clear()
            self.master.clipboard_append(data.get("ocr_text", "") or "")
            self._set_status("Texte OCR copié dans le presse-papiers")

        ocr_btns = ttk.Frame(details_frame)
        ocr_btns.grid(row=4, column=1, sticky="e", padx=(0, 10), pady=(6, 0))
        toggle_ocr_btn = ttk.Button(ocr_btns, text="Afficher texte OCR", command=_toggle_ocr_text)
        toggle_ocr_btn.pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(ocr_btns, text="Copier texte OCR", command=_copy_ocr_text).pack(side=tk.RIGHT)

        warnings = data.get("parse_warnings") or []
        if warnings:
            ttk.Label(
                details_frame,
                text="Alertes: " + " | ".join(str(w) for w in warnings),
                foreground="#9A6700",
                wraplength=430,
                justify=tk.LEFT,
            ).grid(row=6, column=0, columnspan=2, sticky="w", padx=10, pady=(4, 6))

        btn_row = ttk.Frame(modal, padding=(8, 0, 8, 8))
        btn_row.pack(fill=tk.X, side=tk.BOTTOM)

        def _build_confirmed_payload() -> dict | None:
            try:
                montant = float(str(form_vars["montant_debit"].get()).replace(" ", "").replace(",", "."))
            except Exception:
                messagebox.showerror("Prévisualisation OCR", "Montant invalide (exemple: 1 234,56).", parent=modal)
                return None
            confirmed = dict(data)
            confirmed.update(
                {
                    "date": form_vars["date"].get().strip(),
                    "date_valeur": form_vars["date_valeur"].get().strip(),
                    "type_operation": form_vars["type_operation"].get().strip(),
                    "montant_debit": montant,
                    "libelle": form_vars["libelle"].get().strip(),
                    "compte_debit": form_vars["compte_debit"].get().strip(),
                    "compte_credit": form_vars["compte_credit"].get().strip(),
                    "annee": form_vars["annee"].get().strip(),
                }
            )
            return confirmed

        def _annuler():
            result["confirmed_data"] = None
            modal.destroy()

        def _enregistrer():
            confirmed = _build_confirmed_payload()
            if not confirmed:
                return
            save_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "EtatFiFolder", "ocr_saved")
            os.makedirs(save_dir, exist_ok=True)
            base_name = os.path.splitext(os.path.basename(path))[0]
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_path = os.path.join(save_dir, f"{base_name}_{ts}.json")
            payload = dict(confirmed)
            payload["source_file"] = path
            payload["saved_at"] = datetime.now().isoformat(timespec="seconds")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            self._set_status(f"Brouillon OCR enregistré: {os.path.basename(json_path)}")
            messagebox.showinfo("Prévisualisation OCR", f"Données enregistrées:\n{json_path}", parent=modal)

        def _importer():
            confirmed = _build_confirmed_payload()
            if not confirmed:
                return
            result["confirmed_data"] = confirmed
            modal.destroy()

        ttk.Button(btn_row, text="Annuler", command=_annuler).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(btn_row, text="Enregistrer", command=_enregistrer).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(btn_row, text="Importer l'ecriture", command=_importer).pack(side=tk.RIGHT)

        modal.protocol("WM_DELETE_WINDOW", _annuler)
        self.master.wait_window(modal)
        return result["confirmed_data"]

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

        confirmed = self._demander_confirmation_previsualisation(path, data)
        if not confirmed:
            logger.info("Import facture annule par utilisateur apres previsualisation.")
            return

        montant = float(confirmed.get("montant_debit", 0.0) or 0.0)
        montant_str = format_montant(montant).replace(".", ",")
        donnees = [
            confirmed.get("date", ""),
            confirmed.get("libelle", "Facture OCR"),
            confirmed.get("date_valeur", ""),
            montant_str,
            format_montant(0.0).replace(".", ","),
            confirmed.get("compte_debit", "607"),
            confirmed.get("compte_credit", "401"),
            confirmed.get("annee", ""),
        ]

        imported = self.ouvrir_dialogue(True, donnees=donnees)
        if not imported:
            logger.info("Import OCR annule lors du dialogue d'ecriture.")
            return

        self._enregistrer_ocr_import(path, confirmed)
        logger.info("Facture OCR importee avec succes: montant=%s libelle=%s", montant, confirmed.get("libelle", ""))

    def _coerce_amount(self, raw_value) -> float:
        """Convertit un montant OCR (str/float/int) en float."""
        if raw_value is None:
            return 0.0
        if isinstance(raw_value, (int, float)):
            return float(raw_value)
        try:
            return parse_montant(str(raw_value))
        except Exception:
            return 0.0

    def _build_journal_row_from_ocr_payload(self, payload: dict) -> dict:
        """Construit une ligne du journal a partir d'un payload JSON OCR."""
        date_value = str(payload.get("date", "") or "").strip()
        annee = str(payload.get("annee", "") or "").strip()
        if not annee and len(date_value) >= 10:
            # format attendu: JJ/MM/AAAA
            parts = date_value.split("/")
            if len(parts) == 3 and len(parts[2]) == 4 and parts[2].isdigit():
                annee = parts[2]
        return {
            "Date": date_value,
            "Libellé": str(payload.get("libelle", "Facture OCR") or "Facture OCR").strip(),
            "DateValeur": str(payload.get("date_valeur", "") or "").strip(),
            "MontantDébit": self._coerce_amount(payload.get("montant_debit", 0.0)),
            "MontantCrédit": self._coerce_amount(payload.get("montant_credit", 0.0)),
            "CompteDébit": str(payload.get("compte_debit", "607") or "607").strip(),
            "CompteCrédit": str(payload.get("compte_credit", "401") or "401").strip(),
            "Année": annee,
        }

    def _ocr_saved_dir(self) -> str:
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), "EtatFiFolder", "ocr_saved")

    def _get_imported_ocr_json_sources(self) -> set[str]:
        imported_sources = set()
        ocr_df = DataManager.charger_feuille(self.fichier_excel, "OCR_Imports")
        if ocr_df is None or ocr_df.empty or "source_file" not in ocr_df.columns:
            return imported_sources
        for value in ocr_df["source_file"].fillna("").astype(str):
            path = value.strip()
            if path and path.lower().endswith(".json"):
                imported_sources.add(os.path.normpath(path))
        return imported_sources

    def _import_json_ocr_paths(self, json_paths, show_messages: bool = True):
        if self.df is None:
            self.df = pd.DataFrame(columns=CONFIG['colonnes_journal'])

        imported_sources = self._get_imported_ocr_json_sources()
        imported_count = 0
        skipped_count = 0
        errors = []

        for path in json_paths:
            norm_path = os.path.normpath(path)
            if norm_path in imported_sources:
                skipped_count += 1
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                if not isinstance(payload, dict):
                    raise ValueError("Le contenu JSON doit etre un objet.")
                row = self._build_journal_row_from_ocr_payload(payload)
                self.df = pd.concat([self.df, pd.DataFrame([row])], ignore_index=True)
                self._enregistrer_ocr_import(path, payload)
                imported_sources.add(norm_path)
                imported_count += 1
            except Exception as exc:
                errors.append(f"{os.path.basename(path)}: {exc}")

        if imported_count > 0:
            self.afficher_donnees(self.df)
            self.mettre_a_jour_stats()
            self.sauvegarder()
            self._set_status(f"{imported_count} JSON OCR importé(s) dans le journal")

        if show_messages:
            if errors:
                details = "\n".join(errors[:8])
                if len(errors) > 8:
                    details += "\n..."
                messagebox.showwarning(
                    "Import JSON OCR",
                    f"Importés: {imported_count}\nIgnorés (déjà importés): {skipped_count}\nErreurs: {len(errors)}\n\n{details}",
                )
            elif imported_count > 0 or skipped_count > 0:
                messagebox.showinfo(
                    "Import JSON OCR",
                    f"Importés: {imported_count}\nIgnorés (déjà importés): {skipped_count}",
                )
        return imported_count, skipped_count, errors

    def _import_pending_ocr_json(self, show_messages: bool = False):
        save_dir = self._ocr_saved_dir()
        os.makedirs(save_dir, exist_ok=True)
        json_paths = sorted(
            [
                os.path.join(save_dir, name)
                for name in os.listdir(save_dir)
                if name.lower().endswith(".json")
            ]
        )
        if not json_paths:
            return 0, []
        imported_count, _skipped_count, errors = self._import_json_ocr_paths(json_paths, show_messages=show_messages)
        return imported_count, errors

    def importer_json_ocr_vers_journal(self):
        """Importe un ou plusieurs JSON OCR dans le Journal comptable."""
        default_dir = self._ocr_saved_dir()
        os.makedirs(default_dir, exist_ok=True)
        json_paths = filedialog.askopenfilenames(
            title="Selectionner les JSON OCR a importer",
            initialdir=default_dir,
            filetypes=[("JSON", "*.json")],
        )
        if not json_paths:
            return
        self._import_json_ocr_paths(json_paths, show_messages=True)
    
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
            excel_file = DataManager.resolve_journal_file()
            if not excel_file:
                raise RuntimeError("Chemin de journal comptable indisponible.")
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
