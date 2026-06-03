import os
import requests
from typing import List, Dict, Any, Optional
from fastapi import FastAPI
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="API juridique PISTE - Agent copropriété",
    version="5.1.0",
    description="API complète copropriété compatible pipeline, avec traitement profil par profil."
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

PAGE_SIZE_LEGIFRANCE = int(os.getenv("PAGE_SIZE_LEGIFRANCE", "5"))
PAGE_SIZE_JUDILIBRE = int(os.getenv("PAGE_SIZE_JUDILIBRE", "5"))

MAX_REQUETES_LEGIFRANCE_PAR_PROFIL = int(os.getenv("MAX_REQUETES_LEGIFRANCE_PAR_PROFIL", "25"))
MAX_REQUETES_JUDILIBRE_PAR_PROFIL = int(os.getenv("MAX_REQUETES_JUDILIBRE_PAR_PROFIL", "12"))

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
            timeout=30
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


def construire_requetes_completes(requete: RequeteJuridique) -> Dict[str, List[str]]:
    base = [
        requete.requete_principale,
        *requete.requetes_secondaires,
        *requete.articles_prioritaires,
    ]

    textes_loi_1965 = [
        "loi n°65-557 du 10 juillet 1965 copropriété",
        "loi n°65-557 du 10 juillet 1965 article 1",
        "loi n°65-557 du 10 juillet 1965 article 3",
        "loi n°65-557 du 10 juillet 1965 article 5",
        "loi n°65-557 du 10 juillet 1965 article 6-2",
        "loi n°65-557 du 10 juillet 1965 article 6-3",
        "loi n°65-557 du 10 juillet 1965 article 6-4",
        "loi n°65-557 du 10 juillet 1965 article 8",
        "loi n°65-557 du 10 juillet 1965 article 10",
        "loi n°65-557 du 10 juillet 1965 article 11",
        "loi n°65-557 du 10 juillet 1965 article 12",
        "loi n°65-557 du 10 juillet 1965 article 24",
        "loi n°65-557 du 10 juillet 1965 article 25",
        "loi n°65-557 du 10 juillet 1965 article 26",
        "loi n°65-557 du 10 juillet 1965 article 43",
    ]

    decrets_reglements = [
        "décret n°67-223 du 17 mars 1967 copropriété",
        "décret n°55-22 du 4 janvier 1955 publicité foncière",
        "décret n°55-1350 du 14 octobre 1955 état descriptif de division",
        "état descriptif de division publicité foncière copropriété",
        "règlement de copropriété état descriptif de division",
    ]

    reformes_copropriete = [
        "loi SRU n°2000-1208 du 13 décembre 2000 copropriété",
        "loi ENL n°2006-872 du 13 juillet 2006 copropriété",
        "loi MOLLE n°2009-323 du 25 mars 2009 copropriété",
        "loi ALUR n°2014-366 du 24 mars 2014 copropriété",
        "loi ELAN n°2018-1021 du 23 novembre 2018 copropriété",
        "ordonnance n°2019-1101 du 30 octobre 2019 copropriété",
        "décret n°2020-834 du 2 juillet 2020 copropriété",
        "loi 3DS n°2022-217 du 21 février 2022 copropriété",
    ]

    codes = [
        "Code civil servitude fonds servant fonds dominant",
        "Code civil extinction servitude réunion des fonds",
        "Code civil droit de propriété servitude copropriété",
        "Code de la construction et de l'habitation copropriété division immeuble",
        "Code de l'urbanisme changement destination usage lot copropriété",
    ]

    sources_thematiques = [
        *base,
        f"{requete.requete_principale} loi 10 juillet 1965",
        f"{requete.requete_principale} décret 17 mars 1967",
        f"{requete.requete_principale} règlement de copropriété",
        f"{requete.requete_principale} état descriptif de division",
    ]

    jurisprudence = [
        f"{requete.requete_principale} Cour de cassation copropriété",
        f"{requete.requete_principale} chambre civile 3 copropriété",
        f"{requete.requete_principale} jurisprudence copropriété",
        f"{requete.label} Cour de cassation copropriété",
        "article 5 loi 10 juillet 1965 tantièmes copropriété jurisprudence",
        "article 10 loi 10 juillet 1965 charges copropriété jurisprudence",
        "article 43 loi 10 juillet 1965 clause réputée non écrite copropriété jurisprudence",
        "parties communes spéciales copropriété Cour de cassation",
        "jouissance privative partie commune copropriété Cour de cassation",
        "charges spéciales copropriété utilité objective Cour de cassation",
    ]

    return {
        "textes_loi_1965": unique(textes_loi_1965),
        "decrets_reglements": unique(decrets_reglements),
        "reformes_copropriete": unique(reformes_copropriete),
        "codes": unique(codes),
        "sources_thematiques": unique(sources_thematiques),
        "jurisprudence": unique(jurisprudence),
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
            timeout=20
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
            timeout=20
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
    for key in ["date", "decision_date", "dateDecision", "datePublication", "startDate", "dateSignature"]:
        if item.get(key):
            return str(item.get(key))
    return ""


def extraire_texte(item: Dict[str, Any]) -> str:
    for key in ["text", "texte", "snippet", "sommaire", "solution", "summary", "resume"]:
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

    return str(item)[:5000]


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
            "resume": texte[:4000],
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
            source.get("resume", "")[:300]
        )

        cle_txt = str(cle).lower()

        if cle_txt not in vus:
            vus.add(cle_txt)
            resultats.append(source)

    return resultats


