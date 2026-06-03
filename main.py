import os
import requests
from typing import List, Dict, Any, Optional
from fastapi import FastAPI
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="API juridique PISTE - Agent copropriété",
    version="6.0.0",
    description=(
        "API allégée : jurisprudence, textes ciblés par profil, "
        "et textes postérieurs au décret n°2020-834 du 2 juillet 2020."
    )
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


PISTE_CLIENT_ID = os.getenv("PISTE_CLIENT_ID")
PISTE_CLIENT_SECRET = os.getenv("PISTE_CLIENT_SECRET")
PISTE_KEY_ID = os.getenv("PISTE_KEY_ID")
PISTE_ENV = os.getenv("PISTE_ENV", "sandbox").lower()

PAGE_SIZE_LEGIFRANCE = int(os.getenv("PAGE_SIZE_LEGIFRANCE", "3"))
PAGE_SIZE_JUDILIBRE = int(os.getenv("PAGE_SIZE_JUDILIBRE", "5"))

MAX_REQUETES_TEXTES_CIBLES_PAR_PROFIL = int(
    os.getenv("MAX_REQUETES_TEXTES_CIBLES_PAR_PROFIL", "6")
)
MAX_REQUETES_POST_2020_PAR_PROFIL = int(
    os.getenv("MAX_REQUETES_POST_2020_PAR_PROFIL", "4")
)
MAX_REQUETES_JURISPRUDENCE_PAR_PROFIL = int(
    os.getenv("MAX_REQUETES_JURISPRUDENCE_PAR_PROFIL", "8")
)

if PISTE_ENV == "production":
    TOKEN_URL = "https://oauth.piste.gouv.fr/api/oauth/token"
    LEGIFRANCE_URL = "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app/search"
    JUDILIBRE_URL = "https://api.piste.gouv.fr/cassation/judilibre/v1.0/search"
else:
    TOKEN_URL = "https://sandbox-oauth.piste.gouv.fr/api/oauth/token"
    LEGIFRANCE_URL = "https://sandbox-api.piste.gouv.fr/dila/legifrance/lf-engine-app/search"
    JUDILIBRE_URL = "https://sandbox-api.piste.gouv.fr/cassation/judilibre/v1.0/search"


class RequeteJuridique(BaseModel):
    profil: str = "profil_non_precise"
    label: str = "Profil non précisé"
    niveau_detection: str = "non_precise"
    score_detection: Optional[int] = None
    requete_principale: str
    requetes_secondaires: List[str] = Field(default_factory=list)
    articles_prioritaires: List[str] = Field(default_factory=list)
    points_de_controle: List[str] = Field(default_factory=list)


class PackJuridiqueRequest(BaseModel):
    dossier_id: str = "DOSSIER_NON_RENSEIGNE"
    type_dossier: str = "copropriete"
    requetes_juridiques: List[RequeteJuridique] = Field(default_factory=list)


def get_token() -> Optional[str]:
    try:
        response = requests.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(PISTE_CLIENT_ID, PISTE_CLIENT_SECRET),
            timeout=25
        )

        if response.status_code != 200:
            return None

        return response.json().get("access_token")

    except Exception:
        return None


def unique(values: List[str]) -> List[str]:
    seen = set()
    result = []

    for value in values:
        clean = " ".join(str(value or "").split()).strip()

        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            result.append(clean)

    return result


