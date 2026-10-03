"""Styles frontend professionnels — aucune logique métier."""

CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --navy: #0f172a;
        --navy-hover: #1e293b;
        --slate-50: #f8fafc;
        --slate-100: #f1f5f9;
        --slate-200: #e2e8f0;
        --slate-400: #94a3b8;
        --slate-500: #64748b;
        --slate-600: #475569;
        --slate-700: #334155;
        --white: #ffffff;
        --radius: 10px;
        --radius-lg: 14px;
        --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.04);
        --shadow-md: 0 4px 16px rgba(15, 23, 42, 0.06);
    }

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    .stApp {
        background: var(--slate-50) !important;
    }

    /* Masquer éléments Streamlit */
    [data-testid="stDeployButton"], .stAppDeployButton,
    [data-testid="stToolbarActions"], #MainMenu, footer {
        display: none !important;
        visibility: hidden !important;
    }

    header[data-testid="stHeader"] {
        background: transparent !important;
        height: auto !important;
        min-height: 0 !important;
        border: none !important;
        z-index: 1000 !important;
        position: relative !important;
    }

    /* Bouton ouvrir/fermer la barre latérale — visible, sous la navbar */
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapseButton"],
    button[kind="header"][data-testid="stBaseButton-headerNoPadding"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        margin-top: 4.25rem !important;
        margin-left: 0.65rem !important;
        z-index: 1001 !important;
        background: var(--white) !important;
        border: 1px solid var(--slate-200) !important;
        border-radius: 8px !important;
        width: 2.4rem !important;
        height: 2.4rem !important;
        min-width: 2.4rem !important;
        min-height: 2.4rem !important;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.12) !important;
        color: var(--navy) !important;
        align-items: center !important;
        justify-content: center !important;
        transition: background 0.15s ease, border-color 0.15s ease !important;
    }

    [data-testid="collapsedControl"]:hover,
    [data-testid="stSidebarCollapseButton"]:hover,
    button[kind="header"][data-testid="stBaseButton-headerNoPadding"]:hover {
        background: var(--slate-50) !important;
        border-color: var(--slate-400) !important;
    }

    [data-testid="collapsedControl"] svg,
    [data-testid="stSidebarCollapseButton"] svg,
    button[kind="header"][data-testid="stBaseButton-headerNoPadding"] svg {
        width: 1.15rem !important;
        height: 1.15rem !important;
        stroke: var(--navy) !important;
    }

    /* Layout principal */
    .block-container {
        max-width: 1100px !important;
        padding-top: 0.5rem !important;
        padding-bottom: 2rem !important;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: var(--white) !important;
        border-right: 1px solid var(--slate-200) !important;
        box-shadow: 2px 0 12px rgba(15, 23, 42, 0.03) !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 3.5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    [data-testid="stSidebar"] hr {
        margin: 1rem 0 !important;
        border-color: var(--slate-200) !important;
    }

    /* Labels sections sidebar */
    .sidebar-section-label {
        font-size: 0.68rem;
        font-weight: 700;
        color: var(--slate-500);
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin: 0.75rem 0 0.5rem 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .sidebar-section-label span.hint {
        font-size: 0.62rem;
        font-weight: 500;
        color: var(--slate-400);
        letter-spacing: 0;
        text-transform: none;
    }

    .sidebar-empty-box {
        font-size: 0.78rem;
        color: var(--slate-500);
        background: var(--slate-50);
        border: 1px solid var(--slate-200);
        border-radius: var(--radius);
        padding: 0.85rem 1rem;
        text-align: center;
        line-height: 1.45;
    }

    .sidebar-guest-card {
        background: var(--slate-50);
        border: 1px solid var(--slate-200);
        border-radius: var(--radius-lg);
        padding: 1rem;
        margin-top: 0.5rem;
    }

    .sidebar-guest-card .title {
        font-weight: 700;
        font-size: 0.82rem;
        color: var(--navy);
        margin-bottom: 0.35rem;
    }

    .sidebar-guest-card .desc {
        font-size: 0.72rem;
        color: var(--slate-600);
        line-height: 1.45;
    }

    /* Top navbar — pleine largeur, style DataInsight */
    div[data-testid="stHorizontalBlock"]:has(.app-navbar) {
        background: var(--white);
        border-bottom: 1px solid var(--slate-200);
        margin: -0.5rem -5rem 0.75rem -5rem !important;
        padding: 0.75rem 2rem 0.85rem 2rem !important;
        box-shadow: var(--shadow-sm);
        align-items: center !important;
    }

    div[data-testid="stHorizontalBlock"]:has(.app-navbar) [data-testid="column"]:last-child {
        display: flex;
        justify-content: flex-end;
        align-items: center;
    }

    div[data-testid="stHorizontalBlock"]:has(.app-navbar) > [data-testid="column"]:last-child
    > div > [data-testid="stHorizontalBlock"] {
        gap: 0.65rem !important;
        justify-content: flex-end !important;
        align-items: center !important;
        flex-wrap: nowrap !important;
    }

    div[data-testid="stHorizontalBlock"]:has(.app-navbar) [data-testid="column"]:last-child .stButton {
        width: auto !important;
        min-width: fit-content !important;
    }

    div[data-testid="stHorizontalBlock"]:has(.app-navbar) [data-testid="column"]:last-child .stButton > button {
        border-radius: 8px !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        padding: 0.45rem 1.05rem !important;
        white-space: nowrap !important;
        width: auto !important;
        min-width: max-content !important;
        line-height: 1.2 !important;
    }

    div[data-testid="stHorizontalBlock"]:has(.app-navbar) [data-testid="column"]:last-child .stButton > button p {
        white-space: nowrap !important;
        word-break: keep-all !important;
    }

    div[data-testid="stHorizontalBlock"]:has(.app-navbar) [data-testid="column"]:last-child
    .stButton > button[kind="primary"],
    div[data-testid="stHorizontalBlock"]:has(.app-navbar) [data-testid="column"]:last-child
    .stButton > button[data-testid="stBaseButton-primary"] {
        background: var(--navy) !important;
        color: white !important;
        border: none !important;
    }

    div[data-testid="stHorizontalBlock"]:has(.app-navbar) [data-testid="column"]:last-child
    .stButton > button:not([kind="primary"]):not([data-testid="stBaseButton-primary"]) {
        background: var(--white) !important;
        color: var(--navy) !important;
        border: 1px solid var(--slate-200) !important;
    }

    .app-navbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .app-brand {
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .app-brand-icon {
        background: var(--navy);
        color: white;
        border-radius: 8px;
        width: 34px;
        height: 34px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem;
        font-weight: 700;
        flex-shrink: 0;
    }

    .app-brand-name {
        font-weight: 700;
        font-size: 0.95rem;
        color: var(--navy);
        line-height: 1.15;
    }

    .app-brand-tagline {
        font-size: 0.7rem;
        color: var(--slate-500);
        font-weight: 500;
    }

    .nav-guest-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        background: var(--slate-100);
        color: var(--slate-600);
        border: 1px solid var(--slate-200);
        border-radius: 999px;
        padding: 0.35rem 0.85rem;
        font-size: 0.75rem;
        font-weight: 500;
        white-space: nowrap;
    }

    .nav-user-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        background: var(--white);
        border: 1px solid var(--slate-200);
        border-radius: 999px;
        padding: 0.25rem 0.85rem 0.25rem 0.3rem;
        font-size: 0.82rem;
        font-weight: 500;
        color: var(--navy);
    }

    .nav-user-avatar {
        background: var(--navy);
        color: var(--white);
        border-radius: 50%;
        width: 1.65rem;
        height: 1.65rem;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.65rem;
        font-weight: 700;
        flex-shrink: 0;
    }

    .nav-user-name {
        max-width: 120px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    /* Hero / landing */
    .hero-icon-wrap {
        display: flex;
        justify-content: center;
        margin: 1.5rem 0 1rem;
    }

    .hero-icon {
        background: var(--navy);
        color: white;
        border-radius: 50%;
        width: 56px;
        height: 56px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        box-shadow: var(--shadow-md);
        position: relative;
    }

    .hero-icon::after {
        content: "✦";
        position: absolute;
        top: -4px;
        right: -4px;
        font-size: 0.75rem;
        color: #3b82f6;
    }

    .hero-title {
        text-align: center;
        color: var(--navy);
        font-weight: 700;
        font-size: 1.75rem;
        margin: 0 0 0.5rem 0;
        letter-spacing: -0.02em;
    }

    .hero-subtitle {
        text-align: center;
        color: var(--slate-600);
        max-width: 580px;
        margin: 0 auto 1.75rem;
        font-size: 0.88rem;
        line-height: 1.55;
    }

    .feature-card {
        background: var(--white);
        border: 1px solid var(--slate-200);
        border-radius: var(--radius-lg);
        padding: 1.25rem;
        min-height: 130px;
        box-shadow: var(--shadow-sm);
        transition: box-shadow 0.15s ease;
    }

    .feature-card:hover {
        box-shadow: var(--shadow-md);
    }

    .feature-card .icon { font-size: 1.35rem; margin-bottom: 0.5rem; }
    .feature-card .title {
        font-weight: 600;
        font-size: 0.9rem;
        color: var(--navy);
        margin-bottom: 0.3rem;
    }
    .feature-card .desc {
        font-size: 0.78rem;
        color: var(--slate-600);
        line-height: 1.45;
    }

    /* Auth / profil modal */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-modal-title) {
        background: var(--white);
        border: 1px solid var(--slate-200) !important;
        border-radius: var(--radius-lg) !important;
        padding: 1.5rem 2rem 2rem !important;
        max-width: 640px;
        margin: 0.5rem auto 2rem !important;
        box-shadow: var(--shadow-md);
    }

    .auth-modal-title {
        text-align: center;
        color: var(--navy);
        font-weight: 700;
        font-size: 1.15rem;
        margin-bottom: 1rem;
    }

    /* Chat */
    div[data-testid="stChatMessage"] {
        background: var(--white) !important;
        border: 1px solid var(--slate-200) !important;
        border-radius: var(--radius-lg) !important;
        padding: 0.85rem 1.1rem !important;
        margin-bottom: 0.65rem !important;
        box-shadow: var(--shadow-sm) !important;
    }

    div[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background: var(--slate-50) !important;
        border-color: var(--slate-200) !important;
    }

    .stChatInput > div {
        border-radius: var(--radius-lg) !important;
        border: 1px solid var(--slate-200) !important;
        background: var(--white) !important;
        box-shadow: var(--shadow-sm) !important;
    }

    /* File uploader */
    div[data-testid="stFileUploader"] {
        background: var(--white) !important;
        border: 1.5px dashed var(--slate-200) !important;
        border-radius: var(--radius-lg) !important;
        padding: 1.25rem !important;
    }

    div[data-testid="stFileUploader"]:hover {
        border-color: var(--slate-400) !important;
        background: var(--slate-50) !important;
    }

    div[data-testid="stFileUploader"] label {
        font-size: 0.85rem !important;
        color: var(--slate-600) !important;
    }

    /* Boutons principaux */
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stBaseButton-primary"] {
        background: var(--navy) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        padding: 0.45rem 1rem !important;
        transition: background 0.15s ease !important;
    }

    .stButton > button[kind="primary"]:hover {
        background: var(--navy-hover) !important;
    }

    /* Sidebar buttons */
    [data-testid="stSidebar"] .stButton > button {
        text-align: left !important;
        justify-content: flex-start !important;
        background: var(--white) !important;
        border: 1px solid var(--slate-200) !important;
        color: var(--navy) !important;
        border-radius: 8px !important;
        font-size: 0.78rem !important;
        font-weight: 500 !important;
        padding: 0.45rem 0.75rem !important;
        white-space: normal !important;
        line-height: 1.35 !important;
        box-shadow: none !important;
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        background: var(--slate-50) !important;
        border-color: var(--slate-400) !important;
    }

    /* Selectbox sidebar */
    [data-testid="stSidebar"] .stSelectbox > div > div {
        background: var(--white) !important;
        border: 1px solid var(--slate-200) !important;
        border-radius: 8px !important;
        font-size: 0.8rem !important;
    }

    /* Tabs auth (sélecteur dans la modal) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-modal-title) [data-testid="stHorizontalBlock"] {
        gap: 0.55rem !important;
        background: var(--slate-100);
        border-radius: 10px;
        padding: 0.45rem 0.5rem;
        margin-bottom: 1rem;
        flex-wrap: nowrap !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-modal-title) [data-testid="stHorizontalBlock"] .stButton > button {
        border-radius: 8px !important;
        font-size: 0.78rem !important;
        font-weight: 500 !important;
        white-space: nowrap !important;
        padding: 0.45rem 0.65rem !important;
        min-height: 2.25rem !important;
        width: 100% !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-modal-title) [data-testid="stHorizontalBlock"] .stButton > button p {
        white-space: nowrap !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-modal-title)
    [data-testid="stHorizontalBlock"] .stButton > button[kind="primary"],
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-modal-title)
    [data-testid="stHorizontalBlock"] .stButton > button[data-testid="stBaseButton-primary"] {
        background: var(--white) !important;
        color: var(--navy) !important;
        border: none !important;
        box-shadow: var(--shadow-sm) !important;
        font-weight: 600 !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-modal-title)
    [data-testid="stHorizontalBlock"] .stButton > button[kind="secondary"],
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.auth-modal-title)
    [data-testid="stHorizontalBlock"] .stButton > button[data-testid="stBaseButton-secondary"] {
        background: transparent !important;
        color: var(--slate-600) !important;
        border: none !important;
        box-shadow: none !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.55rem !important;
        background: var(--slate-100);
        border-radius: 10px;
        padding: 0.45rem 0.5rem;
        flex-wrap: wrap;
        justify-content: center;
    }

    .stTabs [data-baseweb="tab"],
    .stTabs button[role="tab"] {
        border-radius: 8px !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        color: var(--slate-600) !important;
        padding: 0.5rem 1.05rem !important;
        margin: 0 !important;
        flex: 0 1 auto !important;
        min-height: 2.25rem !important;
        white-space: nowrap !important;
        transition: background 0.15s ease, color 0.15s ease, box-shadow 0.15s ease !important;
    }

    .stTabs [data-baseweb="tab"]:hover,
    .stTabs button[role="tab"]:hover {
        color: var(--navy) !important;
        background: rgba(255, 255, 255, 0.55) !important;
    }

    .stTabs [data-baseweb="tab-highlight"] {
        background-color: var(--navy) !important;
        height: 2px !important;
        border-radius: 2px !important;
    }

    .stTabs [aria-selected="true"],
    .stTabs button[role="tab"][aria-selected="true"] {
        background: var(--white) !important;
        color: var(--navy) !important;
        box-shadow: var(--shadow-sm) !important;
        font-weight: 600 !important;
    }

    /* Dataframe */
    [data-testid="stDataFrame"] {
        border: 1px solid var(--slate-200);
        border-radius: var(--radius);
        overflow: hidden;
    }

    /* Expander */
    .streamlit-expanderHeader {
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        color: var(--slate-700) !important;
    }

    /* Divider principal */
    hr {
        border-color: var(--slate-200) !important;
    }

    /* Sidebar CTA unlock */
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: var(--navy) !important;
        color: white !important;
        border: none !important;
        text-align: center !important;
        justify-content: center !important;
        font-weight: 600 !important;
    }
