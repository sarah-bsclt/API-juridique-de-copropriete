import os
import requests
from typing import List, Dict, Any
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="API Pack Juridique Copropriété",
    version="4.0.0",
    description="API juridique copropriété : lois, décrets, codes, réformes et jurisprudence."
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

if PISTE_ENV == "production":
    TOKEN_URL = "https://oauth.piste.gouv.fr/api/oauth/token"
    LEGIFRANCE_URL = "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app/search"
    JUDILIBRE_URL = "https://api.piste.gouv.fr/cassation/judilibre/v1.0/search"
else:
    TOKEN_URL = "https://sandbox-oauth.piste.gouv.fr/api/oauth/token"
    LEGIFRANCE_URL = "https://sandbox-api.piste.gouv.fr/dila/legifrance/lf-engine-app/search"
    JUDILIBRE_URL = "https://sandbox-api.piste.gouv.fr/cassation/judilibre/v1.0/search"


PAGE_SIZE_LEGIFRANCE = int(os.getenv("PAGE_SIZE_LEGIFRANCE", "10"))
PAGE_SIZE_JUDILIBRE = int(os.getenv("PAGE_SIZE_JUDILIBRE", "10"))


class PackJuridiqueRequest(BaseModel):
    query: str
    type_dossier: str = "copropriete"
    type_operation: str = "non précisé"


def get_token():
    response = requests.post(
        TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=(PISTE_CLIENT_ID, PISTE_CLIENT_SECRET),
        timeout=30
    )

    if response.status_code != 200:
        return None

    return response.json().get("access_token")


def unique(values: List[str]) -> List[str]:
    seen = set()
    result = []

    for value in values:
        clean = " ".join(str(value).split()).strip()

        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            result.append(clean)

    return result