def construire_requetes(requete: RequeteJuridique) -> Dict[str, List[str]]:
    profil = requete.profil.lower()
    label = requete.label.lower()
    principal = requete.requete_principale

    base = [
        principal,
        *requete.requetes_secondaires,
        *requete.articles_prioritaires,
    ]

    textes_cibles = [
        *base,
        f"{principal} copropriété loi 10 juillet 1965",
        f"{principal} règlement de copropriété",
        f"{principal} état descriptif de division",
        f"{principal} décret 17 mars 1967",
    ]

    jurisprudence = [
        f"{principal} Cour de cassation copropriété",
        f"{principal} chambre civile 3 copropriété",
        f"{principal} jurisprudence copropriété",
        f"{requete.label} Cour de cassation copropriété",
    ]

    textes_post_2020 = [
        f"{principal} copropriété après décret 2020-834",
        f"{principal} copropriété loi 3DS 2022",
        f"{principal} copropriété réforme après 2020",
        f"{principal} copropriété texte en vigueur 2021 2022 2023 2024 2025",
    ]

    mots = f"{profil} {label} {principal}".lower()

    if "parties_communes_speciales" in mots or "parties communes spéciales" in mots or "parties communes speciales" in mots:
        textes_cibles += [
            "parties communes spéciales copropriété article 6-2",
            "parties communes spéciales lots concernés copropriété",
            "charges spéciales parties communes spéciales copropriété",
        ]
        jurisprudence += [
            "parties communes spéciales règlement copropriété Cour de cassation",
            "parties communes spéciales charges spéciales copropriété jurisprudence",
        ]
        textes_post_2020 += [
            "parties communes spéciales copropriété après ordonnance 2019 décret 2020",
            "parties communes spéciales copropriété loi 3DS 2022",
        ]

    if "jouissance" in mots:
        textes_cibles += [
            "jouissance privative partie commune copropriété article 6-3",
            "droit de jouissance privative lot bénéficiaire copropriété",
            "jouissance privative règlement de copropriété",
        ]
        jurisprudence += [
            "jouissance privative partie commune copropriété Cour de cassation",
            "droit de jouissance privative copropriété jurisprudence",
        ]
        textes_post_2020 += [
            "jouissance privative copropriété après décret 2020-834",
            "jouissance privative copropriété loi 3DS 2022",
        ]

    if "charges" in mots:
        textes_cibles += [
            "charges générales copropriété article 10 loi 1965",
            "charges spéciales copropriété article 10 loi 1965",
            "services collectifs éléments équipement commun utilité objective article 10",
        ]
        jurisprudence += [
            "charges copropriété utilité objective article 10 Cour de cassation",
            "clause répartition charges copropriété réputée non écrite",
            "répartition charges copropriété article 10 jurisprudence",
        ]
        textes_post_2020 += [
            "charges copropriété après décret 2020-834",
            "charges copropriété loi 3DS 2022",
        ]

    if "tantieme" in mots or "tantième" in mots or "quote" in mots:
        textes_cibles += [
            "calcul tantièmes copropriété article 5 loi 1965",
            "quote-part parties communes article 5 loi 1965",
            "répartition tantièmes état descriptif de division copropriété",
        ]
        jurisprudence += [
            "calcul tantièmes copropriété article 5 Cour de cassation",
            "répartition tantièmes charges copropriété jurisprudence",
        ]
        textes_post_2020 += [
            "tantièmes copropriété après décret 2020-834",
            "quote-part copropriété loi 3DS 2022",
        ]

    if "lot" in mots or "lots" in mots or "division" in mots or "réunion" in mots or "reunion" in mots:
        textes_cibles += [
            "lot de copropriété état descriptif de division",
            "division lot copropriété état descriptif de division",
            "réunion lots copropriété modificatif état descriptif de division",
            "création suppression lot copropriété publicité foncière",
        ]
        jurisprudence += [
            "division lot copropriété état descriptif de division Cour de cassation",
            "réunion lots copropriété modificatif jurisprudence",
            "suppression lot copropriété jurisprudence",
        ]
        textes_post_2020 += [
            "lot copropriété état descriptif de division après décret 2020",
            "division lot copropriété loi 3DS 2022",
        ]

    if "destination" in mots or "usage" in mots:
        textes_cibles += [
            "destination immeuble règlement copropriété article 8 loi 1965",
            "changement usage lot copropriété règlement de copropriété",
            "changement destination lot copropriété",
        ]
        jurisprudence += [
            "changement destination lot copropriété règlement Cour de cassation",
            "destination immeuble copropriété jurisprudence",
        ]
        textes_post_2020 += [
            "destination immeuble copropriété après décret 2020",
            "changement usage lot copropriété loi 3DS 2022",
        ]

    if "servitude" in mots:
        textes_cibles += [
            "Code civil servitude de passage copropriété",
            "Code civil fonds servant fonds dominant servitude",
            "servitude copropriété publicité foncière",
        ]
        jurisprudence += [
            "servitude copropriété fonds servant fonds dominant Cour de cassation",
            "servitude de passage copropriété jurisprudence",
        ]
        textes_post_2020 += [
            "servitude copropriété après 2020",
            "servitude copropriété loi 3DS 2022",
        ]

    if "chauffage" in mots:
        textes_cibles += [
            "chauffage collectif copropriété charges article 10",
            "individualisation frais chauffage copropriété",
            "répartition charges chauffage collectif copropriété",
        ]
        jurisprudence += [
            "chauffage collectif charges copropriété utilité objective Cour de cassation",
        ]
        textes_post_2020 += [
            "chauffage collectif copropriété réglementation après 2020",
            "individualisation frais chauffage copropriété 2021 2022 2023 2024",
        ]

    return {
        "textes_cibles": unique(textes_cibles)[:MAX_REQUETES_TEXTES_CIBLES_PAR_PROFIL],
        "textes_post_2020": unique(textes_post_2020)[:MAX_REQUETES_POST_2020_PAR_PROFIL],
        "jurisprudence": unique(jurisprudence)[:MAX_REQUETES_JURISPRUDENCE_PAR_PROFIL],
    }


