import os
import time
import json
import requests

from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="API juridique PISTE - Agent copropriété",
    version="4.0.0",
    description="API intermédiaire Render pour interroger Légifrance et Judilibre via PISTE."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


PISTE_ENV = os.getenv("PISTE_ENV", "sandbox").lower()

URLS = {
    "sandbox": {
        "oauth": "https://sandbox-oauth.piste.gouv.fr/api/oauth/token",
        "legifrance": "https://sandbox-api.piste.gouv.fr/dila/legifrance/lf-engine-app/search",
        "judilibre": "https://sandbox-api.piste.gouv.fr/cassation/judilibre/v1.0/search",
    },
    "production": {
        "oauth": "https://oauth.piste.gouv.fr/api/oauth/token",
        "legifrance": "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app/search",
        "judilibre": "https://api.piste.gouv.fr/cassation/judilibre/v1.0/search",
    },
}

PISTE_CLIENT_ID = os.getenv("PISTE_CLIENT_ID", "")
PISTE_CLIENT_SECRET = os.getenv("PISTE_CLIENT_SECRET", "")
PISTE_KEY_ID = os.getenv("PISTE_KEY_ID", "")


class RequeteJuridique(BaseModel):
    profil: str = Field(..., description="Profil juridique détecté par l’agent.")
    label: Optional[str] = None
    niveau_detection: Optional[str] = None
    score_detection: Optional[int] = None

    requete_principale: str
    requetes_secondaires: List[str] = []
    articles_prioritaires: List[str] = []
    exclusions: List[str] = []
    points_de_controle: List[str] = []


class PackJuridiqueRequest(BaseModel):
    dossier_id: Optional[str] = None
    type_dossier: Optional[str] = "modificatif_copropriete"
    requetes_juridiques: List[RequeteJuridique]


def check_config() -> None:
    if PISTE_ENV not in URLS:
        raise HTTPException(status_code=500, detail="PISTE_ENV doit être sandbox ou production.")

    missing = []

    if not PISTE_CLIENT_ID:
        missing.append("PISTE_CLIENT_ID")

    if not PISTE_CLIENT_SECRET:
        missing.append("PISTE_CLIENT_SECRET")

    if not PISTE_KEY_ID:
        missing.append("PISTE_KEY_ID")

    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Variables d’environnement manquantes sur Render : {', '.join(missing)}"
        )


def get_token() -> str:
    check_config()

    response = requests.post(
        URLS[PISTE_ENV]["oauth"],
        data={
            "grant_type": "client_credentials",
            "client_id": PISTE_CLIENT_ID,
            "client_secret": PISTE_CLIENT_SECRET,
        },
        timeout=30,
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Erreur OAuth PISTE : {response.status_code} - {response.text[:500]}"
        )

    data = response.json()
    token = data.get("access_token")

    if not token:
        raise HTTPException(status_code=502, detail="Token PISTE absent de la réponse OAuth.")

    return token


def get_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-API-Key": PISTE_KEY_ID,
        "Content-Type": "application/json",
    }


def build_queries(requete: RequeteJuridique) -> List[str]:
    queries = []

    if requete.requete_principale:
        queries.append(requete.requete_principale)

    for item in requete.requetes_secondaires:
        if item and item not in queries:
            queries.append(item)

    for article in requete.articles_prioritaires:
        if article and article not in queries:
            queries.append(article)

    return queries[:8]


def search_legifrance(query: str, token: str, max_results: int = 5) -> Dict[str, Any]:
    headers = get_headers(token)

    payload = {
        "recherche": {
            "champs": [
                {
                    "typeChamp": "ALL",
                    "criteres": [
                        {
                            "typeRecherche": "TOUS_LES_MOTS_DANS_UN_CHAMP",
                            "valeur": query,
                            "operateur": "ET",
                        }
                    ],
                    "operateur": "ET",
                }
            ],
            "filtres": [],
            "sort": "PERTINENCE",
            "fromAdvancedRecherche": False,
            "secondSort": "DATE_DESC",
        },
        "fond": "ALL",
        "pageSize": max_results,
        "pageNumber": 1,
    }

    try:
        response = requests.post(
            URLS[PISTE_ENV]["legifrance"],
            headers=headers,
            json=payload,
            timeout=40,
        )

        return {
            "source": "legifrance",
            "query": query,
            "statut_http": response.status_code,
            "succes": response.ok,
            "donnees": response.json() if response.ok else {},
            "erreur": None if response.ok else response.text[:500],
        }

    except Exception as error:
        return {
            "source": "legifrance",
            "query": query,
            "statut_http": None,
            "succes": False,
            "donnees": {},
            "erreur": str(error),
        }


def search_judilibre(query: str, token: str, max_results: int = 5) -> Dict[str, Any]:
    headers = get_headers(token)

    params = {
        "query": query,
        "page_size": max_results,
    }

    try:
        response = requests.get(
            URLS[PISTE_ENV]["judilibre"],
            headers=headers,
            params=params,
            timeout=40,
        )

        return {
            "source": "judilibre",
            "query": query,
            "statut_http": response.status_code,
            "succes": response.ok,
            "donnees": response.json() if response.ok else {},
            "erreur": None if response.ok else response.text[:500],
        }

    except Exception as error:
        return {
            "source": "judilibre",
            "query": query,
            "statut_http": None,
            "succes": False,
            "donnees": {},
            "erreur": str(error),
        }


def call_piste_for_profile(requete: RequeteJuridique, token: str) -> Dict[str, Any]:
    queries = build_queries(requete)
    resultats_bruts = []

    for query in queries:
        resultats_bruts.append(
            search_legifrance(
                query=query,
                token=token,
                max_results=5,
            )
        )

        time.sleep(0.2)

        resultats_bruts.append(
            search_judilibre(
                query=query,
                token=token,
                max_results=5,
            )
        )

        time.sleep(0.2)

    return {
        "profil": requete.profil,
        "label": requete.label,
        "niveau_detection": requete.niveau_detection,
        "score_detection": requete.score_detection,
        "mode": "render",
        "requete_principale": requete.requete_principale,
        "requetes_executees": queries,
        "exclusions": requete.exclusions,
        "points_de_controle": requete.points_de_controle,
        "resultats_bruts": resultats_bruts,
    }


@app.get("/")
def accueil():
    return {
        "status": "API active",
        "version": "4.0.0",
        "piste_env": PISTE_ENV,
        "message": "API Render prête pour interroger PISTE."
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "piste_env": PISTE_ENV,
        "has_client_id": bool(PISTE_CLIENT_ID),
        "has_client_secret": bool(PISTE_CLIENT_SECRET),
        "has_key_id": bool(PISTE_KEY_ID),
    }


@app.post("/pack-juridique")
def post_pack_juridique(request: PackJuridiqueRequest):
    token = get_token()

    resultats_api = []

    for requete in request.requetes_juridiques:
        try:
            resultat = call_piste_for_profile(
                requete=requete,
                token=token,
            )

            resultats_api.append({
                "profil": requete.profil,
                "statut": "succes",
                "resultats": resultat,
            })

        except Exception as error:
            resultats_api.append({
                "profil": requete.profil,
                "statut": "erreur",
                "erreur": str(error),
                "resultats": {},
            })

    return {
        "dossier_id": request.dossier_id,
        "type_dossier": request.type_dossier,
        "mode_piste": "render",
        "environnement_piste": PISTE_ENV,
        "nombre_requetes": len(request.requetes_juridiques),
        "resultats_api_juridique_bruts": resultats_api,
    }
