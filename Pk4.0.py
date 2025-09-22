import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import base64
import sys  # fullscreen

# =============================== CONFIG & DEFAULTS ===============================

DIRECTORY_HOME = os.path.expanduser("~")
PERCORSO_FILE_CONFIG = os.path.join(DIRECTORY_HOME, "configurazione.json")

DEFAULT_PARAMETRI = {
    "volume_annuo_mq": 16000,
    "costo_C_litro": 175.0,
    "costo_M_litro": 175.0,
    "costo_Y_litro": 175.0,
    "costo_K_litro": 175.0,
    "costo_W_litro": 210.0,
    "consumo_CMYK_mq": 0.006,   # L/mq per 1x CMYK
    "consumo_W_mq": 0.015,      # L/mq per 1W
    "costi_vari_operatore_mq": 0.96,
    "investimento_mq": 1.66,
    "assistenza_ricambi_mq": 0.96,
    "costo_orario_prestampa": 25.0
}

APP_TITLE = "PrintK v 4.0"

# Palette
COLOR_PRIMARY = "#0EA5E9"
COLOR_PRIMARY_DARK = "#0284C7"
COLOR_BG_DARK = "#0B1220"
COLOR_SURFACE_DARK = "#111827"
COLOR_TEXT_LIGHT = "#111827"
COLOR_TEXT_DARK = "#E5E7EB"
COLOR_SURFACE_LIGHT = "#FFFFFF"
COLOR_MUTED_DARK = "#9CA3AF"
COLOR_MUTED_LIGHT = "#6B7280"

# Simple 16x16 gear icon (base64 PNG)
_GEAR_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAvUlEQVQ4T7WTsQ3CMAyFv6bQ"
    "QwWcQzqgJcQG0QZ8g4TkpD9aUuUKYb7cQm0hY0jv8Rr4pEo6LZq0oQ2qgL9i1g0o1nGq0F8Y"
    "l7zC0EwCwJ9cL2Z2cN3dQwQkqQ0wDYF0G8w1H1mWc1Zx4kS2Q2qf5r8a8Jw2iE1v4xw0KkAq"
    "wJ9zVqVJw6w6o6Ckq2rH9f0o7yqC2hLQq2yP8bR0Lq6h7b4OEV4j9wR0pQ1r8i2D2mZ1wqkT"
    "bQf3qgLw0n9c0I1m3oAqEoUu3r9Rk0z0o6f3vR8k8hWwS7g6b1oAAAAAElFTkSuQmCC"
)

# =============================== FORMATTATORI IT ===============================

def format_it(x, dec=2):
    """Formatta con separatore migliaia '.' e decimale ','"""
    try:
        n = float(x)
    except Exception:
        return str(x)
    s = f"{n:,.{dec}f}"             # 12,345.67
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s

def eur(x, dec=2):
    return f"€ {format_it(x, dec)}"

# =============================== UTILS ===============================

def _to_float(s: str) -> float:
    s = (s or "").strip().replace(",", ".")
    return float(s)

def carica_parametri():
    try:
        with open(PERCORSO_FILE_CONFIG, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}
    if "Volume,estimato per anno mq" in data:
        data["volume_annuo_mq"] = data.pop("Volume,estimato per anno mq")
    for k, v in DEFAULT_PARAMETRI.items():
        data.setdefault(k, v)
    for k in list(data.keys()):
        try:
            data[k] = float(data[k])
        except (ValueError, TypeError):
            if isinstance(DEFAULT_PARAMETRI.get(k), (int, float)):
                data[k] = float(DEFAULT_PARAMETRI[k])
    return data

def salva_parametri(parametri: dict):
    with open(PERCORSO_FILE_CONFIG, "w", encoding="utf-8") as f:
        json.dump(parametri, f, indent=4, ensure_ascii=False)

def breakdown_costo(parametri, lung_mm, larg_mm, quantita, cmyk_level, w_level):
    if lung_mm <= 0 or larg_mm <= 0 or quantita <= 0:
        raise ValueError("Valori di lunghezza, larghezza e quantità devono essere > 0.")
    area_mq = (lung_mm / 1000.0) * (larg_mm / 1000.0)
    consumo_cmyk = (parametri["consumo_CMYK_mq"] * area_mq * cmyk_level) if cmyk_level > 0 else 0.0
    consumo_w    = (parametri["consumo_W_mq"]   * area_mq * w_level)    if w_level   > 0 else 0.0
    moltiplicatore_costi = float(w_level + 1)
    base_vari_mq = (parametri["costi_vari_operatore_mq"] + parametri["investimento_mq"] + parametri["assistenza_ricambi_mq"])
    costi_vari = base_vari_mq * area_mq * moltiplicatore_costi
    costo_cmyk = parametri["costo_C_litro"] * consumo_cmyk
    costo_w    = parametri["costo_W_litro"] * consumo_w
    costo_prestampa_unit = parametri["costo_orario_prestampa"] / quantita
    costo_per_pezzo = costo_cmyk + costo_w + costi_vari + costo_prestampa_unit
    totale_commessa = costo_per_pezzo * quantita
    costo_al_mq = (costo_per_pezzo / area_mq) if area_mq > 0 else 0.0
    return {
        "area_mq": area_mq,
        "consumo_cmyk_l": consumo_cmyk,
        "consumo_w_l": consumo_w,
        "costo_cmyk": costo_cmyk,
        "costo_w": costo_w,
        "costi_vari": costi_vari,
        "costo_prestampa_unit": costo_prestampa_unit,
        "costo_per_pezzo": costo_per_pezzo,
        "totale_commessa": totale_commessa,
        "costo_al_mq": costo_al_mq,
        "quantita": int(quantita),
        "w_level": int(w_level),
        "cmyk_level": int(cmyk_level),
        "moltiplicatore_costi": moltiplicatore_costi
    }

