import os
import requests
from typing import List, Dict, Any, Optional
from fastapi import FastAPI
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="API juridique PISTE - Agent copropriété",
    version="5.0.0",
    description="API complète pour interroger Légifrance et Judilibre pour les dossiers de copropriété."
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

PAGE_SIZE_LEGIFRANCE = int(os.getenv("PAGE_SIZE_LEGIFRANCE", "10"))
PAGE_SIZE_JUDILIBRE = int(os.getenv("PAGE_SIZE_JUDILIBRE", "10"))

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

    # Compatibilité avec appel simple éventuel
    query: Optional[str] = None
    type_operation: Optional[str] = None


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


def construire_requetes_completes(requete: RequeteJuridique, type_dossier: str) -> Dict[str, List[str]]:
    base = [
        requete.requete_principale,
        *requete.requetes_secondaires,
        *requete.articles_prioritaires,
    ]

    socle_loi_1965 = [
        "loi n°65-557 du 10 juillet 1965 statut de la copropriété des immeubles bâtis",
        "loi n°65-557 du 10 juillet 1965 article 1 copropriété",
        "loi n°65-557 du 10 juillet 1965 article 2 parties privatives",
        "loi n°65-557 du 10 juillet 1965 article 3 parties communes",
        "loi n°65-557 du 10 juillet 1965 article 5 quote-part parties communes",
        "loi n°65-557 du 10 juillet 1965 article 6-2 parties communes spéciales",
        "loi n°65-557 du 10 juillet 1965 article 6-3 jouissance privative",
        "loi n°65-557 du 10 juillet 1965 article 6-4 parties communes spéciales jouissance privative",
        "loi n°65-557 du 10 juillet 1965 article 8 règlement de copropriété destination immeuble",
        "loi n°65-557 du 10 juillet 1965 article 10 charges copropriété utilité",
        "loi n°65-557 du 10 juillet 1965 article 11 modification répartition charges",
        "loi n°65-557 du 10 juillet 1965 article 12 action révision charges",
        "loi n°65-557 du 10 juillet 1965 article 24 assemblée générale majorité",
        "loi n°65-557 du 10 juillet 1965 article 25 majorité absolue",
        "loi n°65-557 du 10 juillet 1965 article 26 double majorité unanimité",
        "loi n°65-557 du 10 juillet 1965 article 43 clauses réputées non écrites",
    ]

    decrets_reglements = [
        "décret n°67-223 du 17 mars 1967 copropriété",
        "décret n°55-22 du 4 janvier 1955 publicité foncière état descriptif de division",
        "décret n°55-1350 du 14 octobre 1955 état descriptif de division publicité foncière",
        "état descriptif de division publicité foncière copropriété",
        "règlement de copropriété état descriptif de division publicité foncière",
    ]

    reformes = [
        "loi SRU n°2000-1208 du 13 décembre 2000 copropriété loi 1965",
        "loi ENL n°2006-872 du 13 juillet 2006 copropriété",
        "loi MOLLE n°2009-323 du 25 mars 2009 copropriété",
        "loi ALUR n°2014-366 du 24 mars 2014 copropriété",
        "loi ELAN n°2018-1021 du 23 novembre 2018 copropriété parties communes spéciales jouissance privative",
        "ordonnance n°2019-1101 du 30 octobre 2019 réforme droit copropriété",
        "décret n°2020-834 du 2 juillet 2020 copropriété ordonnance 2019",
        "loi 3DS n°2022-217 du 21 février 2022 copropriété",
    ]

    codes = [
        "Code civil servitude fonds servant fonds dominant",
        "Code civil extinction servitude réunion des fonds",
        "Code civil indivision copropriété parties communes",
        "Code civil droit de propriété servitude copropriété",
        "Code de la construction et de l'habitation copropriété division immeuble",
        "Code de l'urbanisme changement destination usage lot copropriété",
    ]

    thematiques = [
        *base,
        f"{requete.profil} copropriété",
        f"{requete.label} copropriété",
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
        "textes_loi_1965": unique(socle_loi_1965),
        "decrets_reglements": unique(decrets_reglements),
        "reformes_copropriete": unique(reformes),
        "codes": unique(codes),
        "sources_thematiques": unique(thematiques),
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
            timeout=30
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
            timeout=30
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

    titles = item.get("titles")
    if isinstance(titles, list) and titles:
        first = titles[0]
        if isinstance(first, dict):
            return str(first.get("startDate") or "")

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

        titre = extraire_titre(item)
        date = extraire_date(item)
        texte = extraire_texte(item)

        sources.append({
            "source": source,
            "categorie": categorie,
            "profil": profil,
            "requete_origine": requete_origine,
            "titre": titre,
            "date": date,
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


def traiter_profil(token: Optional[str], requete: RequeteJuridique, type_dossier: str) -> Dict[str, Any]:
    requetes = construire_requetes_completes(requete, type_dossier)

    blocs = {
        "textes_loi_1965": [],
        "decrets_reglements": [],
        "reformes_copropriete": [],
        "codes": [],
        "sources_thematiques": [],
        "jurisprudence": [],
    }

    for categorie in ["textes_loi_1965", "decrets_reglements", "reformes_copropriete", "codes", "sources_thematiques"]:
        for q in requetes[categorie]:
            bruts = search_legifrance(token, q)
            blocs[categorie].extend(
                normaliser_resultats(bruts, "legifrance", categorie, q, requete.profil)
            )

    for q in requetes["jurisprudence"]:
        bruts = search_judilibre(q)
        blocs["jurisprudence"].extend(
            normaliser_resultats(bruts, "judilibre", "jurisprudence", q, requete.profil)
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
        "nombre_resultats": len(tous_resultats)
    }


@app.get("/")
def accueil():
    return {
        "status": "API active",
        "version": "5.0.0",
        "environnement": PISTE_ENV,
        "message": "API juridique complète copropriété opérationnelle."
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "5.0.0",
        "piste_env": PISTE_ENV,
        "legifrance_page_size": PAGE_SIZE_LEGIFRANCE,
        "judilibre_page_size": PAGE_SIZE_JUDILIBRE,
        "piste_client_id_present": bool(PISTE_CLIENT_ID),
        "piste_client_secret_present": bool(PISTE_CLIENT_SECRET),
        "piste_key_id_present": bool(PISTE_KEY_ID),
    }


@app.post("/pack-juridique")
def post_pack_juridique(request: PackJuridiqueRequest):
    token = get_token()

    requetes = list(request.requetes_juridiques)

    if not requetes and request.query:
        requetes = [
            RequeteJuridique(
                profil=request.type_operation or "recherche_simple",
                label=request.type_operation or "Recherche simple",
                niveau_detection="manuel",
                requete_principale=request.query,
                requetes_secondaires=[],
                articles_prioritaires=[],
                points_de_controle=[]
            )
        ]

    profils = []

    for requete in requetes:
        profils.append(
            traiter_profil(
                token=token,
                requete=requete,
                type_dossier=request.type_dossier
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


@app.get("/pack-juridique")
def get_pack_juridique(query: str, type_dossier: str = "copropriete", type_operation: str = "recherche_simple"):
    request = PackJuridiqueRequest(
        dossier_id="REQUETE_GET",
        type_dossier=type_dossier,
        query=query,
        type_operation=type_operation,
        requetes_juridiques=[]
    )

    return post_pack_juridique(request)
