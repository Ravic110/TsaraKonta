"""
Fenêtre de paramétrage des informations d'en-tête (société)
Sauvegarde/charge les préférences dans EtatFiFolder/settings.json
"""
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd

from models.data import DataManager
from utils.formatters import extraire_numero_compte

STATE_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'EtatFiFolder')
SETTINGS_FILE = os.path.join(STATE_FOLDER, 'settings.json')
OP_COLUMNS = ["ID_PARAMETRE", "TYPE OPERATION", "DEBIT", "CREDIT"]
PCG_COLUMNS = ["NUMERO", "LIBELLE"]

DEFAULT = {
    'nom_societe': '',
    'adresse': '',
    'NIF': '',
    'STAT': '',
    'RCS': ''
}


def load_header_settings():
    os.makedirs(STATE_FOLDER, exist_ok=True)
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    merged = DEFAULT.copy()
                    merged.update(data)
                    return merged
    except Exception:
        pass
    return DEFAULT.copy()


def save_header_settings(values):
    os.makedirs(STATE_FOLDER, exist_ok=True)
    merged = DEFAULT.copy()
    if isinstance(values, dict):
        merged.update(values)
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)


def format_header_text(settings):
    data = DEFAULT.copy()
    if isinstance(settings, dict):
        data.update(settings)

    lines = []
    nom = str(data.get('nom_societe', '')).strip()
    if nom:
        lines.append(nom)

    adresse = str(data.get('adresse', '')).strip()
    if adresse:
        lines.append(adresse)

    infos = []
    for key in ['NIF', 'STAT', 'RCS']:
        value = str(data.get(key, '')).strip()
        if value:
            infos.append(f"{key}: {value}")

    if infos:
        lines.append(' | '.join(infos))

    return '\n'.join(lines)


class SettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        os.makedirs(STATE_FOLDER, exist_ok=True)
        self.title('Paramétrage')
        self.geometry('480x220')
        self._load()
        self._build()

    def _load(self):
        self.settings = load_header_settings()

    def _build(self):
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text='Nom société:').grid(row=0, column=0, sticky=tk.W, pady=4)
        self.nom_var = tk.StringVar(value=self.settings.get('nom_societe', ''))
        ttk.Entry(frm, textvariable=self.nom_var, width=50).grid(row=0, column=1, pady=4)

        ttk.Label(frm, text='Adresse:').grid(row=1, column=0, sticky=tk.W, pady=4)
        self.addr_var = tk.StringVar(value=self.settings.get('adresse', ''))
        ttk.Entry(frm, textvariable=self.addr_var, width=50).grid(row=1, column=1, pady=4)

        ttk.Label(frm, text='NIF:').grid(row=2, column=0, sticky=tk.W, pady=4)
        self.nif_var = tk.StringVar(value=self.settings.get('NIF', ''))
        ttk.Entry(frm, textvariable=self.nif_var, width=30).grid(row=2, column=1, sticky=tk.W, pady=4)

        ttk.Label(frm, text='STAT:').grid(row=3, column=0, sticky=tk.W, pady=4)
        self.stat_var = tk.StringVar(value=self.settings.get('STAT', ''))
        ttk.Entry(frm, textvariable=self.stat_var, width=30).grid(row=3, column=1, sticky=tk.W, pady=4)

        ttk.Label(frm, text='RCS:').grid(row=4, column=0, sticky=tk.W, pady=4)
        self.rcs_var = tk.StringVar(value=self.settings.get('RCS', ''))
        ttk.Entry(frm, textvariable=self.rcs_var, width=30).grid(row=4, column=1, sticky=tk.W, pady=4)

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text='Enregistrer', command=self.save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text='Annuler', command=self.destroy).pack(side=tk.LEFT, padx=6)

    def save(self):
        data = {
            'nom_societe': self.nom_var.get(),
            'adresse': self.addr_var.get(),
            'NIF': self.nif_var.get(),
            'STAT': self.stat_var.get(),
            'RCS': self.rcs_var.get()
        }
        try:
            save_header_settings(data)
            messagebox.showinfo('Paramétrage', 'Paramètres enregistrés')
            self.destroy()
        except Exception as e:
            messagebox.showerror('Erreur', f'Impossible d\'enregistrer: {e}')