# =============================== UI HELPERS ===============================

def _safe_bg(widget, fallback="#F6F8FB"):
    """Ritorna un colore di bg affidabile anche per ttk.* (che non hanno 'bg')."""
    try:
        # per widget Tk classici
        return widget.cget("bg")
    except Exception:
        try:
            # prova con 'background'
            return widget.cget("background")
        except Exception:
            try:
                # prendi il bg del root
                return widget.winfo_toplevel().cget("bg")
            except Exception:
                return fallback

def _lerp_hex_color(c1, c2, t):
    def _hex_to_rgb(h):
        h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    def _rgb_to_hex(r, g, b):
        return f"#{r:02X}{g:02X}{b:02X}"
    r1, g1, b1 = _hex_to_rgb(c1); r2, g2, b2 = _hex_to_rgb(c2)
    r = int(r1 + (r2 - r1) * t); g = int(g1 + (g2 - g1) * t); b = int(b1 + (b2 - b1) * t)
    return _rgb_to_hex(r, g, b)

def draw_vertical_gradient(canvas, width, height, top="#0B1220", bottom="#111827"):
    canvas.delete("grad")
    canvas.configure(background=bottom)
    steps = max(1, height)
    for i in range(steps):
        ratio = i / steps
        c = _lerp_hex_color(top, bottom, ratio)
        canvas.create_rectangle(0, i, width, i+1, outline="", fill=c, tags=("grad",))

class Card(ttk.Frame):
    def __init__(self, master, padding=16, **kw):
        super().__init__(master, **kw)
        self["padding"] = padding
        self["style"] = "Card.TFrame"

class ShadowCard(tk.Frame):
    """Cornice con ombra soft (illusione con due layer) — bg sicuro dal root."""
    def __init__(self, master, padding=16, **kw):
        super().__init__(master, bg=_safe_bg(master), highlightthickness=0, bd=0)
        self._shadow = tk.Frame(self, bg="#D3DEE9")
        self._shadow.pack(fill="both", expand=True, padx=(2,4), pady=(2,4))
        self._card = Card(self._shadow, padding=padding)
        self._card.pack(fill="both", expand=True, padx=(0,2), pady=(0,2))

def add_tooltip(widget, text):
    tip = tk.Toplevel(widget); tip.wm_overrideredirect(True); tip.wm_geometry("0x0+0+0")
    label = tk.Label(tip, text=text, justify="left", background="#111827", foreground="#E5E7EB",
                     relief="solid", borderwidth=1, padx=8, pady=4, font=("Century Gothic", 9))
    label.pack(); tip.withdraw()
    def enter(_):
        tip.deiconify(); x = widget.winfo_rootx() + 10; y = widget.winfo_rooty() + widget.winfo_height() + 8
        tip.wm_geometry(f"+{x}+{y}")
    def leave(_): tip.withdraw()
    widget.bind("<Enter>", enter); widget.bind("<Leave>", leave); return tip

# ------ 3D Pill Button Group ------

class PillGroup:
    def __init__(self, parent, labels, command_on_change,
                 color_active=COLOR_PRIMARY, color_active_hover=COLOR_PRIMARY_DARK):
        self.parent = parent; self.labels = labels; self.command_on_change = command_on_change
        self.color_active = color_active; self.color_active_hover = color_active_hover
        self.value = 0; self.buttons = []; self._build()

    def _build(self):
        for i, lbl in enumerate(self.labels, start=1):
            b = tk.Button(self.parent, text=lbl, font=("Century Gothic", 16, "bold"),
                          relief="raised", bd=3, padx=22, pady=14, cursor="hand2")
            b.grid(row=0, column=i-1, padx=12, pady=10, sticky="nsew")
            b.bind("<Button-1>", lambda e, idx=i: self.toggle(idx))
            b.bind("<Enter>", lambda e, btn=b: self._hover(btn, True))
            b.bind("<Leave>", lambda e, btn=b: self._hover(btn, False))
            add_tooltip(b, f"Seleziona {lbl}. Clicca di nuovo per togliere.")
            self.buttons.append(b)
        for c in range(len(self.labels)): self.parent.columnconfigure(c, weight=1)

    def toggle(self, idx:int):
        self.set(0 if self.value == idx else idx)

    def set(self, idx:int, notify=True):
        self.value = idx
        for i, b in enumerate(self.buttons, start=1):
            if i == idx:
                b.config(bg=self.color_active, fg="white", relief="sunken",
                         activebackground=self.color_active_hover, activeforeground="white")
            else:
                b.config(bg="SystemButtonFace", fg="black", relief="raised", activebackground="SystemButtonFace")
        if notify and self.command_on_change: self.command_on_change(self.value)

    def _hover(self, btn, inside):
        if btn["relief"] == "sunken": btn.config(bg=self.color_active_hover if inside else self.color_active)

    def get(self): return self.value

# ------ Badge pill "Da ricalcolare" ------