def search_legifrance(token: Optional[str], query: str) -> List[Dict[str, Any]]:
    if not token:
        return []

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "recherche": {
            "champs": [
                {
                    "typeChamp": "ALL",
                    "criteres": [
                        {
                            "typeRecherche": "UN_DES_MOTS",
                            "valeur": query,
                            "operateur": "ET"
                        }
                    ],
                    "operateur": "ET"
                }
            ],
            "pageNumber": 1,
            "pageSize": PAGE_SIZE_LEGIFRANCE,
            "sort": "PERTINENCE"
        },
        "fond": "ALL"
    }

    try:
        response = requests.post(
            LEGIFRANCE_URL,
            headers=headers,
            json=payload,
            timeout=18
        )

        if response.status_code != 200:
            return []

        data = response.json()
        return data.get("results", []) or data.get("items", []) or []

    except Exception:
        return []


def search_judilibre(query: str) -> List[Dict[str, Any]]:
    if not PISTE_KEY_ID:
        return []

    headers = {"KeyId": PISTE_KEY_ID}

    params = {
        "query": query,
        "page": 0,
        "page_size": PAGE_SIZE_JUDILIBRE
    }

    try:
        response = requests.get(
            JUDILIBRE_URL,
            headers=headers,
            params=params,
            timeout=18
        )

        if response.status_code != 200:
            return []

        return response.json().get("results", [])

    except Exception:
        return []


def extraire_titre(item: Dict[str, Any]) -> str:
    if item.get("title"):
        return str(item.get("title"))

    if item.get("titre"):
        return str(item.get("titre"))

    titles = item.get("titles")
    if isinstance(titles, list) and titles:
        first = titles[0]
        if isinstance(first, dict):
            return str(first.get("title") or first.get("id") or "Source juridique")

    return str(item.get("id") or item.get("cid") or item.get("num") or "Source juridique")


def extraire_date(item: Dict[str, Any]) -> str:
    for key in [
        "date",
        "decision_date",
        "dateDecision",
        "datePublication",
        "startDate",
        "dateSignature"
    ]:
        if item.get(key):
            return str(item.get(key))

    return ""


def extraire_texte(item: Dict[str, Any]) -> str:
    for key in [
        "text",
        "texte",
        "snippet",
        "sommaire",
        "solution",
        "summary",
        "resume"
    ]:
        if item.get(key):
            return str(item.get(key))

    sections = item.get("sections")
    if isinstance(sections, list):
        extracts = []

        for section in sections:
            for extract in section.get("extracts", []):
                values = extract.get("values", [])

                if isinstance(values, list):
                    extracts.extend([str(value) for value in values])

        if extracts:
            return "\n".join(extracts)

    return str(item)[:4000]


def normaliser_resultats(
    resultats: List[Dict[str, Any]],
    source: str,
    categorie: str,
    requete_origine: str,
    profil: str
) -> List[Dict[str, Any]]:
    sources = []

    for item in resultats:
        if not isinstance(item, dict):
            continue

        texte = extraire_texte(item)

        sources.append({
            "source": source,
            "categorie": categorie,
            "profil": profil,
            "requete_origine": requete_origine,
            "titre": extraire_titre(item),
            "date": extraire_date(item),
            "nature": item.get("nature") or item.get("type") or item.get("origin"),
            "juridiction": item.get("jurisdiction") or item.get("juridiction"),
            "identifiant": item.get("id") or item.get("cid") or item.get("num"),
            "resume": texte[:2500],
            "donnee_originale": item
        })

    return sources