def construire_requetes(query: str, type_operation: str) -> Dict[str, List[str]]:
    q = query.strip()
    op = type_operation.strip()
    mots = f"{q} {op}".lower()

    socle_loi_1965 = [
        "loi n°65-557 du 10 juillet 1965 copropriété article 1",
        "loi n°65-557 du 10 juillet 1965 copropriété article 3",
        "loi n°65-557 du 10 juillet 1965 copropriété article 5",
        "loi n°65-557 du 10 juillet 1965 copropriété article 6-2",
        "loi n°65-557 du 10 juillet 1965 copropriété article 6-3",
        "loi n°65-557 du 10 juillet 1965 copropriété article 6-4",
        "loi n°65-557 du 10 juillet 1965 copropriété article 8",
        "loi n°65-557 du 10 juillet 1965 copropriété article 10",
        "loi n°65-557 du 10 juillet 1965 copropriété article 24",
        "loi n°65-557 du 10 juillet 1965 copropriété article 25",
        "loi n°65-557 du 10 juillet 1965 copropriété article 26",
        "loi n°65-557 du 10 juillet 1965 copropriété article 43",
    ]

    decrets_reglements = [
        "décret n°67-223 du 17 mars 1967 copropriété",
        "décret n°55-22 du 4 janvier 1955 publicité foncière état descriptif de division",
        "décret n°55-1350 du 14 octobre 1955 publicité foncière état descriptif de division",
        "état descriptif de division publicité foncière copropriété",
        "règlement de copropriété état descriptif de division publicité foncière",
    ]

    reformes_copropriete = [
        "loi SRU n°2000-1208 du 13 décembre 2000 copropriété loi 1965",
        "loi ENL n°2006-872 du 13 juillet 2006 copropriété",
        "loi ALUR n°2014-366 du 24 mars 2014 copropriété règlement de copropriété",
        "loi ELAN n°2018-1021 du 23 novembre 2018 copropriété parties communes spéciales",
        "ordonnance n°2019-1101 du 30 octobre 2019 copropriété loi 1965",
        "décret n°2020-834 du 2 juillet 2020 copropriété ordonnance 2019",
        "loi 3DS n°2022-217 du 21 février 2022 copropriété",
    ]

    codes = [
        "Code civil servitude fonds servant fonds dominant",
        "Code civil extinction servitude réunion des fonds",
        "Code civil indivision copropriété parties communes",
        "Code de la construction et de l'habitation copropriété division immeuble",
        "Code de l'urbanisme changement destination lot copropriété",
    ]

    thematiques = [
        q,
        f"{q} copropriété",
        f"{q} loi 10 juillet 1965",
        f"{q} décret 17 mars 1967",
        f"{q} règlement de copropriété",
        f"{q} état descriptif de division",
    ]

    jurisprudence = [
        f"{q} jurisprudence Cour de cassation copropriété",
        f"{q} chambre civile 3 copropriété",
        f"{q} clause réputée non écrite copropriété",
        f"{q} article 10 loi 10 juillet 1965 jurisprudence",
        f"{q} article 5 loi 10 juillet 1965 jurisprudence",
    ]

    if "parties communes" in mots or "spéciales" in mots or "speciales" in mots:
        thematiques += [
            "parties communes spéciales copropriété article 6-2 loi 1965",
            "parties communes spéciales lots concernés copropriété",
            "charges spéciales parties communes spéciales copropriété",
        ]
        jurisprudence += [
            "parties communes spéciales règlement copropriété Cour de cassation",
            "parties communes spéciales charges spéciales copropriété jurisprudence",
        ]

    if "jouissance" in mots:
        thematiques += [
            "jouissance privative partie commune copropriété article 6-3",
            "droit de jouissance privative lot bénéficiaire copropriété",
        ]
        jurisprudence += [
            "jouissance privative partie commune copropriété Cour de cassation",
        ]

    if "tantième" in mots or "tantieme" in mots or "quote" in mots:
        thematiques += [
            "calcul tantièmes copropriété article 5 loi 1965",
            "quote-part parties communes article 5 loi 1965",
            "répartition tantièmes état descriptif de division copropriété",
        ]
        jurisprudence += [
            "calcul tantièmes copropriété article 5 Cour de cassation",
            "répartition tantièmes charges copropriété jurisprudence",
        ]

    if "charges" in mots:
        thematiques += [
            "charges générales copropriété article 10 loi 1965",
            "charges spéciales copropriété article 10 loi 1965",
            "services collectifs éléments équipement commun utilité objective article 10",
        ]
        jurisprudence += [
            "charges copropriété utilité objective article 10 Cour de cassation",
            "clause répartition charges copropriété réputée non écrite",
        ]

    if "chauffage" in mots:
        thematiques += [
            "chauffage collectif copropriété charges article 10",
            "individualisation frais chauffage copropriété",
            "répartition charges chauffage collectif utilité objective copropriété",
        ]
        jurisprudence += [
            "chauffage collectif charges copropriété utilité objective Cour de cassation",
        ]

    if "servitude" in mots:
        codes += [
            "Code civil servitude de passage",
            "Code civil extinction servitude confusion fonds",
        ]
        jurisprudence += [
            "servitude copropriété fonds servant fonds dominant Cour de cassation",
        ]

    if "destination" in mots or "usage" in mots:
        thematiques += [
            "destination immeuble règlement copropriété article 8 loi 1965",
            "changement usage lot copropriété règlement de copropriété",
        ]
        jurisprudence += [
            "changement destination lot copropriété règlement Cour de cassation",
        ]

    return {
        "textes_loi_1965": unique(socle_loi_1965),
        "decrets_reglements": unique(decrets_reglements),
        "reformes_copropriete": unique(reformes_copropriete),
        "codes": unique(codes),
        "thematiques": unique(thematiques),
        "jurisprudence": unique(jurisprudence),
    }


def search_legifrance(token: str, query: str) -> List[Dict[str, Any]]:
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

    return str(item.get("id") or "Source juridique")


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

    titles = item.get("titles")

    if isinstance(titles, list) and titles:
        first = titles[0]
        if isinstance(first, dict):
            return str(first.get("startDate") or "")

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

    return str(item)[:3000]


def normaliser_resultats(
    resultats: List[Dict[str, Any]],
    source: str,
    categorie: str,
    requete_origine: str
) -> List[Dict[str, Any]]:

    sources = []
    vus = set()

    for item in resultats:
        if not isinstance(item, dict):
            continue

        titre = extraire_titre(item)
        date = extraire_date(item)
        texte = extraire_texte(item)

        cle = (
            source,
            categorie,
            titre[:200].lower(),
            texte[:300].lower()
        )

        if cle in vus:
            continue

        vus.add(cle)

        sources.append({
            "source": source,
            "categorie": categorie,
            "requete_origine": requete_origine,
            "titre": titre,
            "date": date,
            "nature": item.get("nature") or item.get("type") or item.get("origin"),
            "juridiction": item.get("jurisdiction") or item.get("juridiction"),
            "identifiant": item.get("id") or item.get("cid") or item.get("num"),
            "extrait": texte[:4000],
            "donnee_originale": item
        })

    return sources