</style>
"""

NAVBAR_HTML = """
<div class="app-navbar">
    <div class="app-brand">
        <div class="app-brand-icon">⚡</div>
        <div>
            <div class="app-brand-name">DataInsight AI</div>
            <div class="app-brand-tagline">Analyse de données e-commerce</div>
        </div>
    </div>
</div>
"""

def guest_badge_html() -> str:
    return '<div class="nav-guest-badge">👤 Mode invité</div>'

def user_chip_html(username: str) -> str:
    initials = username[:2].upper() if username else "??"
    safe_name = username.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""
    <div class="nav-user-chip">
        <div class="nav-user-avatar">{initials}</div>
        <span class="nav-user-name">{safe_name}</span>
    </div>
    """

HERO_HTML = """
<div class="hero-icon-wrap">
    <div class="hero-icon">📄</div>
</div>
<h2 class="hero-title">Discutez avec vos données e-commerce</h2>
<p class="hero-subtitle">
    Importez un fichier CSV ou Excel. DataInsight AI analysera vos colonnes et répondra
    à vos questions avec des explications, tableaux, graphiques et rapports PDF.
</p>
"""

FEATURE_CARDS = [
    ("📄", "Profilage automatique", "Détecter les types, valeurs nulles et colonnes clés."),
    ("💬", "Langage naturel", "Posez vos questions en français ou anglais."),
    ("📊", "Rapports PDF", "Exportez vos insights en rapport professionnel."),
]

def sidebar_section(title: str, hint: str = "") -> str:
    hint_html = f'<span class="hint">{hint}</span>' if hint else ""
    return f'<div class="sidebar-section-label"><span>{title}</span>{hint_html}</div>'

def feature_card_html(icon: str, title: str, desc: str) -> str:
    return f"""
    <div class="feature-card">
        <div class="icon">{icon}</div>
        <div class="title">{title}</div>
        <div class="desc">{desc}</div>
    </div>
    """

def guest_card_html() -> str:
    return """
    <div class="sidebar-guest-card">
        <div class="title">👤 Mode Invité</div>
        <div class="desc">3 questions par session. Connectez-vous pour un accès illimité au chat et à l'historique.</div>
    </div>
    """

def empty_box_html(text: str) -> str:
    return f'<div class="sidebar-empty-box">{text}</div>'