class PillBadge(tk.Canvas):
    def __init__(self, master, text="Da ricalcolare", bg="#DC2626", fg="#FFFFFF", **kw):
        super().__init__(master, height=24, bd=0, highlightthickness=0, bg=_safe_bg(master), **kw)
        self._text = text; self._bg = bg; self._fg = fg
        self._draw()

    def _draw(self):
        self.delete("all")
        pad_x = 10; pad_y = 6; r = 12
        t_id = self.create_text(0, 0, text=self._text, fill=self._fg, font=("Century Gothic", 10, "bold"), anchor="nw")
        bbox = self.bbox(t_id)
        w = (bbox[2]-bbox[0]) + pad_x*2; h = (bbox[3]-bbox[1]) + pad_y
        self.config(width=w, height=h)
        self._round_rect(1,1,w-1,h-1,r, fill=self._bg, outline="")
        self.coords(t_id, pad_x, (h - (bbox[3]-bbox[1]))/2)

    def _round_rect(self, x1, y1, x2, y2, r, **kwargs):
        pts = [
            x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r, x2,y2, x2-r,y2,
            x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1
        ]
        return self.create_polygon(pts, smooth=True, **kwargs)

# ------ Toast (notifica non intrusiva) ------

class Toast(tk.Toplevel):
    def __init__(self, master, text, ms=1800):
        super().__init__(master)
        self.overrideredirect(True); self.attributes("-topmost", True)
        frm = tk.Frame(self, bg="#111827"); frm.pack(fill="both", expand=True)
        tk.Label(frm, text=text, bg="#111827", fg="#E5E7EB",
                 font=("Century Gothic", 10), padx=12, pady=8).pack()
        self.update_idletasks()
        x = master.winfo_rootx() + master.winfo_width() - self.winfo_width() - 24
        y = master.winfo_rooty() + master.winfo_height() - self.winfo_height() - 24
        self.geometry(f"+{x}+{y}")
        self.after(ms, self.destroy)

# =============================== WINDOWS (Setup & Report) ===============================

def apri_finestra_setup(root, parametri, theme_ctrl):
    win = tk.Toplevel(root); win.title("Impostazioni"); win.transient(root); win.grab_set()
    win.configure(bg=theme_ctrl.color("surface"))
    header = ttk.Frame(win, padding=(16,12)); header.pack(fill="x")
    ttk.Label(header, text="Impostazioni", font=("Century Gothic", 16, "bold")).pack(side="left")
    shadow = tk.Frame(win, bg="#D3DEE9"); shadow.pack(fill="both", expand=True, padx=(18,20), pady=(10,18))
    body = Card(shadow, padding=16); body.pack(fill="both", expand=True, padx=(0,2), pady=(0,2))
    wrap = ttk.Frame(body); wrap.pack(fill="both", expand=True)

    rows = [
        ("Volume annuo stimato (mq)", "volume_annuo_mq"),
        ("Costo C medio (€/L)", "costo_C_litro"),
        ("Costo M medio (€/L)", "costo_M_litro"),
        ("Costo Y medio (€/L)", "costo_Y_litro"),
        ("Costo K medio (€/L)", "costo_K_litro"),
        ("Costo W (€/L)", "costo_W_litro"),
        ("Consumo CMYK (L/mq)", "consumo_CMYK_mq"),
        ("Consumo W base (L/mq)", "consumo_W_mq"),
        ("Costi operatore (€/mq)", "costi_vari_operatore_mq"),
        ("Investimento (€/mq)", "investimento_mq"),
        ("Assistenza/Ricambi (€/mq)", "assistenza_ricambi_mq"),
        ("Prestampa (€/h)", "costo_orario_prestampa"),
    ]

    edit_vars = {}
    for i, (lbl, key) in enumerate(rows):
        ttk.Label(wrap, text=lbl).grid(row=i, column=0, sticky="w", padx=(0,10), pady=6)
        sv = tk.StringVar(value=str(parametri.get(key, DEFAULT_PARAMETRI[key])))
        ent = ttk.Entry(wrap, textvariable=sv, font=("Century Gothic", 12))
        ent.grid(row=i, column=1, sticky="ew", pady=6)
        add_tooltip(ent, f"Inserisci {lbl.lower()}.")
        wrap.columnconfigure(1, weight=1)
        edit_vars[key] = sv

    btns = ttk.Frame(win, padding=(16,0)); btns.pack(fill="x", pady=8)
    def salva():
        try:
            for k, var in edit_vars.items(): parametri[k] = _to_float(var.get())
            salva_parametri(parametri); messagebox.showinfo("Salvataggio", "Modifiche salvate con successo."); win.destroy()
        except ValueError: messagebox.showerror("Errore", "Valori non validi. Controlla i campi numerici.")

    b_ann = ttk.Button(btns, text="Annulla", command=win.destroy)
    b_sal = ttk.Button(btns, text="Salva", style="Accent.TButton", command=salva)
    b_ann.pack(side="right"); b_sal.pack(side="right", padx=(0,8))
    add_tooltip(b_sal, "Salva i parametri di stampa."); add_tooltip(b_ann, "Chiudi senza salvare.")