def rechercher_legifrance_par_categories(
    token: str,
    requetes: Dict[str, List[str]]
) -> Dict[str, List[Dict[str, Any]]]:

    resultats = {
        "textes_loi_1965": [],
        "decrets_reglements": [],
        "reformes_copropriete": [],
        "codes": [],
        "thematiques": [],
    }

    for categorie in resultats.keys():
        for requete in requetes.get(categorie, []):
            bruts = search_legifrance(token, requete)
            resultats[categorie].extend(
                normaliser_resultats(
                    bruts,
                    source="legifrance",
                    categorie=categorie,
                    requete_origine=requete
                )
            )

    return resultats


def rechercher_judilibre(
    requetes: Dict[str, List[str]]
) -> List[Dict[str, Any]]:

    resultats = []

    for requete in requetes.get("jurisprudence", []):
        bruts = search_judilibre(requete)
        resultats.extend(
            normaliser_resultats(
                bruts,
                source="judilibre",
                categorie="jurisprudence",
                requete_origine=requete
            )
        )

    return resultats


def dedupliquer_sources(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    vus = set()
    resultats = []

    for source in sources:
        cle = (
            source.get("source"),
            source.get("identifiant"),
            source.get("titre"),
            source.get("extrait", "")[:300]
        )

        cle_txt = str(cle).lower()

        if cle_txt not in vus:
            vus.add(cle_txt)
            resultats.append(source)

    return resultats


@app.get("/")
def accueil():
    return {
        "status": "API active",
        "version": "4.0.0",
        "environnement": PISTE_ENV,
        "message": "API juridique copropriété opérationnelle."
    }


@app.post("/pack-juridique")
def post_pack_juridique(request: PackJuridiqueRequest):
    token = get_token()

    requetes = construire_requetes(
        query=request.query,
        type_operation=request.type_operation
    )

    legifrance = rechercher_legifrance_par_categories(
        token=token,
        requetes=requetes
    )

    jurisprudence = rechercher_judilibre(
        requetes=requetes
    )

    for categorie in legifrance:
        legifrance[categorie] = dedupliquer_sources(legifrance[categorie])

    jurisprudence = dedupliquer_sources(jurisprudence)

    return {
        "question": request.query,
        "type_dossier": request.type_dossier,
        "type_operation": request.type_operation,
        "environnement_piste": PISTE_ENV,
        "requetes_effectuees": requetes,

        "textes_loi_1965": legifrance["textes_loi_1965"],
        "decrets_reglements": legifrance["decrets_reglements"],
        "reformes_copropriete": legifrance["reformes_copropriete"],
        "codes": legifrance["codes"],
        "sources_thematiques": legifrance["thematiques"],
        "jurisprudence": jurisprudence,

        "points_vigilance": [
            "Vérifier la conformité à la loi n°65-557 du 10 juillet 1965.",
            "Vérifier la conformité au décret n°67-223 du 17 mars 1967.",
            "Vérifier les impacts des réformes SRU, ALUR, ELAN, ordonnance 2019 et décret 2020.",
            "Vérifier les parties communes spéciales au regard des articles 6-2 et 6-4.",
            "Vérifier les jouissances privatives au regard des articles 6-3 et 6-4.",
            "Vérifier les charges et tantièmes au regard des articles 5 et 10.",
            "Vérifier la concordance entre règlement, EDD, tableaux et plans.",
            "Ne jamais appliquer une règle sans confrontation avec le dossier transmis."
        ],

        "consigne_pour_agent": (
            "Utiliser les sources comme appui juridique. "
            "Distinguer textes applicables, réformes, codes, décrets et jurisprudence. "
            "Ne pas recopier intégralement les sources. "
            "Confronter chaque règle avec le contenu réel du dossier."
        )
    }


@app.get("/pack-juridique")
def get_pack_juridique(
    query: str,
    type_dossier: str = "copropriete",
    type_operation: str = "non précisé"
):
    request = PackJuridiqueRequest(
        query=query,
        type_dossier=type_dossier,
        type_operation=type_operation
    )

    return post_pack_juridique(request)