def dedupliquer(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    vus = set()
    resultats = []

    for source in sources:
        cle = (
            source.get("source"),
            source.get("categorie"),
            source.get("identifiant"),
            source.get("titre"),
            source.get("resume", "")[:250]
        )

        cle_txt = str(cle).lower()

        if cle_txt not in vus:
            vus.add(cle_txt)
            resultats.append(source)

    return resultats


def traiter_profil(token: Optional[str], requete: RequeteJuridique) -> Dict[str, Any]:
    requetes = construire_requetes(requete)

    textes_cibles = []
    textes_post_2020 = []
    jurisprudence = []

    for q in requetes["textes_cibles"]:
        bruts = search_legifrance(token, q)
        textes_cibles.extend(
            normaliser_resultats(
                bruts,
                source="legifrance",
                categorie="textes_cibles",
                requete_origine=q,
                profil=requete.profil
            )
        )

    for q in requetes["textes_post_2020"]:
        bruts = search_legifrance(token, q)
        textes_post_2020.extend(
            normaliser_resultats(
                bruts,
                source="legifrance",
                categorie="textes_post_2020",
                requete_origine=q,
                profil=requete.profil
            )
        )

    for q in requetes["jurisprudence"]:
        bruts = search_judilibre(q)
        jurisprudence.extend(
            normaliser_resultats(
                bruts,
                source="judilibre",
                categorie="jurisprudence",
                requete_origine=q,
                profil=requete.profil
            )
        )

    textes_cibles = dedupliquer(textes_cibles)
    textes_post_2020 = dedupliquer(textes_post_2020)
    jurisprudence = dedupliquer(jurisprudence)

    resultats_juridiques = []
    resultats_juridiques.extend(textes_cibles)
    resultats_juridiques.extend(textes_post_2020)
    resultats_juridiques.extend(jurisprudence)

    return {
        "profil": requete.profil,
        "label": requete.label,
        "niveau_detection": requete.niveau_detection,
        "score_detection": requete.score_detection,
        "statut": "succes",
        "requete_principale": requete.requete_principale,
        "requetes_executees": requetes,
        "points_de_controle": requete.points_de_controle,

        "textes_cibles": textes_cibles,
        "textes_post_2020": textes_post_2020,
        "jurisprudence": jurisprudence,

        "resultats_juridiques": resultats_juridiques,
        "nombre_resultats": len(resultats_juridiques),
        "nombre_requetes_textes_cibles": len(requetes["textes_cibles"]),
        "nombre_requetes_textes_post_2020": len(requetes["textes_post_2020"]),
        "nombre_requetes_jurisprudence": len(requetes["jurisprudence"])
    }


@app.get("/")
def accueil():
    return {
        "status": "API active",
        "version": "6.0.0",
        "environnement": PISTE_ENV,
        "message": "API juridique allégée : jurisprudence, textes ciblés, textes postérieurs à 2020."
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "6.0.0",
        "piste_env": PISTE_ENV,
        "page_size_legifrance": PAGE_SIZE_LEGIFRANCE,
        "page_size_judilibre": PAGE_SIZE_JUDILIBRE,
        "max_requetes_textes_cibles_par_profil": MAX_REQUETES_TEXTES_CIBLES_PAR_PROFIL,
        "max_requetes_post_2020_par_profil": MAX_REQUETES_POST_2020_PAR_PROFIL,
        "max_requetes_jurisprudence_par_profil": MAX_REQUETES_JURISPRUDENCE_PAR_PROFIL,
        "piste_client_id_present": bool(PISTE_CLIENT_ID),
        "piste_client_secret_present": bool(PISTE_CLIENT_SECRET),
        "piste_key_id_present": bool(PISTE_KEY_ID),
    }


@app.post("/pack-juridique")
def post_pack_juridique(request: PackJuridiqueRequest):
    token = get_token()

    profils = []

    for requete in request.requetes_juridiques:
        profils.append(
            traiter_profil(
                token=token,
                requete=requete
            )
        )

    total = sum(profil.get("nombre_resultats", 0) for profil in profils)

    return {
        "dossier_id": request.dossier_id,
        "type_dossier": request.type_dossier,
        "mode_piste": "render",
        "environnement_piste": PISTE_ENV,
        "nombre_profils_traites": len(profils),
        "nombre_resultats_juridiques": total,
        "profils": profils,
        "note": (
            "API allégée : les grandes réformes jusqu'au décret 2020 doivent provenir du RAG local. "
            "Render fournit uniquement les textes ciblés, les textes postérieurs à 2020 et la jurisprudence spécifique au profil."
        )
    }
