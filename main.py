"""
Application Comptable Refactorisée
Point d'entrée principal

Pour lancer l'application:
    python main.py
"""
import tkinter as tk
from ui.comptabilite_app import ComptabiliteApp


def main():
    """Lance l'application"""
    root = tk.Tk()
    root.title("Application Tsarakonta - Logiciel de comptabilité")
    root.geometry("1200x700")
    
    app = ComptabiliteApp(root)
    app.pack(side="top", fill="both", expand=True)
    
    root.mainloop()


if __name__ == "__main__":
    main()