class OperationTypesWindow(tk.Toplevel):
    """Fenetre CRUD pour les types d'operations comptables (sittings/settings.xlsx)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Gestion des types d'operations")
        self.geometry("860x460")
        self.transient(parent)
        self.grab_set()

        self.settings_path = DataManager.resolve_operation_settings_file()
        self.pcg_values = self._load_pcg_values()
        self.df = pd.DataFrame(columns=OP_COLUMNS)
        self.selected_index = None
        self._build()
        self._load()

    def _load_pcg_values(self):
        pcg_df, _pcg_path = DataManager.load_pcg_dataframe()
        if pcg_df is None or pcg_df.empty:
            return ["Saisir manuellement"]
        values = []
        for _, row in pcg_df.iterrows():
            numero = str(row.get("NUMERO", "") or "").strip()
            libelle = str(row.get("LIBELLE", "") or "").strip()
            if numero and libelle:
                values.append(f"{numero} - {libelle}")
            elif numero:
                values.append(numero)
        return values if values else ["Saisir manuellement"]

    def _build(self):
        root = ttk.Frame(self, padding=10)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=3)
        root.columnconfigure(1, weight=2)
        root.rowconfigure(1, weight=1)

        self.path_var = tk.StringVar(value="")
        ttk.Label(root, textvariable=self.path_var, foreground="#4A5A57").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        table_frame = ttk.LabelFrame(root, text="Operations")
        table_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(table_frame, columns=OP_COLUMNS, show="headings", height=14)
        self.tree.heading("ID_PARAMETRE", text="ID")
        self.tree.heading("TYPE OPERATION", text="Type operation")
        self.tree.heading("DEBIT", text="Debit")
        self.tree.heading("CREDIT", text="Credit")
        self.tree.column("ID_PARAMETRE", width=70, anchor=tk.CENTER)
        self.tree.column("TYPE OPERATION", width=330, anchor=tk.W)
        self.tree.column("DEBIT", width=90, anchor=tk.CENTER)
        self.tree.column("CREDIT", width=90, anchor=tk.CENTER)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns")

        form = ttk.LabelFrame(root, text="Edition")
        form.grid(row=1, column=1, sticky="nsew")
        form.columnconfigure(1, weight=1)

        self.id_var = tk.StringVar()
        self.type_var = tk.StringVar()
        self.debit_var = tk.StringVar()
        self.credit_var = tk.StringVar()

        ttk.Label(form, text="ID:").grid(row=0, column=0, sticky="w", pady=4, padx=(8, 6))
        ttk.Entry(form, textvariable=self.id_var).grid(row=0, column=1, sticky="ew", pady=4, padx=(0, 8))
        ttk.Label(form, text="Type operation:").grid(row=1, column=0, sticky="w", pady=4, padx=(8, 6))
        ttk.Entry(form, textvariable=self.type_var).grid(row=1, column=1, sticky="ew", pady=4, padx=(0, 8))
        ttk.Label(form, text="Compte debit:").grid(row=2, column=0, sticky="w", pady=4, padx=(8, 6))
        self.debit_combo = ttk.Combobox(form, textvariable=self.debit_var, values=self.pcg_values, width=36)
        self.debit_combo.grid(row=2, column=1, sticky="ew", pady=4, padx=(0, 8))
        ttk.Label(form, text="Compte credit:").grid(row=3, column=0, sticky="w", pady=4, padx=(8, 6))
        self.credit_combo = ttk.Combobox(form, textvariable=self.credit_var, values=self.pcg_values, width=36)
        self.credit_combo.grid(row=3, column=1, sticky="ew", pady=4, padx=(0, 8))
        self._bind_compte_combo(self.debit_combo, self.debit_var)
        self._bind_compte_combo(self.credit_combo, self.credit_var)
        self.debit_combo.configure(postcommand=lambda c=self.debit_combo: self._ensure_dropdown_xscroll(c))
        self.credit_combo.configure(postcommand=lambda c=self.credit_combo: self._ensure_dropdown_xscroll(c))

        btns = ttk.Frame(form)
        btns.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 6), padx=8)
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)
        btns.columnconfigure(2, weight=1)

        ttk.Button(btns, text="Nouveau", command=self._clear_form).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(btns, text="Ajouter", command=self._add_row).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(btns, text="Modifier", command=self._update_row).grid(row=0, column=2, sticky="ew", padx=(4, 0))
        ttk.Button(btns, text="Supprimer", command=self._delete_row).grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=(6, 0))
        ttk.Button(btns, text="Enregistrer", command=self._save).grid(row=1, column=1, sticky="ew", padx=4, pady=(6, 0))
        ttk.Button(btns, text="Fermer", command=self.destroy).grid(row=1, column=2, sticky="ew", padx=(4, 0), pady=(6, 0))

    def _load(self):
        df, path = DataManager.load_operation_types_dataframe(self.settings_path)
        self.settings_path = path
        self.path_var.set(f"Fichier: {self.settings_path or 'sittings.xlsx'}")
        self.df = df.copy() if df is not None else pd.DataFrame(columns=OP_COLUMNS)
        for col in OP_COLUMNS:
            if col not in self.df.columns:
                self.df[col] = ""
        self.df = self.df[OP_COLUMNS].fillna("").astype(str)
        self._refresh_tree()
        self._clear_form()

    def _refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx, row in self.df.iterrows():
            self.tree.insert("", tk.END, iid=str(idx), values=tuple(row[col] for col in OP_COLUMNS))

    def _on_select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        idx = int(selection[0])
        if idx < 0 or idx >= len(self.df):
            return
        self.selected_index = idx
        row = self.df.iloc[idx]
        self.id_var.set(str(row.get("ID_PARAMETRE", "") or ""))
        self.type_var.set(str(row.get("TYPE OPERATION", "") or ""))
        self.debit_var.set(str(row.get("DEBIT", "") or ""))
        self.credit_var.set(str(row.get("CREDIT", "") or ""))

    def _clear_form(self):
        self.selected_index = None
        self.id_var.set(self._next_id())
        self.type_var.set("")
        self.debit_var.set("")
        self.credit_var.set("")
        self.tree.selection_remove(*self.tree.selection())

    def _next_id(self):
        max_id = 0
        for value in self.df.get("ID_PARAMETRE", pd.Series(dtype=str)).astype(str):
            text = value.strip()
            if text.isdigit():
                max_id = max(max_id, int(text))
        return str(max_id + 1)

    def _read_form(self):
        debit_value = self.debit_var.get().strip()
        credit_value = self.credit_var.get().strip()
        if " - " in debit_value:
            debit_value = extraire_numero_compte(debit_value)
        if " - " in credit_value:
            credit_value = extraire_numero_compte(credit_value)
        row = {
            "ID_PARAMETRE": self.id_var.get().strip() or self._next_id(),
            "TYPE OPERATION": self.type_var.get().strip(),
            "DEBIT": debit_value,
            "CREDIT": credit_value,
        }
        if not row["TYPE OPERATION"]:
            messagebox.showwarning("Operations", "Le type d'operation est obligatoire.", parent=self)
            return None
        if not row["DEBIT"] or not row["CREDIT"]:
            messagebox.showwarning("Operations", "Les comptes debit/credit sont obligatoires.", parent=self)
            return None
        return row

    def _bind_compte_combo(self, combo: ttk.Combobox, var: tk.StringVar):
        def _filter(_event=None):
            query = var.get().strip()
            if not query:
                combo["values"] = self.pcg_values
                return
            if self.pcg_values == ["Saisir manuellement"]:
                combo["values"] = self.pcg_values
                return
            filtered = [v for v in self.pcg_values if query in v.split(" - ")[0]]
            combo["values"] = filtered if filtered else self.pcg_values

        def _select(_event=None):
            selected = var.get().strip()
            if " - " in selected:
                var.set(extraire_numero_compte(selected))

        combo.bind("<KeyRelease>", _filter)
        combo.bind("<<ComboboxSelected>>", _select)

    def _ensure_dropdown_xscroll(self, combo: ttk.Combobox):
        """Ajoute un scroll horizontal directement dans la liste déroulante du Combobox."""
        try:
            popdown = combo.tk.call("ttk::combobox::PopdownWindow", str(combo))
            listbox_path = f"{popdown}.f.l"
            frame_path = f"{popdown}.f"
            xsb_path = f"{frame_path}.xsb"

            if not int(combo.tk.call("winfo", "exists", listbox_path)):
                return
            listbox = combo.nametowidget(listbox_path)
            frame = combo.nametowidget(frame_path)

            if int(combo.tk.call("winfo", "exists", xsb_path)):
                xsb = combo.nametowidget(xsb_path)
            else:
                xsb = tk.Scrollbar(frame, name="xsb", orient=tk.HORIZONTAL, command=listbox.xview)
                xsb.pack(side=tk.BOTTOM, fill=tk.X)

            listbox.configure(xscrollcommand=xsb.set)
            # Largeur de popup plus confortable pour les libellés longs.
            try:
                listbox.configure(width=max(48, int(combo.cget("width")) + 8))
            except Exception:
                pass
        except Exception:
            # Fallback silencieux si la plateforme ne supporte pas ce hook Tk interne.
            return

    def _add_row(self):
        row = self._read_form()
        if not row:
            return
        self.df = pd.concat([self.df, pd.DataFrame([row])], ignore_index=True)
        self._refresh_tree()
        self._clear_form()

    def _update_row(self):
        if self.selected_index is None:
            messagebox.showwarning("Operations", "Selectionnez une ligne a modifier.", parent=self)
            return
        row = self._read_form()
        if not row:
            return
        for key, value in row.items():
            self.df.iloc[self.selected_index, self.df.columns.get_loc(key)] = value
        self._refresh_tree()
        self.tree.selection_set(str(self.selected_index))

    def _delete_row(self):
        if self.selected_index is None:
            messagebox.showwarning("Operations", "Selectionnez une ligne a supprimer.", parent=self)
            return
        if not messagebox.askyesno("Operations", "Supprimer cette ligne ?", parent=self):
            return
        self.df = self.df.drop(index=self.selected_index).reset_index(drop=True)
        self._refresh_tree()
        self._clear_form()

    def _save(self):
        ok = DataManager.save_operation_types_dataframe(self.df, self.settings_path)
        if ok:
            messagebox.showinfo("Operations", "Parametres enregistres.", parent=self)
            self._load()


class PCGWindow(tk.Toplevel):
    """Fenetre CRUD du plan comptable general (PCG)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Gestion PCG")
        self.geometry("860x460")
        self.transient(parent)
        self.grab_set()

        self.pcg_path = DataManager.resolve_pcg_file()
        self.df = pd.DataFrame(columns=PCG_COLUMNS)
        self.selected_index = None
        self._build()
        self._load()

    def _build(self):
        root = ttk.Frame(self, padding=10)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=3)
        root.columnconfigure(1, weight=2)
        root.rowconfigure(1, weight=1)

        self.path_var = tk.StringVar(value="")
        ttk.Label(root, textvariable=self.path_var, foreground="#4A5A57").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )

        table_frame = ttk.LabelFrame(root, text="Comptes PCG")
        table_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(table_frame, columns=PCG_COLUMNS, show="headings", height=14)
        self.tree.heading("NUMERO", text="Numero")
        self.tree.heading("LIBELLE", text="Libelle")
        self.tree.column("NUMERO", width=140, anchor=tk.CENTER)
        self.tree.column("LIBELLE", width=380, anchor=tk.W)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns")

        form = ttk.LabelFrame(root, text="Edition")
        form.grid(row=1, column=1, sticky="nsew")
        form.columnconfigure(1, weight=1)

        self.numero_var = tk.StringVar()
        self.libelle_var = tk.StringVar()

        ttk.Label(form, text="Numero compte:").grid(row=0, column=0, sticky="w", pady=4, padx=(8, 6))
        ttk.Entry(form, textvariable=self.numero_var).grid(row=0, column=1, sticky="ew", pady=4, padx=(0, 8))
        ttk.Label(form, text="Libelle compte:").grid(row=1, column=0, sticky="w", pady=4, padx=(8, 6))
        ttk.Entry(form, textvariable=self.libelle_var).grid(row=1, column=1, sticky="ew", pady=4, padx=(0, 8))

        btns = ttk.Frame(form)
        btns.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 6), padx=8)
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)
        btns.columnconfigure(2, weight=1)

        ttk.Button(btns, text="Nouveau", command=self._clear_form).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(btns, text="Ajouter", command=self._add_row).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(btns, text="Modifier", command=self._update_row).grid(row=0, column=2, sticky="ew", padx=(4, 0))
        ttk.Button(btns, text="Supprimer", command=self._delete_row).grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=(6, 0))
        ttk.Button(btns, text="Enregistrer", command=self._save).grid(row=1, column=1, sticky="ew", padx=4, pady=(6, 0))
        ttk.Button(btns, text="Fermer", command=self.destroy).grid(row=1, column=2, sticky="ew", padx=(4, 0), pady=(6, 0))

    def _load(self):
        df, path = DataManager.load_pcg_dataframe(self.pcg_path)
        self.pcg_path = path
        self.path_var.set(f"Fichier: {self.pcg_path or 'pcg.xlsx'}")
        self.df = df.copy() if df is not None else pd.DataFrame(columns=PCG_COLUMNS)
        for col in PCG_COLUMNS:
            if col not in self.df.columns:
                self.df[col] = ""
        self.df = self.df[PCG_COLUMNS].fillna("").astype(str)
        self._refresh_tree()
        self._clear_form()

    def _refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx, row in self.df.iterrows():
            self.tree.insert("", tk.END, iid=str(idx), values=(row["NUMERO"], row["LIBELLE"]))

    def _on_select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        idx = int(selection[0])
        if idx < 0 or idx >= len(self.df):
            return
        self.selected_index = idx
        row = self.df.iloc[idx]
        self.numero_var.set(str(row.get("NUMERO", "") or ""))
        self.libelle_var.set(str(row.get("LIBELLE", "") or ""))

    def _clear_form(self):
        self.selected_index = None
        self.numero_var.set("")
        self.libelle_var.set("")
        self.tree.selection_remove(*self.tree.selection())

    def _read_form(self):
        row = {
            "NUMERO": self.numero_var.get().strip(),
            "LIBELLE": self.libelle_var.get().strip(),
        }
        if not row["NUMERO"]:
            messagebox.showwarning("PCG", "Le numero de compte est obligatoire.", parent=self)
            return None
        if not row["LIBELLE"]:
            messagebox.showwarning("PCG", "Le libelle de compte est obligatoire.", parent=self)
            return None
        return row

    def _add_row(self):
        row = self._read_form()
        if not row:
            return
        self.df = pd.concat([self.df, pd.DataFrame([row])], ignore_index=True)
        self._refresh_tree()
        self._clear_form()

    def _update_row(self):
        if self.selected_index is None:
            messagebox.showwarning("PCG", "Selectionnez une ligne a modifier.", parent=self)
            return
        row = self._read_form()
        if not row:
            return
        for key, value in row.items():
            self.df.iloc[self.selected_index, self.df.columns.get_loc(key)] = value
        self._refresh_tree()
        self.tree.selection_set(str(self.selected_index))

    def _delete_row(self):
        if self.selected_index is None:
            messagebox.showwarning("PCG", "Selectionnez une ligne a supprimer.", parent=self)
            return
        if not messagebox.askyesno("PCG", "Supprimer cette ligne ?", parent=self):
            return
        self.df = self.df.drop(index=self.selected_index).reset_index(drop=True)
        self._refresh_tree()
        self._clear_form()

    def _save(self):
        ok = DataManager.save_pcg_dataframe(self.df, self.pcg_path)
        if ok:
            if hasattr(self.parent, "charger_pcg"):
                self.parent.charger_pcg()
            messagebox.showinfo("PCG", "PCG enregistre.", parent=self)
            self._load()
