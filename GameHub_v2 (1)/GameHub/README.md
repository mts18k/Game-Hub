# 🎮 GameHub V2 — ton espace gaming

Une application de bureau locale réalisée en Python + Streamlit. Elle rassemble un catalogue de jeux, les favoris, un Coach gaming optionnel, les actualités officielles et un suivi automatique du temps de jeu Windows.

## Nouveautés de la V2

- **Actus gaming** : Epic Games / Fortnite, Roblox et Minecraft via leurs pages ou flux officiels, plus les annonces Steam pour plusieurs jeux compatibles.
- **Suivi automatique sur PC** : `tracker.py` détecte les processus de jeux connus et comptabilise leur temps sans formulaire manuel. Le fichier local de suivi est `data/auto_sessions.json`.
- **Sessions live** : GameHub indique les jeux détectés actuellement et actualise le statut pendant que l'application reste ouverte.
- **Profil local** : pseudo et avatar personnalisables. Il ne s'agit pas d'un compte en ligne.
- **Design revu** : police Space Grotesk et police Rajdhani dans la barre latérale, couleurs gaming et panneaux actualisés.
- Catalogue filtrable, favoris, notes, jeux personnalisés, graphiques de temps de jeu, générateur de pseudos et Coach IA optionnel.

## Installer et lancer sur Windows

1. Installe **Python 3.10 ou plus récent** depuis [python.org](https://www.python.org/downloads/). Si l'installateur le propose, coche **Add Python to PATH**.
2. Décompresse `GameHub.zip` dans un dossier.
3. Double-clique sur **`lancer_gamehub.bat`**.
4. Lors du premier lancement, le fichier crée un environnement Python local et installe les dépendances. Une connexion Internet est nécessaire pour cette étape.
5. GameHub s'ouvre dans le navigateur. **Laisse GameHub ouvert pendant tes sessions** : le processus `tracker.py` compte les processus compatibles tant que GameHub est lancé. Il se ferme après l'arrêt de l'application.

Pour fermer GameHub, reviens à la fenêtre principale et fais `Ctrl + C`. Le processus de suivi se termine peu après.

### Lancer manuellement en cas de problème

Ouvre un terminal dans le dossier GameHub et exécute :

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
start /min .venv\Scripts\python.exe tracker.py
.venv\Scripts\python.exe -m streamlit run app.py
```

## Suivi automatique : limites à connaître

Le suivi local détecte certains noms de processus Windows. Il ne demande pas de connexion aux comptes Epic, Roblox ou Microsoft et n'accède pas à leurs mots de passe. Il comptabilise le temps où le jeu tourne, même s'il est minimisé, et non uniquement le temps passé avec la fenêtre au premier plan.

Jeux détectés dans cette version : Fortnite, Roblox, Minecraft Java/Bedrock, VALORANT, GTA V, Rocket League, Geometry Dash, Apex Legends, Counter-Strike 2, Terraria, Stardew Valley, Dota 2, Fall Guys, PUBG, Genshin Impact, Overwatch 2 et League of Legends. Les noms de fichiers peuvent varier selon la version ou le launcher. Si un jeu n'est pas compté, consulte son exécutable Windows et ajoute-le dans `tracker.py` à `PROCESS_GAMES`.

Les heures des consoles, du téléphone ou des sessions réalisées quand GameHub n'est pas lancé ne sont pas détectées par ce suivi local. La V2 n'intègre pas une connexion automatique aux comptes de plateforme, car il n'existe pas une API publique commune qui expose le temps de jeu personnel pour Epic Games, Roblox et Minecraft. Ne saisis pas tes mots de passe de ces services dans GameHub.

## Actualités

- **Epic Games / Fortnite** : page officielle des actualités Fortnite.
- **Roblox** : salle de presse officielle Roblox.
- **Minecraft** : flux RSS officiel de Minecraft.net.
- **Steam** : API publique pour les jeux présents dans le catalogue qui ont un identifiant Steam.

Le chargement des actus demande une connexion Internet. Si un site change sa structure, son extraction HTML peut momentanément ne rien afficher : dans ce cas, ouvre le lien officiel fourni dans l'interface.

## Activer le Coach IA (facultatif)

1. Crée une clé API OpenAI dans ton compte API.
2. Copie `.env.example` sous le nom `.env`.
3. Renseigne `OPENAI_API_KEY` et un modèle disponible dans ton compte.
4. Redémarre GameHub.

L'usage de l'API peut être facturé séparément de l'abonnement ChatGPT. Ne partage jamais le fichier `.env` et ne l'ajoute pas à GitHub.

## Données et confidentialité

- `data/user_data.json` : profil local, favoris, notes, jeux ajoutés et sessions entrées manuellement.
- `data/auto_sessions.json` : temps détecté par `tracker.py`.
- Aucun identifiant ou mot de passe Epic, Roblox ou Microsoft n'est demandé ou sauvegardé.
- Les données restent dans le dossier GameHub sur cet ordinateur. Fais une sauvegarde depuis « Mon profil & paramètres » avant de réinstaller ou déplacer le dossier.

## Structure

```text
GameHub/
├── app.py
├── tracker.py
├── lancer_gamehub.bat
├── requirements.txt
├── .env.example
├── README.md
└── data/
```
