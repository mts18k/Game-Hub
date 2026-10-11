from __future__ import annotations

import copy
import html
import json
import os
import re
import uuid
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from bs4 import BeautifulSoup
import streamlit as st
from dotenv import load_dotenv

# Optional AI: the app still works without an API key.
load_dotenv(Path(__file__).parent / ".env")

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
DATA_FILE = DATA_DIR / "user_data.json"
AUTO_TRACKING_FILE = DATA_DIR / "auto_sessions.json"
AUTO_RESET_MARKER = DATA_DIR / ".reset_auto_tracking"
DATA_DIR.mkdir(exist_ok=True)

st.set_page_config(
    page_title="GameHub | Ton espace gaming",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

GAMES: list[dict[str, Any]] = [
    {"id": "fortnite", "name": "Fortnite", "emoji": "🪂", "genre": "Battle royale", "platforms": ["PC", "PlayStation", "Xbox", "Switch", "Mobile"], "description": "Construis, explore et tente de finir dernier survivant. Créatif et compétitif.", "vibe": "Compétitif / fun", "steam_appid": None},
    {"id": "minecraft", "name": "Minecraft", "emoji": "⛏️", "genre": "Sandbox / survie", "platforms": ["PC", "PlayStation", "Xbox", "Switch", "Mobile"], "description": "Construis ton univers, explore des mondes et crée tes propres aventures.", "vibe": "Créatif / chill", "steam_appid": None},
    {"id": "roblox", "name": "Roblox", "emoji": "🧱", "genre": "Plateforme / expériences", "platforms": ["PC", "PlayStation", "Xbox", "Mobile"], "description": "Des milliers d'expériences : aventure, horreur, simulation et compétition.", "vibe": "Social / varié", "steam_appid": None},
    {"id": "valorant", "name": "VALORANT", "emoji": "🎯", "genre": "FPS tactique", "platforms": ["PC", "PlayStation", "Xbox"], "description": "Un FPS tactique qui récompense la précision, la communication et les stratégies d'équipe.", "vibe": "Compétitif", "steam_appid": None},
    {"id": "gtav", "name": "GTA V", "emoji": "🚘", "genre": "Action / monde ouvert", "platforms": ["PC", "PlayStation", "Xbox"], "description": "Un grand monde ouvert à explorer, avec des missions et de nombreuses activités.", "vibe": "Sandbox / action", "steam_appid": 271590},
    {"id": "rocketleague", "name": "Rocket League", "emoji": "🚗", "genre": "Sport / arcade", "platforms": ["PC", "PlayStation", "Xbox", "Switch"], "description": "Du football en voitures : mécanique, placement et réflexes font la différence.", "vibe": "Compétitif / rapide", "steam_appid": 252950},
    {"id": "geometrydash", "name": "Geometry Dash", "emoji": "🔺", "genre": "Rythme / plateforme", "platforms": ["PC", "Mobile"], "description": "Un jeu de rythme exigeant basé sur le timing, les réflexes et la mémorisation.", "vibe": "Précision / challenge", "steam_appid": 322170},
    {"id": "apex", "name": "Apex Legends", "emoji": "🚀", "genre": "Battle royale / FPS", "platforms": ["PC", "PlayStation", "Xbox", "Switch"], "description": "Un battle royale en escouade avec des personnages aux capacités différentes.", "vibe": "Rapide / équipe", "steam_appid": 1172470},
    {"id": "cs2", "name": "Counter-Strike 2", "emoji": "💥", "genre": "FPS tactique", "platforms": ["PC"], "description": "Un FPS compétitif où l'information, la précision et la coopération comptent.", "vibe": "Compétitif", "steam_appid": 730},
    {"id": "terraria", "name": "Terraria", "emoji": "🌳", "genre": "Aventure / sandbox", "platforms": ["PC", "PlayStation", "Xbox", "Switch", "Mobile"], "description": "Explore, mine, fabrique de l'équipement et découvre des zones secrètes.", "vibe": "Aventure / créatif", "steam_appid": 105600},
    {"id": "stardew", "name": "Stardew Valley", "emoji": "🌻", "genre": "Simulation / détente", "platforms": ["PC", "PlayStation", "Xbox", "Switch", "Mobile"], "description": "Fais prospérer ta ferme, rencontre les habitants et avance à ton rythme.", "vibe": "Chill / gestion", "steam_appid": 413150},
    {"id": "dota2", "name": "Dota 2", "emoji": "🧙", "genre": "MOBA", "platforms": ["PC"], "description": "Un MOBA stratégique où les rôles, les décisions et le jeu d'équipe sont essentiels.", "vibe": "Stratégie / équipe", "steam_appid": 570},
    {"id": "fallguys", "name": "Fall Guys", "emoji": "🍬", "genre": "Party game", "platforms": ["PC", "PlayStation", "Xbox", "Switch"], "description": "Des parcours colorés et des mini-jeux chaotiques à jouer entre amis.", "vibe": "Fun / social", "steam_appid": None},
    {"id": "brawls", "name": "Brawl Stars", "emoji": "⭐", "genre": "Action / arène", "platforms": ["Mobile"], "description": "Des parties courtes en arène avec plusieurs modes et personnages.", "vibe": "Rapide / social", "steam_appid": None},
    {"id": "genshin", "name": "Genshin Impact", "emoji": "🌌", "genre": "Action RPG", "platforms": ["PC", "PlayStation", "Mobile"], "description": "Explore un monde fantastique, découvre son histoire et développe ton équipe.", "vibe": "Exploration / aventure", "steam_appid": None},
    {"id": "pubg", "name": "PUBG: BATTLEGROUNDS", "emoji": "🪂", "genre": "Battle royale", "platforms": ["PC", "PlayStation", "Xbox"], "description": "Un battle royale tactique où la lecture de zone et la coordination sont importantes.", "vibe": "Tactique / survie", "steam_appid": 578080},
]

STEAM_NEWS_GAMES = {g["name"]: g["steam_appid"] for g in GAMES if g.get("steam_appid")}

DEFAULT_DATA: dict[str, Any] = {
    "favorites": [],
    "sessions": [],
    "custom_games": [],
    "game_notes": {},
    "goal_minutes_week": 300,
    "profile_name": "Player",
    "profile_emoji": "🎮",
}


def load_data() -> dict[str, Any]:
    if not DATA_FILE.exists():
        return copy.deepcopy(DEFAULT_DATA)
    try:
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        data = copy.deepcopy(DEFAULT_DATA)
        if isinstance(raw, dict):
            data.update(raw)
        for key, fallback in DEFAULT_DATA.items():
            if not isinstance(data.get(key), type(fallback)):
                data[key] = fallback
        return data
    except (OSError, json.JSONDecodeError):
        return copy.deepcopy(DEFAULT_DATA)


def save_data() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(st.session_state.data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_auto_tracking() -> dict[str, Any]:
    """Lit les sessions du petit processus local de détection de jeux."""
    if not AUTO_TRACKING_FILE.exists():
        return {"sessions": [], "last_tick_at": None}
    try:
        raw = json.loads(AUTO_TRACKING_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("sessions", []), list):
            return raw
    except (OSError, json.JSONDecodeError):
        pass
    return {"sessions": [], "last_tick_at": None}


def all_sessions() -> list[dict[str, Any]]:
    """Mélange les sessions manuelles déjà présentes et les sessions automatiques."""
    manual = [dict(s, source="manual") for s in st.session_state.data.get("sessions", [])]
    tracking = read_auto_tracking()
    automatic: list[dict[str, Any]] = []
    for raw in tracking.get("sessions", []):
        if not isinstance(raw, dict):
            continue
        item = dict(raw, source="auto")
        if item.get("seconds") is not None:
            item["minutes"] = max(int(item.get("minutes", 0)), int(round(float(item.get("seconds", 0)) / 60)))
        item.setdefault("date", str(item.get("started_at", ""))[:10])
        automatic.append(item)
    return manual + automatic


def running_auto_sessions() -> list[dict[str, Any]]:
    return [s for s in read_auto_tracking().get("sessions", []) if isinstance(s, dict) and not s.get("ended_at")]


if "data" not in st.session_state:
    st.session_state.data = load_data()
if "coach_result" not in st.session_state:
    st.session_state.coach_result = ""
if "name_result" not in st.session_state:
    st.session_state.name_result = ""
if "patch_result" not in st.session_state:
    st.session_state.patch_result = ""


def all_games() -> list[dict[str, Any]]:
    return GAMES + st.session_state.data.get("custom_games", [])


def game_by_id(game_id: str) -> dict[str, Any] | None:
    return next((g for g in all_games() if g.get("id") == game_id), None)


def toggle_favorite(game_id: str) -> None:
    favorites = st.session_state.data["favorites"]
    if game_id in favorites:
        favorites.remove(game_id)
    else:
        favorites.append(game_id)
    save_data()


def strip_html(value: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", value or "")
    return html.unescape(re.sub(r"\s+", " ", no_tags)).strip()


def generate_with_ai(prompt: str, fallback: str) -> tuple[str, bool, str]:
    """Returns (result, used_ai, error_message)."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return fallback, False, ""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini").strip() or "gpt-5.4-mini"
        response = client.responses.create(
            model=model,
            instructions=(
                "Tu es GameHub Coach, un assistant gaming en français. Donne des conseils positifs, "
                "concrets, adaptés au niveau indiqué. N'invente pas de statistiques ou de mises à jour "
                "récentes. Structure tes réponses avec des titres et des étapes courtes. Encourage les "
                "pauses, le respect des autres joueurs et une pratique équilibrée."
            ),
            input=prompt,
            max_output_tokens=1100,
        )
        answer = getattr(response, "output_text", "") or ""
        if not answer.strip():
            return fallback, False, "L'IA n'a pas renvoyé de texte cette fois."
        return answer.strip(), True, ""
    except Exception as exc:  # friendly UI; details go to logs, not the page
        print(f"GameHub AI error: {type(exc).__name__}: {exc}")
        return fallback, False, "Impossible de joindre l'IA. Vérifie la clé API, le modèle et ta connexion."


@st.cache_data(ttl=900, show_spinner=False)
def fetch_steam_news(app_id: int) -> list[dict[str, str]]:
    url = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"
    response = requests.get(url, params={"appid": app_id, "count": 6, "maxlength": 500, "format": "json"}, timeout=10)
    response.raise_for_status()
    news = response.json().get("appnews", {}).get("newsitems", [])
    items: list[dict[str, str]] = []
    for entry in news:
        items.append({
            "title": strip_html(str(entry.get("title", "Annonce Steam"))),
            "summary": strip_html(str(entry.get("contents", "")))[:360],
            "url": str(entry.get("url", "https://store.steampowered.com/")),
            "date": datetime.fromtimestamp(int(entry.get("date", 0))).strftime("%d.%m.%Y") if entry.get("date") else "Date inconnue",
            "source": "Steam",
        })
    return items


NEWS_SOURCES = {
    "Epic Games / Fortnite": {
        "url": "https://www.fortnite.com/news?lang=fr",
        "mode": "html",
        "source": "Epic Games / Fortnite",
        "domain": "fortnite.com",
        "emoji": "🪂",
    },
    "Roblox": {
        "url": "https://about.roblox.com/fr/newsroom",
        "mode": "html",
        "source": "Roblox",
        "domain": "about.roblox.com",
        "emoji": "🧱",
    },
    "Minecraft": {
        "url": "https://www.minecraft.net/en-us/feeds/community-content/rss",
        "mode": "rss",
        "source": "Minecraft",
        "domain": "minecraft.net",
        "emoji": "⛏️",
    },
}


def _format_pubdate(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return "Date non fournie"
    # Les dates du flux ne sont pas toutes au même format : les garder si on ne les reconnait pas.
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(text).astimezone().strftime("%d.%m.%Y")
    except (TypeError, ValueError, OverflowError):
        return text[:40]


@st.cache_data(ttl=900, show_spinner=False)
def fetch_official_news(source_name: str) -> list[dict[str, str]]:
    """Récupère les annonces de sources officielles. Aucune actualité n'est inventée en mode hors ligne."""
    config = NEWS_SOURCES[source_name]
    headers = {"User-Agent": "Mozilla/5.0 (compatible; GameHub/2.0; +local gaming dashboard)"}
    response = requests.get(config["url"], headers=headers, timeout=15)
    response.raise_for_status()
    items: list[dict[str, str]] = []

    if config["mode"] == "rss":
        root = ET.fromstring(response.content)
        # Supporte RSS et Atom sans dépendance supplémentaire.
        for item in root.findall(".//item"):
            title = strip_html(item.findtext("title", default=""))
            url = (item.findtext("link", default="") or "").strip()
            summary = strip_html(item.findtext("description", default=""))[:420]
            date_text = item.findtext("pubDate", default="")
            if title and url.startswith("https://"):
                items.append({"title": title, "summary": summary, "url": url, "date": _format_pubdate(date_text), "source": config["source"]})
        if not items:
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for item in root.findall(".//atom:entry", ns):
                title = strip_html(item.findtext("atom:title", default="", namespaces=ns))
                link_el = item.find("atom:link", ns)
                url = link_el.get("href", "") if link_el is not None else ""
                summary = strip_html(item.findtext("atom:summary", default="", namespaces=ns))[:420]
                date_text = item.findtext("atom:updated", default="", namespaces=ns)
                if title and url.startswith("https://"):
                    items.append({"title": title, "summary": summary, "url": url, "date": _format_pubdate(date_text), "source": config["source"]})
    else:
        soup = BeautifulSoup(response.text, "html.parser")
        seen: set[str] = set()
        for anchor in soup.select("a[href]"):
            href = (anchor.get("href") or "").strip()
            title = strip_html(anchor.get_text(" ", strip=True))
            if not href or not title or len(title) < 8:
                continue
            lowered = title.casefold()
            if lowered in {"en savoir plus", "lire la suite", "read more", "learn more", "voir plus"}:
                continue
            if source_name == "Epic Games / Fortnite":
                # Les articles Fortnite utilisent des chemins /news/ ; ignorer les liens génériques.
                if "/news/" not in href and not href.startswith("/news?"):
                    continue
                if href.startswith("/"):
                    href = "https://www.fortnite.com" + href
                if not href.startswith("https://www.fortnite.com/news"):
                    continue
            elif source_name == "Roblox":
                # On vise les articles de la salle de presse, pas les liens de navigation.
                if "/newsroom/" not in href and not "/newsroom?" in href:
                    continue
                if href.startswith("/"):
                    href = "https://about.roblox.com" + href
                if not href.startswith("https://about.roblox.com/"):
                    continue
            if href in seen:
                continue
            seen.add(href)
            parent_text = strip_html(anchor.parent.get_text(" ", strip=True)) if anchor.parent else ""
            summary = parent_text.replace(title, "", 1).strip()[:420]
            items.append({"title": title, "summary": summary, "url": href, "date": "Dernière publication", "source": config["source"]})
            if len(items) >= 12:
                break

    # En premier les annonces les plus récentes dans l'ordre du flux/page officielle.
    return items[:10]


def section_header(title: str, subtitle: str | None = None) -> None:
    st.markdown(f"<div class='section-title'>{title}</div>", unsafe_allow_html=True)
    if subtitle:
        st.caption(subtitle)


def game_card(game: dict[str, Any], key_prefix: str = "game") -> None:
    favorite = game["id"] in st.session_state.data["favorites"]
    with st.container(border=True):
        st.markdown(f"<div class='game-emoji'>{game.get('emoji', '🎮')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='game-title'>{html.escape(game['name'])}</div>", unsafe_allow_html=True)
        st.markdown(f"<span class='tag'>{html.escape(game.get('genre', 'Autre'))}</span>", unsafe_allow_html=True)
        st.write(game.get("description", "Ton jeu ajouté à GameHub."))
        st.caption(" · ".join(game.get("platforms", ["Personnalisé"])))
        label = "★ Retirer des favoris" if favorite else "☆ Ajouter aux favoris"
        if st.button(label, key=f"{key_prefix}_fav_{game['id']}", use_container_width=True):
            toggle_favorite(game["id"])
            st.rerun()


# --- Styles ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root { color-scheme: dark; }
html, body, [class*="css"], .stApp { font-family: 'Space Grotesk', 'Segoe UI', sans-serif; }
.stApp { background: radial-gradient(ellipse at top left, rgba(99,70,220,.16), transparent 34%), radial-gradient(ellipse at bottom right, rgba(15,175,191,.08), transparent 30%), #090b12; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #111522 0%, #0c0f17 100%); border-right: 1px solid #292d43; }
[data-testid="stSidebar"] * { font-family: 'Rajdhani', 'Space Grotesk', sans-serif; }
[data-testid="stSidebar"] h1 { font-family: 'Rajdhani', sans-serif; font-size: 2.2rem; letter-spacing: .04em; font-weight: 700; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { font-size: 1.13rem; font-weight: 700; letter-spacing: .025em; }
[data-testid="stSidebar"] [data-testid="stRadio"] label p { font-family: 'Rajdhani', sans-serif; }
.block-container { padding-top: 1.7rem; padding-bottom: 3rem; max-width: 1450px; }
h1, h2, h3 { letter-spacing: -0.035em; }
.hero { background: linear-gradient(120deg, rgba(93,66,220,.38), rgba(24,184,197,.14)), #141827; border: 1px solid #343752; border-radius: 22px; padding: 30px; margin-bottom: 18px; box-shadow: 0 16px 55px rgba(0,0,0,.17); }
.hero-kicker { color: #a9a4ff; text-transform: uppercase; letter-spacing: .19em; font-size: 11px; font-weight: 800; }
.hero-title { font-size: clamp(30px, 4vw, 48px); font-weight: 900; line-height: 1.05; margin: 10px 0 12px; }
.hero-copy { max-width: 760px; color: #c3c8d6; font-size: 15px; }
.section-title { font-size: 23px; font-weight: 850; letter-spacing: -.025em; margin: 18px 0 5px; }
.game-emoji { font-size: 36px; line-height: 1.1; margin-bottom: 10px; }
.game-title { font-size: 19px; font-weight: 800; margin-bottom: 5px; }
.tag { display: inline-block; border: 1px solid #49416e; background: #221f38; color: #c8c0ff; padding: 3px 9px; border-radius: 999px; font-size: 11px; margin-bottom: 8px; }
.small-muted { color: #9fa6b8; font-size: 13px; }
div[data-testid="stMetric"] { background: linear-gradient(145deg, #151a2a, #10131d); border: 1px solid #292f42; padding: 14px 16px; border-radius: 15px; }
.stButton button { border-radius: 10px; font-weight: 700; transition: border-color .15s ease, transform .15s ease; }
.stButton button:hover { border-color: #8a80ff; transform: translateY(-1px); }
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] { border-radius: 10px; }
.news-source { font-family: 'Rajdhani', sans-serif; text-transform: uppercase; letter-spacing: .13em; color: #a9a4ff; font-size: 12px; font-weight: 700; }
.live-pulse { color: #6ee7b7; font-weight: 700; }
hr { border-color: #282d3e; }
</style>
""", unsafe_allow_html=True)

# --- Navigation ---
with st.sidebar:
    profile_name = html.escape(str(st.session_state.data.get("profile_name", "Player"))[:28])
    profile_emoji = html.escape(str(st.session_state.data.get("profile_emoji", "🎮"))[:8])
    st.markdown("# 🎮 GameHub")
    st.caption("PLAYER HUB  •  V2.0")
    st.markdown(f"<div style='background:#191e2e;border:1px solid #303750;border-radius:14px;padding:12px;margin:10px 0 14px'><div style='font-size:28px'>{profile_emoji}</div><div style='font-size:18px;font-weight:700'>{profile_name}</div><div style='font-size:12px;color:#9fa6b8'>Profil local · PC</div></div>", unsafe_allow_html=True)
    st.divider()
    page = st.radio(
        "Navigation",
        ["Accueil", "Explorer les jeux", "Mes favoris", "Mes sessions", "Actus gaming", "Coach IA", "Mon profil & paramètres"],
        label_visibility="collapsed",
    )
    st.divider()
    ai_enabled = bool(os.getenv("OPENAI_API_KEY", "").strip())
    st.markdown(f"**Coach IA**  {'🟢 configuré' if ai_enabled else '⚪ mode local'}")
    st.caption("Le suivi automatique marche quand GameHub est lancé sur ce PC.")

# --- Pages ---
if page == "Accueil":
    st.markdown("""
    <div class="hero">
      <div class="hero-kicker">PLAYER HUB • VERSION 2.0</div>
      <div class="hero-title">Ton univers gaming.<br>Un seul endroit.</div>
      <div class="hero-copy">Découvre des jeux, suis automatiquement tes heures de jeu, consulte les actus officielles et prépare ta prochaine progression avec le Coach GameHub.</div>
    </div>
    """, unsafe_allow_html=True)

    sessions = all_sessions()
    total_minutes = sum(int(s.get("minutes", 0)) for s in sessions)
    favorites = st.session_state.data["favorites"]
    active_sessions = running_auto_sessions()
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("Jeux dans le catalogue", len(all_games()))
    g2.metric("Tes favoris", len(favorites))
    g3.metric("Jeux détectés maintenant", len(active_sessions))
    g4.metric("Temps suivi", f"{total_minutes // 60} h {total_minutes % 60:02d}")
    if active_sessions:
        playing_names = ", ".join(sorted({str(s.get("game", "Jeu")) for s in active_sessions}))
        st.success(f"🟢 Suivi automatique actif : {playing_names}. Les heures s'ajoutent sans intervention.")
    else:
        tracking = read_auto_tracking()
        if tracking.get("last_tick_at"):
            st.info("🛰️ Suivi automatique prêt. Lance un jeu PC compatible pendant que GameHub est ouvert : il sera détecté tout seul.")
        else:
            st.info("🛰️ Le suivi démarre avec le lanceur GameHub. Aucun compte externe ni saisie manuelle nécessaires pour suivre les jeux détectés sur ce PC.")

    left, right = st.columns([1.25, 1])
    with left:
        section_header("✨ Pour commencer", "Les fonctions les plus utiles sont juste ici.")
        quick = st.columns(2)
        with quick[0]:
            with st.container(border=True):
                st.markdown("### 🔎 Explorer")
                st.write("Trouve un jeu selon ton style et ta plateforme.")
                if st.button("Ouvrir le catalogue", use_container_width=True):
                    st.session_state._go_explore = True
                    st.rerun()
        with quick[1]:
            with st.container(border=True):
                st.markdown("### 🧠 Coach gaming")
                st.write("Obtiens un plan d'entraînement adapté à ton jeu.")
                if st.button("Ouvrir le coach", use_container_width=True):
                    st.session_state._go_coach = True
                    st.rerun()
        if st.session_state.pop("_go_explore", False):
            st.info("Choisis **Explorer les jeux** dans le menu à gauche.")
        if st.session_state.pop("_go_coach", False):
            st.info("Choisis **Coach IA** dans le menu à gauche.")
    with right:
        section_header("🎯 Mini-défis du jour", "Des idées pour varier tes sessions.")
        quests = [
            ("01", "Le warm-up", "Passe 5 à 10 minutes à t'échauffer avant une partie classée."),
            ("02", "Le joueur malin", "Après une partie, note une chose à refaire et une à améliorer."),
            ("03", "Le bon équilibre", "Fais une petite pause entre deux longues sessions.")
        ]
        for number, title, desc in quests:
            with st.container(border=True):
                c1, c2 = st.columns([0.15, 1])
                c1.markdown(f"**{number}**")
                c2.markdown(f"**{title}**")
                c2.caption(desc)

    section_header("⭐ Tes favoris")
    fav_games = [g for g in all_games() if g["id"] in favorites]
    if fav_games:
        cols = st.columns(min(3, len(fav_games)))
        for i, game in enumerate(fav_games[:3]):
            with cols[i]:
                game_card(game, "home")
    else:
        st.info("Tu n'as pas encore de favoris. Va dans **Explorer les jeux** et appuie sur ☆.")

elif page == "Explorer les jeux":
    section_header("🔎 Explorer les jeux", "Recherche un titre, filtre par genre ou par plateforme, puis ajoute tes favoris.")
    f1, f2, f3 = st.columns([1.5, 1, 1])
    with f1:
        query = st.text_input("Rechercher", placeholder="Ex. Minecraft, FPS, aventure…")
    genres = sorted({g.get("genre", "Autre") for g in all_games()})
    with f2:
        genre_filter = st.selectbox("Genre", ["Tous"] + genres)
    with f3:
        platform_filter = st.selectbox("Plateforme", ["Toutes", "PC", "PlayStation", "Xbox", "Switch", "Mobile"])

    filtered = all_games()
    if query.strip():
        q = query.strip().casefold()
        filtered = [g for g in filtered if q in g["name"].casefold() or q in g.get("genre", "").casefold() or q in g.get("description", "").casefold()]
    if genre_filter != "Tous":
        filtered = [g for g in filtered if g.get("genre") == genre_filter]
    if platform_filter != "Toutes":
        filtered = [g for g in filtered if platform_filter in g.get("platforms", [])]
    st.caption(f"{len(filtered)} jeu(x) trouvé(s)")
    if filtered:
        cols = st.columns(3)
        for idx, game in enumerate(filtered):
            with cols[idx % 3]:
                game_card(game, "explore")
    else:
        st.warning("Aucun résultat. Essaie un autre mot ou un autre filtre.")

    with st.expander("＋ Ajouter un jeu au catalogue"):
        with st.form("custom_game_form", clear_on_submit=True):
            custom_name = st.text_input("Nom du jeu", max_chars=50)
            custom_genre = st.text_input("Genre", placeholder="Ex. Horreur, aventure…", max_chars=40)
            custom_platform = st.selectbox("Plateforme principale", ["PC", "PlayStation", "Xbox", "Switch", "Mobile", "Autre"])
            custom_description = st.text_area("Description", max_chars=220, placeholder="Pourquoi tu aimes ce jeu ?")
            custom_emoji = st.selectbox("Icône", ["🎮", "👾", "🔥", "🌌", "🧩", "🏎️", "🏆", "🧟", "🐉", "⭐"])
            submitted = st.form_submit_button("Ajouter à GameHub", use_container_width=True)
        if submitted:
            if not custom_name.strip():
                st.error("Entre un nom de jeu.")
            elif any(g["name"].casefold() == custom_name.strip().casefold() for g in all_games()):
                st.warning("Ce jeu est déjà dans le catalogue.")
            else:
                st.session_state.data["custom_games"].append({
                    "id": f"custom_{uuid.uuid4().hex[:10]}",
                    "name": custom_name.strip(),
                    "emoji": custom_emoji,
                    "genre": custom_genre.strip() or "Personnalisé",
                    "platforms": [custom_platform],
                    "description": custom_description.strip() or "Jeu ajouté par toi dans GameHub.",
                    "vibe": "Personnalisé",
                    "steam_appid": None,
                })
                save_data()
                st.success(f"{custom_name.strip()} a été ajouté !")
                st.rerun()

elif page == "Mes favoris":
    section_header("⭐ Mes favoris", "Ta liste personnelle de jeux à retrouver rapidement.")
    fav_games = [g for g in all_games() if g["id"] in st.session_state.data["favorites"]]
    if not fav_games:
        st.info("Ta liste est vide pour l'instant. Ajoute des jeux depuis le catalogue.")
    else:
        cols = st.columns(3)
        for idx, game in enumerate(fav_games):
            with cols[idx % 3]:
                game_card(game, "favpage")
                note_value = st.session_state.data["game_notes"].get(game["id"], "")
                note = st.text_area("Ta note", value=note_value, key=f"note_{game['id']}", height=75, placeholder="À tester, objectif, pseudo d'ami…")
                if st.button("Enregistrer la note", key=f"save_note_{game['id']}", use_container_width=True):
                    st.session_state.data["game_notes"][game["id"]] = note[:1000]
                    save_data()
                    st.success("Note enregistrée.")

elif page == "Mes sessions":
    section_header("⏱️ Ton temps de jeu", "Les jeux PC compatibles sont détectés automatiquement quand GameHub tourne. Aucun formulaire n'est requis pour eux.")

    @st.fragment(run_every=15)
    def render_session_dashboard() -> None:
        active_now = running_auto_sessions()
        if active_now:
            names = " · ".join(sorted({str(item.get("game", "Jeu")) for item in active_now}))
            st.success(f"🟢 EN COURS — {names}. Les statistiques se mettent à jour automatiquement.")
        else:
            tracking_state = read_auto_tracking()
            if tracking_state.get("last_tick_at"):
                st.caption(f"🛰️ Détecteur local actif au dernier contrôle : {tracking_state.get('last_tick_at')}. Lance un jeu compatible pour démarrer le suivi.")
            else:
                st.warning("Le détecteur n'a pas encore écrit de données. Lance GameHub avec lancer_gamehub.bat et laisse-le ouvert pendant que tu joues.")

        sessions_live = all_sessions()
        total_minutes = sum(int(item.get("minutes", 0)) for item in sessions_live)
        today = date.today().isoformat()
        today_minutes = sum(int(item.get("minutes", 0)) for item in sessions_live if str(item.get("date", ""))[:10] == today)
        week_start = date.today().toordinal() - date.today().weekday()
        week_minutes = 0
        for item in sessions_live:
            try:
                if date.fromisoformat(str(item.get("date", "2000-01-01"))[:10]).toordinal() >= week_start:
                    week_minutes += int(item.get("minutes", 0))
            except (ValueError, TypeError):
                pass
        auto_count = sum(1 for item in sessions_live if item.get("source") == "auto")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Temps total", f"{total_minutes // 60} h {total_minutes % 60:02d}")
        c2.metric("Aujourd'hui", f"{today_minutes // 60} h {today_minutes % 60:02d}")
        c3.metric("Cette semaine", f"{week_minutes // 60} h {week_minutes % 60:02d}")
        c4.metric("Sessions auto détectées", auto_count)

        if sessions_live:
            sums: dict[str, float] = defaultdict(float)
            for item in sessions_live:
                sums[str(item.get("game", "Jeu inconnu"))] += int(item.get("minutes", 0)) / 60
            df = pd.DataFrame([{"Jeu": k, "Heures": round(v, 2)} for k, v in sorted(sums.items(), key=lambda pair: pair[1], reverse=True)])
            section_header("📊 Répartition du temps de jeu")
            st.bar_chart(df, x="Jeu", y="Heures", use_container_width=True)
            section_header("🕹️ Historique des sessions")
            for sess in sorted(sessions_live, key=lambda item: str(item.get("started_at", item.get("date", ""))), reverse=True):
                with st.container(border=True):
                    cols = st.columns([1.15, .55, .7, 1.6])
                    title = str(sess.get("game", "Jeu inconnu"))
                    if sess.get("source") == "auto" and not sess.get("ended_at"):
                        title += "  🟢 EN COURS"
                    elif sess.get("source") == "auto":
                        title += "  · automatique"
                    cols[0].markdown(f"**{title}**")
                    mins = int(sess.get("minutes", 0))
                    cols[1].write(f"{mins // 60} h {mins % 60:02d}" if mins >= 60 else f"{mins} min")
                    cols[2].caption(str(sess.get("date", ""))[:10])
                    note_text = str(sess.get("mode", ""))
                    if sess.get("note"):
                        note_text += " · " + str(sess.get("note", ""))
                    cols[3].caption(note_text.strip(" ·"))

            manual_sessions = [item for item in st.session_state.data["sessions"] if isinstance(item, dict)]
            if manual_sessions:
                options = {f"{item.get('date')} — {item.get('game')} — {item.get('minutes')} min": item.get("id") for item in sorted(manual_sessions, key=lambda value: value.get("date", ""), reverse=True)}
                selected_label = st.selectbox("Supprimer une session ajoutée manuellement", ["Ne rien supprimer"] + list(options.keys()))
                if st.button("Supprimer la session sélectionnée", disabled=selected_label == "Ne rien supprimer"):
                    sid = options.get(selected_label)
                    st.session_state.data["sessions"] = [item for item in manual_sessions if item.get("id") != sid]
                    save_data()
                    st.success("Session manuelle supprimée.")
                    st.rerun()
        else:
            st.info("Aucune heure détectée pour l'instant. Lance un jeu compatible pendant que GameHub est ouvert ; le suivi démarrera tout seul.")

    render_session_dashboard()

    with st.expander("＋ Ajouter une session manuellement (facultatif)", expanded=False):
        games = all_games()
        if games:
            with st.form("session_form", clear_on_submit=True):
                game_labels = {game["name"]: game["id"] for game in games}
                picked_name = st.selectbox("Jeu", list(game_labels.keys()))
                s1, s2, s3 = st.columns(3)
                with s1:
                    minutes = st.number_input("Durée (minutes)", min_value=5, max_value=720, value=60, step=5)
                with s2:
                    played_on = st.date_input("Date", value=date.today())
                with s3:
                    play_mode = st.selectbox("Type de session", ["Solo", "Avec des amis", "En ligne / classé", "Entraînement", "Autre"])
                session_note = st.text_input("Note (facultatif)", max_chars=160, placeholder="Ex. bonne partie, objectif atteint…")
                add_session = st.form_submit_button("Enregistrer la session", use_container_width=True)
            if add_session:
                st.session_state.data["sessions"].append({
                    "id": uuid.uuid4().hex,
                    "game_id": game_labels[picked_name],
                    "game": picked_name,
                    "minutes": int(minutes),
                    "date": played_on.isoformat(),
                    "mode": play_mode,
                    "note": session_note.strip(),
                })
                save_data()
                st.success("Session enregistrée !")
                st.rerun()

elif page == "Coach IA":
    section_header("🧠 Coach GameHub", "Plans de progression, idées de pseudos et aide pour comprendre les notes de mise à jour.")
    if os.getenv("OPENAI_API_KEY", "").strip():
        st.success(f"IA connectée via l'API OpenAI · modèle configuré : {os.getenv('OPENAI_MODEL', 'gpt-5.4-mini')}")
    else:
        st.info("Le coach fonctionne en mode local. Pour activer la vraie IA, ajoute ta clé API dans le fichier .env. Les appels API peuvent être payants.")

    tab_plan, tab_names, tab_patch = st.tabs(["🎯 Plan gaming", "✨ Générateur de pseudos", "🧾 Comprendre une mise à jour"])
    with tab_plan:
        games = all_games()
        labels = {g["name"]: g for g in games}
        selected_game = st.selectbox("Ton jeu", list(labels.keys()), key="coach_game")
        c1, c2 = st.columns(2)
        with c1:
            goal = st.selectbox("Objectif", ["Être plus régulier", "Améliorer ma visée / mes réflexes", "Mieux comprendre les stratégies", "Mieux jouer en équipe", "Progresser sans tilt", "Découvrir les bases"])
            level = st.selectbox("Niveau", ["Débutant", "Intermédiaire", "Avancé"])
        with c2:
            time_budget = st.selectbox("Temps disponible par session", ["15 minutes", "30 minutes", "45 minutes", "1 heure"])
            style = st.selectbox("Style de jeu", ["Plutôt détente", "Compétitif", "Avec des amis", "Je découvre encore"])
        extra = st.text_area("Précision facultative", placeholder="Ex. je joue à la manette, j'ai du mal à gérer mon temps…", max_chars=500)
        if st.button("Générer mon plan", type="primary", use_container_width=True):
            game = labels[selected_game]
            fallback = (
                f"## Plan de progression — {selected_game}\n\n"
                f"**Objectif :** {goal}\n\n"
                f"1. **Échauffement (5 min)** — lance une activité facile pour te mettre dans le rythme.\n"
                f"2. **Focus principal (10–20 min)** — travaille une seule compétence liée à ton objectif : précision, placement, timing ou communication.\n"
                f"3. **Mise en pratique** — applique cette compétence dans une partie normale, sans chercher à tout corriger à la fois.\n"
                f"4. **Bilan rapide (2 min)** — note une réussite et un point à essayer autrement à la prochaine session.\n\n"
                f"**Conseil adapté :** {game.get('description', '')} Garde la session à {time_budget}, fais une pause si tu fatigues et mesure tes progrès sur plusieurs sessions, pas sur une seule partie.\n\n"
                "*Mode local : ajoute une clé API OpenAI pour personnaliser encore plus ce plan.*"
            )
            prompt = f"Prépare un plan d'entraînement réaliste pour le jeu {selected_game}. Objectif : {goal}. Niveau : {level}. Durée : {time_budget}. Style : {style}. Informations supplémentaires : {extra or 'Aucune'}. Réponds en français, avec un plan minuté, 3 exercices concrets, un objectif mesurable et une astuce pour rester calme. Ne prétends pas connaître les dernières mises à jour."
            with st.spinner("Préparation du plan…"):
                answer, used_ai, error = generate_with_ai(prompt, fallback)
            st.session_state.coach_result = answer
            st.session_state.coach_used_ai = used_ai
            st.session_state.coach_error = error
        if st.session_state.coach_result:
            if st.session_state.get("coach_used_ai"):
                st.caption("Réponse générée par l'IA.")
            else:
                st.caption("Plan local pré-écrit, sans appel IA.")
            if st.session_state.get("coach_error"):
                st.warning(st.session_state.coach_error)
            st.markdown(st.session_state.coach_result)
            st.download_button("Télécharger le plan (.md)", st.session_state.coach_result, file_name="mon_plan_gamehub.md", mime="text/markdown")

    with tab_names:
        name_game = st.text_input("Jeu / univers", placeholder="Ex. Minecraft, Fortnite, Roblox…")
        name_vibe = st.selectbox("Vibe du pseudo", ["Tryhard", "Drôle", "Mystérieux", "Court et propre", "Cyber / futuriste", "Chill"])
        name_language = st.selectbox("Style", ["Français", "Anglais", "Mix français/anglais", "Inventé / unique"])
        if st.button("Créer des pseudos", use_container_width=True):
            fallback_names = {
                "Tryhard": ["VexNova", "ClutchOrbit", "PixelFury", "NightReset", "ZeroDelay", "KryoRush", "TurboGhost", "AimPulse", "NovaShift", "HexRunner"],
                "Drôle": ["PatateCritique", "PingouinPro", "LagDeGénie", "CroissantGG", "OopsRespawn", "PoulpePressé", "ClavierFou", "PasLeBoss", "Baguette.exe", "MiniPanique"],
                "Mystérieux": ["VoidWhisper", "NocturneX", "EchoPhantom", "SilentRune", "UmbraWave", "GhostSignal", "DarkOrbit", "MoonCipher", "VelvetHex", "ObsidianFox"],
                "Court et propre": ["Kyro", "Nexo", "Vexo", "Zuno", "Rynx", "Lumo", "Kova", "Zyro", "Mavi", "Orbi"],
                "Cyber / futuriste": ["NeonCircuit", "CyberComet", "GlitchNova", "BytePhantom", "QuantumFlux", "SynthRider", "PixelNexus", "PulseMatrix", "ChromeEcho", "DataDrift"],
                "Chill": ["SoftPixel", "CloudyGG", "LofiRunner", "MellowNova", "SlowOrbit", "CozyRespawn", "MoonTea", "CalmQuest", "SundayByte", "TinyAurora"],
            }
            fallback = "## Idées de pseudos\n\n" + "\n".join(f"- **{n}**" for n in fallback_names[name_vibe]) + "\n\n*Tu peux les personnaliser en ajoutant un chiffre ou un mot qui te ressemble.*"
            prompt = f"Génère 15 pseudos uniques pour un joueur. Jeu/univers : {name_game or 'gaming général'}. Ambiance : {name_vibe}. Langue : {name_language}. Évite les insultes, les données personnelles et les caractères trop difficiles à taper. Une liste simple avec une mini-explication pour les 5 meilleurs."
            answer, used_ai, error = generate_with_ai(prompt, fallback)
            st.session_state.name_result = answer
            st.session_state.name_used_ai = used_ai
            st.session_state.name_error = error
        if st.session_state.name_result:
            if not st.session_state.get("name_used_ai"):
                st.caption("Générateur local, sans appel IA.")
            if st.session_state.get("name_error"):
                st.warning(st.session_state.name_error)
            st.markdown(st.session_state.name_result)
            st.download_button("Télécharger les pseudos", st.session_state.name_result, file_name="pseudos_gamehub.md", mime="text/markdown")

    with tab_patch:
        patch_text = st.text_area("Colle ici les notes de mise à jour", height=190, max_chars=12000, placeholder="Colle les notes ou le changelog que tu veux comprendre…")
        patch_goal = st.selectbox("Je veux surtout…", ["Un résumé simple", "Les changements importants", "Ce que ça change pour les joueurs", "Les points à surveiller"])
        if st.button("Expliquer les notes", use_container_width=True):
            if not patch_text.strip():
                st.warning("Colle d'abord le texte des notes de mise à jour.")
            else:
                fallback = "## Résumé à faire\n\nLe mode local ne peut pas analyser automatiquement ce texte. Active l'API OpenAI pour obtenir un résumé. Tu peux aussi lire le texte et repérer les sections **Équilibrage**, **Corrections de bugs** et **Nouveautés**."
                prompt = f"Explique ce texte de mise à jour en français simple. Objectif de lecture : {patch_goal}. Distingue faits explicitement présents et interprétation. N'ajoute aucune information externe. Texte :\n\n{patch_text}"
                with st.spinner("Analyse du texte…"):
                    answer, used_ai, error = generate_with_ai(prompt, fallback)
                st.session_state.patch_result = answer
                st.session_state.patch_used_ai = used_ai
                st.session_state.patch_error = error
        if st.session_state.patch_result:
            if not st.session_state.get("patch_used_ai"):
                st.caption("Mode local : configure l'IA pour analyser le texte automatiquement.")
            if st.session_state.get("patch_error"):
                st.warning(st.session_state.patch_error)
            st.markdown(st.session_state.patch_result)
            st.download_button("Télécharger le résumé", st.session_state.patch_result, file_name="resume_patch_gamehub.md", mime="text/markdown")

elif page == "Actus gaming":
    section_header("📰 Actus gaming", "Les annonces récentes de Fortnite / Epic Games, Roblox et Minecraft, récupérées depuis leurs pages officielles.")
    news_sources = ["Epic Games / Fortnite", "Roblox", "Minecraft", "Steam — actualités d'un jeu"]
    selected_source = st.selectbox("Source", news_sources, index=0)

    if selected_source == "Steam — actualités d'un jeu":
        choices = list(STEAM_NEWS_GAMES.keys())
        chosen_news_game = st.selectbox("Jeu Steam", choices)
        st.caption("Les annonces sont récupérées depuis l'API publique Steam pour les titres compatibles.")
        source_cache_key = f"Steam — {chosen_news_game}"
        if st.button("↻ Charger les actualités", type="primary", use_container_width=True):
            try:
                with st.spinner("Chargement des annonces Steam…"):
                    items = fetch_steam_news(int(STEAM_NEWS_GAMES[chosen_news_game]))
                st.session_state.setdefault("news_by_source", {})[source_cache_key] = {"items": items}
            except requests.RequestException:
                st.session_state.setdefault("news_by_source", {})[source_cache_key] = {"items": [], "error": "Steam est indisponible. Vérifie ta connexion et réessaie."}
    else:
        config = NEWS_SOURCES[selected_source]
        st.markdown(f"<div class='news-source'>{config['emoji']} SOURCE OFFICIELLE</div>", unsafe_allow_html=True)
        st.caption(f"Source : {config['url']}")
        source_cache_key = selected_source
        if st.button("↻ Charger les dernières actus", type="primary", use_container_width=True):
            try:
                with st.spinner(f"Lecture des actualités {selected_source}…"):
                    items = fetch_official_news(selected_source)
                st.session_state.setdefault("news_by_source", {})[source_cache_key] = {"items": items}
            except (requests.RequestException, ET.ParseError, ValueError, KeyError) as exc:
                print(f"GameHub news error ({selected_source}): {type(exc).__name__}: {exc}")
                st.session_state.setdefault("news_by_source", {})[source_cache_key] = {"items": [], "error": "Impossible de récupérer les actus pour le moment. Réessaie plus tard ou ouvre la page officielle ci-dessous."}

    cache = st.session_state.get("news_by_source", {}).get(source_cache_key, {})
    if cache.get("error"):
        st.warning(cache["error"])
        if selected_source != "Steam — actualités d'un jeu":
            st.markdown(f"[Ouvrir la page officielle ↗]({NEWS_SOURCES[selected_source]['url']})")
    elif cache.get("items"):
        st.caption(f"{len(cache['items'])} annonce(s) chargée(s) · les résultats sont mis en cache pendant 15 minutes.")
        for item in cache["items"]:
            with st.container(border=True):
                st.caption(f"{item.get('source', selected_source)}  ·  {item.get('date', 'Date non fournie')}")
                st.markdown(f"### {html.escape(item.get('title', 'Annonce'))}")
                summary = item.get("summary", "")
                st.write(summary or "Ouvre la source officielle pour lire l'annonce complète.")
                st.markdown(f"[Lire l'annonce ↗]({item.get('url', NEWS_SOURCES.get(selected_source, {}).get('url', 'https://store.steampowered.com/'))})")
    else:
        st.info("Choisis une source puis clique sur le bouton pour charger ses actualités. Une connexion Internet est nécessaire.")

elif page == "Mon profil & paramètres":
    section_header("👤 Mon profil & paramètres", "Personnalise ton espace, règle ton suivi automatique et gère tes données.")

    with st.container(border=True):
        st.markdown("#### ✨ Profil GameHub local")
        st.caption("Ce profil sert à personnaliser GameHub sur cet ordinateur. Il ne s'agit pas d'un compte en ligne ni d'une connexion Epic / Roblox / Microsoft.")
        with st.form("profile_form"):
            profile_name = st.text_input("Pseudo affiché", value=str(st.session_state.data.get("profile_name", "Player")), max_chars=28)
            profile_emoji = st.selectbox("Avatar", ["🎮", "👾", "🔥", "🪂", "⛏️", "🧱", "⚡", "🐉", "🏆", "🌌"], index=["🎮", "👾", "🔥", "🪂", "⛏️", "🧱", "⚡", "🐉", "🏆", "🌌"].index(st.session_state.data.get("profile_emoji", "🎮")) if st.session_state.data.get("profile_emoji", "🎮") in ["🎮", "👾", "🔥", "🪂", "⛏️", "🧱", "⚡", "🐉", "🏆", "🌌"] else 0)
            save_profile = st.form_submit_button("Enregistrer mon profil", use_container_width=True)
        if save_profile:
            st.session_state.data["profile_name"] = profile_name.strip() or "Player"
            st.session_state.data["profile_emoji"] = profile_emoji
            save_data()
            st.success("Profil mis à jour !")
            st.rerun()

    with st.container(border=True):
        st.markdown("#### 🛰️ Suivi automatique du temps de jeu")
        auto_state = read_auto_tracking()
        active = running_auto_sessions()
        if active:
            active_names = ", ".join(sorted({str(item.get("game", "Jeu")) for item in active}))
            st.success(f"Détection active maintenant : {active_names}")
        elif auto_state.get("last_tick_at"):
            st.info(f"Dernier contrôle du détecteur : {auto_state.get('last_tick_at')}")
        else:
            st.warning("Aucune donnée du détecteur pour l'instant. Lance GameHub avec lancer_gamehub.bat.")
        st.write("GameHub surveille les processus de jeu sur ce PC et ajoute automatiquement les minutes détectées. Pour comptabiliser une partie, laisse GameHub ouvert pendant que tu joues. Le système n'enregistre pas tes frappes clavier, tes écrans ni tes mots de passe.")
        st.caption("Jeux actuellement pris en charge par le détecteur : Fortnite, Roblox, Minecraft Java/Bedrock, VALORANT, GTA V, Rocket League, Geometry Dash, Apex Legends, Counter-Strike 2, Terraria, Stardew Valley, Dota 2, Fall Guys, PUBG, Genshin Impact, Overwatch 2 et League of Legends. Les noms de processus peuvent changer après une mise à jour.")

    with st.container(border=True):
        st.markdown("#### 🔐 Connexion aux comptes Epic / Roblox / Microsoft")
        st.write("Il n'existe pas de connexion unique qui permette à GameHub de lire automatiquement le temps joué de tous ces comptes. Pour éviter de te demander des mots de passe ou de stocker des cookies, la V2 suit les jeux lancés localement sur ton PC. Les heures des consoles ou d'autres appareils ne sont pas récupérées par ce suivi local.")
        st.caption("La connexion officielle à un compte et la synchronisation du temps de jeu pourront être ajoutées plus tard uniquement si une API officielle adaptée est disponible.")

    with st.container(border=True):
        st.markdown("#### 📦 Exporter tes données")
        export_payload = {"profil_et_donnees": st.session_state.data, "suivi_automatique_local": read_auto_tracking()}
        export_data = json.dumps(export_payload, ensure_ascii=False, indent=2)
        st.download_button("Télécharger ma sauvegarde complète (.json)", export_data, file_name="gamehub_sauvegarde.json", mime="application/json", use_container_width=True)

    with st.container(border=True):
        st.markdown("#### 🧠 Configurer le Coach IA")
        st.write("Pour activer les réponses IA, crée un fichier `.env` à partir de `.env.example`, puis renseigne ta clé API OpenAI. L'utilisation de l'API peut être facturée séparément de l'abonnement ChatGPT.")
        st.code('OPENAI_API_KEY="ta-cle-api"\nOPENAI_MODEL="gpt-5.4-mini"', language="bash")
        st.caption("Ne partage jamais ton fichier .env, ne le téléverse pas sur GitHub et ne mets pas la clé dans le code public.")

    with st.container(border=True):
        st.markdown("#### 🧹 Réinitialiser GameHub")
        st.warning("Cette action efface le profil, les favoris, les sessions manuelles, les notes et les jeux que tu as ajoutés. Coche aussi la case de suivi si tu veux supprimer les heures détectées automatiquement.")
        confirm_reset = st.checkbox("Je confirme vouloir effacer mes données GameHub")
        reset_auto = st.checkbox("Effacer aussi l'historique de temps de jeu automatique")
        if st.button("Réinitialiser les données sélectionnées", type="secondary", disabled=not confirm_reset, use_container_width=True):
            st.session_state.data = copy.deepcopy(DEFAULT_DATA)
            save_data()
            if reset_auto:
                try:
                    AUTO_RESET_MARKER.touch()
                    AUTO_TRACKING_FILE.unlink(missing_ok=True)
                except OSError:
                    st.error("Le suivi automatique n'a pas pu être réinitialisé. Ferme GameHub puis réessaie.")
            st.success("Données réinitialisées.")
            st.rerun()

with st.sidebar:
    st.markdown("---")
    st.caption("GameHub v2.0 · Python + Streamlit · suivi local")