def apri_finestra_report(root, details, theme_ctrl):
    win = tk.Toplevel(root); win.title("Report calcolo"); win.transient(root)
    win.configure(bg=theme_ctrl.color("surface"))
    header = ttk.Frame(win, padding=(16,12)); header.pack(fill="x")
    ttk.Label(header, text="Report Calcolo Area, Consumi e Costi", font=("Century Gothic", 16, "bold")).pack(side="left")

    shadow = tk.Frame(win, bg="#D3DEE9"); shadow.pack(fill="both", expand=True, padx=(18,20), pady=(10,18))
    body = Card(shadow, padding=16); body.pack(fill="both", expand=True, padx=(0,2), pady=(0,2))

    tv = ttk.Treeview(body, columns=("k","v"), show="headings")
    tv.heading("k", text="Voce"); tv.heading("v", text="Valore")
    tv.column("k", anchor="w", width=360, stretch=True); tv.column("v", anchor="e", width=180, stretch=True)
    tv.pack(fill="both", expand=True, padx=6, pady=6)

    def add(k, v): tv.insert("", "end", values=(k, v))

    add("Quantità", f"{details['quantita']}")
    add("Superficie per pezzo (mq)", format_it(details['area_mq'], 3))
    if details["cmyk_level"] > 0:
        add("Passaggi CMYK", f"{details['cmyk_level']}×")
        add("Consumo CMYK per pezzo (L)", format_it(details['consumo_cmyk_l'], 3))
        add("Costo CMYK per pezzo (€)", eur(details['costo_cmyk']))
    if details["w_level"] > 0:
        add("Strati W", f"{details['w_level']}W")
        add("Consumo W per pezzo (L)", format_it(details['consumo_w_l'], 3))
        add("Costo W per pezzo (€)", eur(details['costo_w']))
        add("Moltiplicatore costi vari", f"{details['moltiplicatore_costi']:.0f}×")
    add("Costi vari per pezzo (€)", eur(details['costi_vari']))
    add("Prestampa allocata per pezzo (€)", eur(details['costo_prestampa_unit']))
    add("Costo per pezzo (€)", eur(details['costo_per_pezzo']))
    add("€/mq (per pezzo)", eur(details['costo_al_mq']))
    ttk.Button(win, text="Chiudi", command=win.destroy).pack(pady=(0,12))

# =============================== THEME CONTROLLER ===============================

class ThemeController:
    def __init__(self, root):
        self.root = root; self.dark = False; self.style = ttk.Style(root)
        try: self.style.configure(".", font=("Century Gothic", 11))
        except Exception: pass
        self.apply_light()

    def color(self, key):
        if self.dark:
            mapping = {"bg": COLOR_BG_DARK, "surface": COLOR_SURFACE_DARK, "text": COLOR_TEXT_DARK,
                       "muted": COLOR_MUTED_DARK, "accent": COLOR_PRIMARY, "accent_hover": COLOR_PRIMARY_DARK}
        else:
            mapping = {"bg": "#EEF6FB", "surface": COLOR_SURFACE_LIGHT, "text": COLOR_TEXT_LIGHT,
                       "muted": COLOR_MUTED_LIGHT, "accent": COLOR_PRIMARY, "accent_hover": COLOR_PRIMARY_DARK}
        return mapping[key]

    def _base_style(self):
        fg = self.color("text"); surf = self.color("surface")
        self.style.configure("TFrame", background=self.color("bg"))
        self.style.configure("Card.TFrame", background=surf, relief="flat", borderwidth=0)
        self.style.configure("TLabel", background=surf, foreground=fg)
        self.style.configure("TEntry", fieldbackground=surf, background=surf, foreground=fg)
        self.style.configure("TSpinbox", fieldbackground=surf, background=surf, foreground=fg)
        self.style.configure("Treeview", background=surf, fieldbackground=surf, foreground=fg)
        self.style.configure("TCheckbutton", background=self.color("bg"), foreground=fg)
        self.style.configure("TRadiobutton", background=self.color("bg"), foreground=fg)
        self.style.configure("TButton", padding=8)
        self.style.configure("Accent.TButton", padding=10, foreground="#FFFFFF", background=self.color("accent"))
        self.style.map("Accent.TButton", background=[("active", self.color("accent_hover"))])

        # ====== Focus outline chiaro ======
        self.style.map("TEntry",
            fieldbackground=[("focus", "#FFF7E6")],
            foreground=[("focus", self.color("text"))]
        )
        self.style.map("TSpinbox",
            fieldbackground=[("focus", "#FFF7E6")],
            foreground=[("focus", self.color("text"))]
        )
        self.style.map("TButton",
            background=[("focus", self.color("accent_hover")), ("active", self.color("accent_hover"))],
            foreground=[("focus", "#FFFFFF")]
        )
        self.style.map("Accent.TButton",
            background=[("focus", self.color("accent_hover")), ("active", self.color("accent_hover"))]
        )
        self.style.map("TCheckbutton",
            foreground=[("focus", self.color("accent"))]
        )
        self.style.map("TRadiobutton",
            foreground=[("focus", self.color("accent"))]
        )
        self.style.map("Treeview",
            background=[("focus", "#F0F9FF")]
        )

        # ====== Badge styles ======
        self.style.configure("Badge.Danger.TLabel", background="#DC2626", foreground="#FFFFFF", padding=4)
        self.style.configure("Badge.Success.TLabel", background="#059669", foreground="#FFFFFF", padding=4)

    def apply_dark(self):
        self.dark = True
        try:
            if "clam" in self.style.theme_names(): self.style.theme_use("clam")
        except Exception: pass
        self._base_style(); self.root.configure(bg=self.color("bg"))

    def apply_light(self):
        self.dark = False
        try:
            if "clam" in self.style.theme_names(): self.style.theme_use("clam")
        except Exception: pass
        self._base_style(); self.root.configure(bg=self.color("bg"))

