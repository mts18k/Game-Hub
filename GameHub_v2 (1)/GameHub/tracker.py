from __future__ import annotations

"""Suivi local des jeux Windows. Ne se connecte à aucun compte externe."""

import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
TRACKING_FILE = DATA_DIR / "auto_sessions.json"
RESET_MARKER = DATA_DIR / ".reset_auto_tracking"
POLL_SECONDS = 10

# Noms d'exécutables courants. Le lanceur Epic/Steam seul n'est volontairement
# pas suivi : on compte le jeu lancé, pas le temps passé dans le launcher.
PROCESS_GAMES: dict[str, tuple[str, set[str]]] = {
    "fortnite": ("Fortnite", {"fortniteclient-win64-shipping.exe", "fortniteclient-win64-shipping_be.exe", "fortniteclient-win64-shipping_eac_eos.exe"}),
    "roblox": ("Roblox", {"robloxplayerbeta.exe"}),
    "minecraft": ("Minecraft", {"minecraft.windows.exe", "minecraft.exe"}),
    "valorant": ("VALORANT", {"valorant-win64-shipping.exe"}),
    "gtav": ("GTA V", {"gta5.exe", "gta5_enhanced.exe", "playgtav.exe"}),
    "rocketleague": ("Rocket League", {"rocketleague.exe"}),
    "geometrydash": ("Geometry Dash", {"geometrydash.exe"}),
    "apex": ("Apex Legends", {"r5apex.exe"}),
    "cs2": ("Counter-Strike 2", {"cs2.exe"}),
    "terraria": ("Terraria", {"terraria.exe"}),
    "stardew": ("Stardew Valley", {"stardew valley.exe", "stardewvalley.exe"}),
    "dota2": ("Dota 2", {"dota2.exe"}),
    "fallguys": ("Fall Guys", {"fallguys_client_game.exe", "fallguys_client_game-win64-shipping.exe"}),
    "pubg": ("PUBG: BATTLEGROUNDS", {"tslgame.exe"}),
    "genshin": ("Genshin Impact", {"yuanshen.exe", "genshinimpact.exe"}),
    "overwatch": ("Overwatch 2", {"overwatch.exe"}),
    "leagueoflegends": ("League of Legends", {"league of legends.exe"}),
}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_state() -> dict[str, Any]:
    if TRACKING_FILE.exists():
        try:
            state = json.loads(TRACKING_FILE.read_text(encoding="utf-8"))
            if isinstance(state, dict) and isinstance(state.get("sessions", []), list):
                state.setdefault("sessions", [])
                return state
        except (OSError, json.JSONDecodeError):
            pass
    return {"sessions": [], "last_tick_at": None, "tracker_version": 1}


def write_state(state: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = TRACKING_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, TRACKING_FILE)


def detect_running_games() -> dict[str, str]:
    found: dict[str, str] = {}
    try:
        for proc in psutil.process_iter(attrs=["name", "cmdline"]):
            info = proc.info
            name = (info.get("name") or "").casefold()
            cmdline = " ".join(info.get("cmdline") or []).casefold()
            for game_id, (display_name, executables) in PROCESS_GAMES.items():
                if name in executables:
                    found[game_id] = display_name

            # Java Edition: compter javaw.exe uniquement si sa ligne de commande
            # ressemble à celle du client Minecraft, pas chaque programme Java.
            if name == "javaw.exe" and (
                "net.minecraft.client.main.main" in cmdline
                or ("minecraft" in cmdline and ("--gameDir".casefold() in cmdline or "minecraftlauncher" in cmdline))
            ):
                found["minecraft"] = "Minecraft"
    except (psutil.Error, OSError):
        pass
    return found


def streamlit_app_running() -> bool:
    """Indique si ce GameHub semble encore lancé, pour arrêter le tracker après fermeture."""
    try:
        for proc in psutil.process_iter(attrs=["name", "cmdline"]):
            args = proc.info.get("cmdline") or []
            joined = " ".join(args).casefold()
            process_name = (proc.info.get("name") or "").casefold()
            is_python_or_streamlit = process_name in {"python.exe", "pythonw.exe", "streamlit.exe", "python", "streamlit"}
            if is_python_or_streamlit and "streamlit" in joined and "app.py" in joined and str(ROOT).casefold() in joined:
                return True
    except (psutil.Error, OSError):
        return True  # Ne pas arrêter par erreur si Windows bloque l'accès à un processus.
    return False


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    state = read_state()
    launched_at = time.monotonic()
    last_seen_app = launched_at
    previous_tick = time.monotonic()

    while True:
        # L'interface peut demander une remise à zéro même lorsque le tracker est actif.
        if RESET_MARKER.exists():
            state = {"sessions": [], "last_tick_at": None, "tracker_version": 1}
            try:
                RESET_MARKER.unlink(missing_ok=True)
                TRACKING_FILE.unlink(missing_ok=True)
            except OSError:
                pass
        now_mono = time.monotonic()
        is_app_running = streamlit_app_running()
        if is_app_running:
            last_seen_app = now_mono
        elif now_mono - launched_at > 120 and now_mono - last_seen_app > 45:
            # Quitter en arrière-plan après la fermeture de GameHub.
            break

        current = detect_running_games()
        delta = max(0.0, min(now_mono - previous_tick, POLL_SECONDS * 2))
        previous_tick = now_mono
        sessions = state.setdefault("sessions", [])
        active_by_game: dict[str, dict[str, Any]] = {
            str(s.get("game_id")): s for s in sessions
            if not s.get("ended_at") and s.get("game_id")
        }

        # Fermer les sessions dont le jeu n'est plus détecté.
        for game_id, session in list(active_by_game.items()):
            if game_id not in current:
                session["ended_at"] = now_iso()
                session["minutes"] = int(float(session.get("seconds", 0)) // 60)

        # Créer ou mettre à jour la session de chaque jeu détecté.
        for game_id, game_name in current.items():
            session = active_by_game.get(game_id)
            if session is None or session.get("ended_at"):
                session = {
                    "id": uuid.uuid4().hex,
                    "game_id": game_id,
                    "game": game_name,
                    "started_at": now_iso(),
                    "ended_at": None,
                    "seconds": 0.0,
                    "minutes": 0,
                    "date": datetime.now().astimezone().date().isoformat(),
                    "mode": "Automatique",
                    "note": "Détecté sur ce PC",
                    "source": "auto",
                }
                sessions.append(session)
            else:
                session["seconds"] = round(float(session.get("seconds", 0)) + delta, 1)
                session["minutes"] = int(float(session.get("seconds", 0)) // 60)
                session["date"] = str(session.get("started_at", now_iso()))[:10]

        # Limiter la taille du fichier sans supprimer les sessions actives.
        if len(sessions) > 1200:
            active_ids = {s.get("id") for s in sessions if not s.get("ended_at")}
            completed = [s for s in sessions if s.get("id") not in active_ids]
            active = [s for s in sessions if s.get("id") in active_ids]
            state["sessions"] = completed[-1100:] + active
        state["last_tick_at"] = now_iso()
        state["tracker_version"] = 1
        try:
            write_state(state)
        except OSError:
            # Si le fichier est temporairement bloqué, réessayer à la prochaine boucle.
            pass
        time.sleep(POLL_SECONDS)

    # À la sortie du site, noter la fin des sessions encore actives.
    for session in state.get("sessions", []):
        if not session.get("ended_at"):
            session["ended_at"] = now_iso()
            session["minutes"] = int(float(session.get("seconds", 0)) // 60)
    state["last_tick_at"] = now_iso()
    try:
        write_state(state)
    except OSError:
        pass


if __name__ == "__main__":
    main()