def traiter_profil(token: Optional[str], requete: RequeteJuridique) -> Dict[str, Any]:
    requetes = construire_requetes_completes(requete)

    blocs = {
        "textes_loi_1965": [],
        "decrets_reglements": [],
        "reformes_copropriete": [],
        "codes": [],
        "sources_thematiques": [],
        "jurisprudence": [],
    }

    compteur_legifrance = 0

    for categorie in [
        "textes_loi_1965",
        "decrets_reglements",
        "reformes_copropriete",
        "codes",
        "sources_thematiques"
    ]:
        for q in requetes[categorie]:
            if compteur_legifrance >= MAX_REQUETES_LEGIFRANCE_PAR_PROFIL:
                break

            bruts = search_legifrance(token, q)
            compteur_legifrance += 1

            blocs[categorie].extend(
                normaliser_resultats(
                    bruts,
                    source="legifrance",
                    categorie=categorie,
                    requete_origine=q,
                    profil=requete.profil
                )
            )

    compteur_judilibre = 0

    for q in requetes["jurisprudence"]:
        if compteur_judilibre >= MAX_REQUETES_JUDILIBRE_PAR_PROFIL:
            break

        bruts = search_judilibre(q)
        compteur_judilibre += 1

        blocs["jurisprudence"].extend(
            normaliser_resultats(
                bruts,
                source="judilibre",
                categorie="jurisprudence",
                requete_origine=q,
                profil=requete.profil
            )
        )

    for categorie in blocs:
        blocs[categorie] = dedupliquer(blocs[categorie])

    tous_resultats = []
    for categorie in blocs:
        tous_resultats.extend(blocs[categorie])

    return {
        "profil": requete.profil,
        "label": requete.label,
        "niveau_detection": requete.niveau_detection,
        "score_detection": requete.score_detection,
        "statut": "succes",
        "requete_principale": requete.requete_principale,
        "requetes_executees": requetes,
        "points_de_controle": requete.points_de_controle,
        "textes_loi_1965": blocs["textes_loi_1965"],
        "decrets_reglements": blocs["decrets_reglements"],
        "reformes_copropriete": blocs["reformes_copropriete"],
        "codes": blocs["codes"],
        "sources_thematiques": blocs["sources_thematiques"],
        "jurisprudence": blocs["jurisprudence"],
        "resultats_juridiques": tous_resultats,
        "nombre_resultats": len(tous_resultats),
        "nombre_requetes_legifrance_executees": compteur_legifrance,
        "nombre_requetes_judilibre_executees": compteur_judilibre
    }


@app.get("/")
def accueil():
    return {
        "status": "API active",
        "version": "5.1.0",
        "environnement": PISTE_ENV,
        "message": "API juridique complète copropriété opérationnelle."
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "5.1.0",
        "piste_env": PISTE_ENV,
        "page_size_legifrance": PAGE_SIZE_LEGIFRANCE,
        "page_size_judilibre": PAGE_SIZE_JUDILIBRE,
        "max_requetes_legifrance_par_profil": MAX_REQUETES_LEGIFRANCE_PAR_PROFIL,
        "max_requetes_judilibre_par_profil": MAX_REQUETES_JUDILIBRE_PAR_PROFIL,
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
            "Pack juridique complet : loi de 1965, décret de 1967, publicité foncière, "
            "réformes SRU/ALUR/ELAN/ordonnance 2019, codes, sources thématiques et jurisprudence."
        )
    }