# =============================== APP ===============================

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)

        # --- Fullscreen: all'avvio e scorciatoie ---
        self._is_fullscreen = False
        self._enter_fullscreen()  # parte già a schermo intero
        self.bind("<F11>", self._toggle_fullscreen)  # toggle
        self.bind("<Escape>", self._exit_fullscreen) # esci

        # Icona
        try:
            data = base64.b64decode(_GEAR_B64); self._icon_img = tk.PhotoImage(data=data); self.iconphoto(True, self._icon_img)
        except Exception: pass

        self.parametri = carica_parametri()
        self.theme = ThemeController(self)

        # Stato calcolo/dirty
        self._has_result = False
        self._dirty_after_calc = False
        self._alert_shown = False

        # BACKDROP con gradiente (Canvas a piena finestra)
        self.bg_canvas = tk.Canvas(self, highlightthickness=0, bd=0)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        # stage dentro il canvas
        self.stage = ttk.Frame(self.bg_canvas)
        self.bg_item = self.bg_canvas.create_window(0, 0, window=self.stage, anchor="nw")
        # ridisegna su qualunque resize
        self.bind("<Configure>", self._redraw_bg)
        self.bg_canvas.bind("<Configure>", self._redraw_bg)

        # TOP BAR
        self._build_topbar(self.stage)

        # CONTENUTO principale con ombra morbida
        content_outer = tk.Frame(self.stage, bg="#D3DEE9")
        content_outer.pack(fill="both", expand=True, padx=(18,20), pady=(6,18))
        content = Card(content_outer, padding=16)
        content.pack(fill="both", expand=True, padx=(0,2), pady=(0,2))

        # Griglia responsive
        content.columnconfigure(0, weight=1, uniform="col")
        content.columnconfigure(1, weight=1, uniform="col")
        content.rowconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)

        # Inchiostri (ShadowCard)
        ink_outer = tk.Frame(content, bg="#D3DEE9")
        ink_outer.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0,12))
        ink_wrap = ShadowCard(ink_outer, padding=22)
        ink_wrap.pack(fill="both", expand=True)
        self.card_ink = ink_wrap._card
        self._build_ink(self.card_ink)

        # Misure (ShadowCard)
        mis_outer = tk.Frame(content, bg="#D3DEE9")
        mis_outer.grid(row=1, column=0, sticky="nsew", padx=(0,8))
        mis_outer.grid_rowconfigure(0, weight=1); mis_outer.grid_columnconfigure(0, weight=1)
        mis_wrap = ShadowCard(mis_outer, padding=22)
        mis_wrap.pack(fill="both", expand=True)
        self.card_misure = mis_wrap._card
        self._build_misure(self.card_misure)

        # Colonna destra
        right_col = ttk.Frame(content)
        right_col.grid(row=1, column=1, sticky="nsew", padx=(8,0))
        right_col.rowconfigure(0, weight=0)
        right_col.rowconfigure(1, weight=1)
        right_col.columnconfigure(0, weight=1)

        # Azioni (ShadowCard)
        az_outer = tk.Frame(right_col, bg="#D3DEE9")
        az_outer.grid(row=0, column=0, sticky="nsew", pady=(0,8))
        az_wrap = ShadowCard(az_outer, padding=18)
        az_wrap.pack(fill="both", expand=True)
        self.card_azioni = az_wrap._card
        self._build_actions(self.card_azioni)

        # Risultato (ShadowCard)
        self.res_outer = tk.Frame(right_col, bg="#D3DEE9")
        self.res_outer.grid(row=1, column=0, sticky="nsew")
        self.res_outer.grid_rowconfigure(0, weight=1); self.res_outer.grid_columnconfigure(0, weight=1)
        res_wrap = ShadowCard(self.res_outer, padding=18)
        res_wrap.pack(fill="both", expand=True)
        self.card_result = res_wrap._card
        self._build_result(self.card_result)

        # Shortcuts
        self.bind("<Return>", lambda e: self.esegui_calcolo())
        self.bind("<Control-i>", lambda e: self.open_setup())
        self.bind("<Control-I>", lambda e: self.open_setup())
        self.bind("<Control-l>", lambda e: self.theme.apply_light())
        self.bind("<Control-L>", lambda e: self.theme.apply_light())
        self.bind("<Control-d>", lambda e: self.theme.apply_dark())
        self.bind("<Control-D>", lambda e: self.theme.apply_dark())

        self.ent_lung.focus_set()
        self.after(10, self._redraw_bg)

    # ---------- Fullscreen helpers ----------
    def _enter_fullscreen(self):
        if sys.platform.startswith("win"):
            try:
                self.state("zoomed")
            except Exception:
                self.attributes("-fullscreen", True)
                self._is_fullscreen = True
        else:
            self.attributes("-fullscreen", True)
            self._is_fullscreen = True

    def _toggle_fullscreen(self, event=None):
        self._is_fullscreen = not getattr(self, "_is_fullscreen", False)
        if sys.platform.startswith("win"):
            self.state("zoomed" if self._is_fullscreen else "normal")
        else:
            self.attributes("-fullscreen", self._is_fullscreen)
        return "break"

    def _exit_fullscreen(self, event=None):
        self._is_fullscreen = False
        if sys.platform.startswith("win"):
            self.state("normal")
        else:
            self.attributes("-fullscreen", False)
        return "break"

    # ---------- Top Bar ----------
    def _build_topbar(self, parent):
        bar = ttk.Frame(parent, padding=(16,12)); bar.pack(fill="x")
        left = ttk.Frame(bar); left.pack(side="left")
        ttk.Label(left, text=APP_TITLE, font=("Century Gothic", 24, "bold")).pack(side="left")
        right = ttk.Frame(bar); right.pack(side="right")
        self.theme_var = tk.BooleanVar(value=False)
        dark_chk = ttk.Checkbutton(right, text="Dark", variable=self.theme_var, command=self._toggle_theme)
        dark_chk.pack(side="right", padx=(10,0)); add_tooltip(dark_chk, "Attiva/disattiva il tema scuro.")

        img = None
        try: img = tk.PhotoImage(data=base64.b64decode(_GEAR_B64))
        except Exception: pass
        btn = ttk.Button(right, text="⚙️  Impostazioni", image=img, compound="left",
                         style="Accent.TButton", command=self.open_setup)
        btn.image = img; btn.pack(side="right"); add_tooltip(btn, "Apri le impostazioni della macchina/costi.")

        sep = ttk.Separator(parent, orient="horizontal")
        sep.pack(fill="x", padx=16, pady=(4,0))

    def _toggle_theme(self):
        self.theme.apply_dark() if self.theme_var.get() else self.theme.apply_light()
        self._redraw_bg()

    # ---------- Placeholder helper ----------
    def _set_placeholder(self, entry, text):
        try:
            entry.insert(0, text)
            entry.config(foreground="#9CA3AF")
        except Exception:
            try:
                entry.insert(0, text)
            except Exception:
                pass
        def on_focus_in(e):
            try:
                if entry.get() == text:
                    entry.delete(0, "end")
                    entry.config(foreground="#111827")
            except Exception:
                pass
        def on_focus_out(e):
            try:
                if not entry.get():
                    entry.insert(0, text)
                    entry.config(foreground="#9CA3AF")
            except Exception:
                pass
        entry.bind("<FocusIn>", on_focus_in); entry.bind("<FocusOut>", on_focus_out)

    # ---------- Inchiostri ----------
    def _build_ink(self, parent):
        title = ttk.Label(parent, text="Inchiostri / Strati", font=("Century Gothic", 20, "bold"))
        title.pack(anchor="w", pady=(0,8)); add_tooltip(title, "Configura i passaggi CMYK e gli strati di Bianco (W).")
        ttk.Label(parent, text="Clicca per attivare. Riclicca sul pulsante attivo per disattivare.",
                  font=("Century Gothic", 12)).pack(anchor="w", pady=(0,12))

        wrap = ttk.Frame(parent); wrap.pack(fill="both", expand=True)
        cmyk_head = ttk.Frame(wrap); cmyk_head.grid(row=0, column=0, sticky="w")
        lab_cmyk = ttk.Label(cmyk_head, text="Passaggi CMYK", font=("Century Gothic", 14, "bold"))
        lab_cmyk.pack(side="left", pady=(0,6)); add_tooltip(lab_cmyk, "Numero di passate CMYK.")
        cmyk_row = tk.Frame(wrap, bd=0); cmyk_row.grid(row=1, column=0, sticky="nsew")
        self.cmyk_group = PillGroup(cmyk_row, labels=["1× CMYK","2× CMYK","3× CMYK","4× CMYK","5× CMYK","6× CMYK"],
                                    command_on_change=lambda v: self._on_input_changed())

        w_head = ttk.Frame(wrap); w_head.grid(row=2, column=0, sticky="w", pady=(16,0))
        lab_w = ttk.Label(w_head, text="Strati Bianco (W)", font=("Century Gothic", 14, "bold"))
        lab_w.pack(side="left"); add_tooltip(lab_w, "Numero di strati di bianco coprente.")
        w_row = tk.Frame(wrap, bd=0); w_row.grid(row=3, column=0, sticky="nsew")
        self.w_group = PillGroup(w_row, labels=["1W","2W","3W","4W","5W","6W"],
                                 command_on_change=lambda v: self._on_input_changed())
        wrap.columnconfigure(0, weight=1)

    # ---------- Misure ----------
    def _build_misure(self, parent):
        lab_title = ttk.Label(parent, text="Dimensioni e Quantità", font=("Century Gothic", 18, "bold"))
        lab_title.pack(anchor="w", pady=(0,10)); add_tooltip(lab_title, "Inserisci le dimensioni del pezzo e la quantità.")
        grid = ttk.Frame(parent); grid.pack(fill="both", expand=True)
        for r in range(3): grid.rowconfigure(r, weight=1)
        grid.columnconfigure(0, weight=0); grid.columnconfigure(1, weight=1)
        lab_font=("Century Gothic",14); ent_font=("Century Gothic",18)

        l1 = ttk.Label(grid, text="Lunghezza (mm)", font=lab_font); l1.grid(row=0,column=0,sticky="w",pady=8)
        add_tooltip(l1,"Lato lungo in millimetri.")
        self.var_lung = tk.StringVar(); self.ent_lung = ttk.Entry(grid, textvariable=self.var_lung, font=ent_font)
        self.ent_lung.grid(row=0,column=1,sticky="ew",padx=(10,16),pady=8); self.ent_lung.bind("<KeyRelease>", lambda e: self._on_input_changed())
        add_tooltip(self.ent_lung,"Digita la lunghezza (mm).")

        l2 = ttk.Label(grid, text="Larghezza (mm)", font=lab_font); l2.grid(row=1,column=0,sticky="w",pady=8)
        add_tooltip(l2,"Lato corto in millimetri.")
        self.var_larg = tk.StringVar(); self.ent_larg = ttk.Entry(grid, textvariable=self.var_larg, font=ent_font)
        self.ent_larg.grid(row=1,column=1,sticky="ew",padx=(10,16),pady=8); self.ent_larg.bind("<KeyRelease>", lambda e: self._on_input_changed())
        add_tooltip(self.ent_larg,"Digita la larghezza (mm).")

        l3 = ttk.Label(grid, text="Quantità", font=lab_font); l3.grid(row=2,column=0,sticky="w",pady=8)
        add_tooltip(l3,"Numero di pezzi da produrre.")
        self.var_qta = tk.StringVar(value="1"); self.ent_qta = ttk.Entry(grid, textvariable=self.var_qta, font=ent_font)
        self.ent_qta.grid(row=2,column=1,sticky="ew",padx=(10,16),pady=8); self.ent_qta.bind("<KeyRelease>", lambda e: self._on_input_changed())
        add_tooltip(self.ent_qta,"Digita la quantità pezzi.")

        # placeholders sicuri
        self._set_placeholder(self.ent_lung, "es. 250")
        self._set_placeholder(self.ent_larg, "es. 120")
        self._set_placeholder(self.ent_qta,  "es. 50")

        # focus ring blu
        def _focus_ring_on(w):
            try: w.configure(highlightthickness=2, highlightbackground="#2563EB", highlightcolor="#2563EB")
            except Exception: pass
        def _focus_ring_off(w):
            try: w.configure(highlightthickness=1, highlightbackground="#CBD5E1")
            except Exception: pass
        for w in (self.ent_lung, self.ent_larg, self.ent_qta):
            try: w.configure(highlightthickness=1, highlightbackground="#CBD5E1")
            except Exception: pass
            w.bind("<FocusIn>",  lambda e, ww=w: _focus_ring_on(ww))
            w.bind("<FocusOut>", lambda e, ww=w: _focus_ring_off(ww))

    # ---------- Azioni ----------
    def _build_actions(self, parent):
        lab = ttk.Label(parent, text="Azioni", font=("Century Gothic",16,"bold")); lab.pack(anchor="w", pady=(0,8))
        add_tooltip(lab,"Comandi principali.")
        row1 = ttk.Frame(parent); row1.pack(fill="x", expand=True)
        calc = ttk.Button(row1, text="🧮  Calcola", style="Accent.TButton", command=self.esegui_calcolo)
        calc.pack(side="left"); add_tooltip(calc,"Esegui il calcolo (Invio).")
        setup = ttk.Button(row1, text="⚙️  Impostazioni", command=self.open_setup)
        setup.pack(side="left", padx=8); add_tooltip(setup,"Modifica i parametri di costo e consumo.")
        row2 = ttk.Frame(parent); row2.pack(fill="x", pady=(12,0))
        ttk.Label(row2, text="Margine % (prezzo vendita)", font=("Century Gothic", 12)).pack(side="left")
        self.var_margin = tk.StringVar(value="35")

        # ttk.Spinbox fallback a tk.Spinbox se assente
        try:
            sp = ttk.Spinbox(row2, from_=0, to=500, increment=1, width=6, textvariable=self.var_margin, justify="center")
        except Exception:
            sp = tk.Spinbox(row2, from_=0, to=500, increment=1, width=6, textvariable=self.var_margin, justify="center")
        sp.pack(side="left", padx=(8,0)); self.var_margin.trace_add("write", lambda *_: self._on_input_changed())
        add_tooltip(sp,"Percentuale di ricarico sul costo totale.")

        # focus ring anche sullo Spinbox
        def _focus_ring_on(w):
            try: w.configure(highlightthickness=2, highlightbackground="#2563EB", highlightcolor="#2563EB")
            except Exception: pass
        def _focus_ring_off(w):
            try: w.configure(highlightthickness=1, highlightbackground="#CBD5E1")
            except Exception: pass
        try: sp.configure(highlightthickness=1, highlightbackground="#CBD5E1")
        except Exception: pass
        sp.bind("<FocusIn>",  lambda e, ww=sp: _focus_ring_on(ww))
        sp.bind("<FocusOut>", lambda e, ww=sp: _focus_ring_off(ww))

        hint = ttk.Label(parent, text="Ctrl+D (Dark) / Ctrl+L (Light).", foreground=ThemeController(self).color("muted"))
        hint.pack(anchor="w", pady=(12,0)); add_tooltip(hint,"Scorciatoie per cambiare tema.")

    # ---------- Risultato ----------
    def _build_result(self, parent):
        header = ttk.Frame(parent); header.pack(fill="x", pady=(0,8))
        ttk.Label(header, text="Risultato", font=("Century Gothic", 16, "bold")).pack(side="left")
        self.badge_dirty = PillBadge(header, text="Da ricalcolare")
        self.badge_dirty.place_forget()
        add_tooltip(header, "Il badge rosso indica che devi ricalcolare.")

        self.var_totale_commessa = tk.StringVar(value="—")
        big = ttk.Frame(parent); big.pack(fill="x", pady=(6,10))
        ttk.Label(big, text="Totale commessa (costo):", font=("Century Gothic", 13, "bold")).pack(side="left")
        total = ttk.Entry(big, textvariable=self.var_totale_commessa, font=("Century Gothic", 19, "bold"),
                          state="readonly", justify="center")
        total.pack(side="right"); add_tooltip(total,"Costo totale di produzione della commessa.")

        self.var_totale_vendita = tk.StringVar(value="—")
        big2 = ttk.Frame(parent); big2.pack(fill="x", pady=(0,12))
        ttk.Label(big2, text="Prezzo di vendita (totale):", font=("Century Gothic", 13, "bold")).pack(side="left")
        total_sell = ttk.Entry(big2, textvariable=self.var_totale_vendita, font=("Century Gothic", 19, "bold"),
                               state="readonly", justify="center")
        total_sell.pack(side="right"); add_tooltip(total_sell,"Totale venduto = costo × (1 + margine%).")

        self.var_costo_pz = tk.StringVar(value="—")
        self.var_costo_mq = tk.StringVar(value="—")
        self.var_pv_pz = tk.StringVar(value="—")

        sub1 = ttk.Frame(parent); sub1.pack(fill="x")
        ttk.Label(sub1, text="€/pz (costo):", font=("Century Gothic", 12)).pack(side="left")
        lab_cpz = ttk.Label(sub1, textvariable=self.var_costo_pz, font=("Century Gothic", 13, "bold"))
        lab_cpz.pack(side="left", padx=(6,16)); add_tooltip(lab_cpz,"Costo per singolo pezzo.")
        ttk.Label(sub1, text="€/mq (costo per pezzo):", font=("Century Gothic", 12)).pack(side="left")
        lab_cmq = ttk.Label(sub1, textvariable=self.var_costo_mq, font=("Century Gothic", 13, "bold"))
        lab_cmq.pack(side="left", padx=6); add_tooltip(lab_cmq,"Costo per metro quadro del singolo pezzo.")

        sub2 = ttk.Frame(parent); sub2.pack(fill="x", pady=(6,0))
        ttk.Label(sub2, text="€/pz (vendita):", font=("Century Gothic", 12)).pack(side="left")
        lab_pvpz = ttk.Label(sub2, textvariable=self.var_pv_pz, font=("Century Gothic", 13, "bold"))
        lab_pvpz.pack(side="left", padx=(6,16)); add_tooltip(lab_pvpz,"Prezzo di vendita per pezzo.")

        rep = ttk.Button(parent, text="📊  Apri report dettagliato", command=self.open_report)
        rep.pack(pady=(12,0)); add_tooltip(rep,"Mostra il dettaglio di superfici, consumi e costi.")
        self.btn_report = rep

    # ---------- Gestione "dirty" ----------
    def _on_input_changed(self):
        if not self._has_result or self._dirty_after_calc: return
        self._dirty_after_calc = True
        self.res_outer.configure(bg="#FBEAEA")
        header = self.card_result.winfo_children()[0]
        self.badge_dirty.place(in_=header, relx=1.0, x=-4, y=0, anchor="ne")
        if not self._alert_shown:
            self._alert_shown = True
            messagebox.showwarning("Valori modificati",
                                   "Hai cambiato dei parametri dopo il calcolo.\nPremi «🧮 Calcola» per aggiornare i risultati.")
        try: self.btn_report.config(state="disabled")
        except Exception: pass

    def _clear_dirty(self):
        self._dirty_after_calc = False; self._alert_shown = False
        self.res_outer.configure(bg="#D3DEE9"); self.badge_dirty.place_forget()
        try: self.btn_report.config(state="normal")
        except Exception: pass

    # ---------- Actions ----------
    def open_setup(self): apri_finestra_setup(self, self.parametri, self.theme)

    def open_report(self):
        if not hasattr(self, "_last_details"):
            messagebox.showinfo("Informazione", "Calcola prima un risultato per vedere il report."); return
        if self._dirty_after_calc:
            messagebox.showwarning("Da ricalcolare", "I valori sono cambiati. Premi «🧮 Calcola» e poi riapri il report."); return
        apri_finestra_report(self, self._last_details, self.theme)

    def esegui_calcolo(self):
        prog = ttk.Progressbar(self.card_result, mode="indeterminate", length=140, maximum=60)
        prog.pack(pady=(0,8)); prog.start(18); self.card_result.update_idletasks()
        try:
            lung = _to_float(self.var_lung.get()); larg = _to_float(self.var_larg.get()); qta = _to_float(self.var_qta.get())
            if lung <= 0 or larg <= 0 or qta <= 0: raise ValueError
            cmyk_level = self.cmyk_group.get(); w_level = self.w_group.get()
            details = breakdown_costo(self.parametri, lung_mm=lung, larg_mm=larg, quantita=qta,
                                      cmyk_level=cmyk_level, w_level=w_level)
            self._last_details = details

            # costo (formattazione italiana)
            self.var_totale_commessa.set(eur(details['totale_commessa']))
            self.var_costo_pz.set(eur(details['costo_per_pezzo']))
            self.var_costo_mq.set(eur(details['costo_al_mq']))

            # prezzo vendita con margine %
            try: marg = max(0.0, _to_float(self.var_margin.get()))
            except Exception: marg = 0.0
            pv_tot = details['totale_commessa'] * (1.0 + marg/100.0)
            pv_pz  = pv_tot / details['quantita']
            self.var_totale_vendita.set(eur(pv_tot))
            self.var_pv_pz.set(eur(pv_pz))

            self._has_result = True
            self._clear_dirty()
            Toast(self, "✅ Calcolo aggiornato")
        except ValueError:
            messagebox.showerror("Errore", "Inserisci valori validi per lunghezza, larghezza e quantità (maggiore di 0).")
        finally:
            try: prog.stop(); prog.destroy()
            except Exception: pass

    # ---------- Background / adattamento ----------
    def _redraw_bg(self, event=None):
        w = self.bg_canvas.winfo_width() or self.winfo_width() or 960
        h = self.bg_canvas.winfo_height() or self.winfo_height() or 650
        if self.theme.dark: top, bottom = COLOR_BG_DARK, COLOR_SURFACE_DARK
        else:               top, bottom = "#E8F4FC", "#F6F8FB"
        self.configure(bg=bottom)
        draw_vertical_gradient(self.bg_canvas, w, h, top=top, bottom=bottom)
        self.bg_canvas.itemconfig(self.bg_item, width=w, height=h)
        self.stage.configure(width=w, height=h)

# =============================== MAIN ===============================

if __name__ == "__main__":
    app = App()
    app.mainloop()
