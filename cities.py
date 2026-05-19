"""
Registry of Turkish municipalities for the e-license platform.
Each city has issuer metadata, license ID prefix, and districts (where applicable).
"""
from __future__ import annotations

# District lists for metropolitan municipalities
METRO_DISTRICTS: dict[str, list[str]] = {
    "istanbul": [
        "Adalar", "Arnavutköy", "Ataşehir", "Avcılar", "Bağcılar", "Bahçelievler",
        "Bakırköy", "Başakşehir", "Bayrampaşa", "Beşiktaş", "Beykoz", "Beylikdüzü",
        "Beyoğlu", "Büyükçekmece", "Çatalca", "Çekmeköy", "Esenler", "Esenyurt",
        "Eyüpsultan", "Fatih", "Gaziosmanpaşa", "Güngören", "Kadıköy", "Kağıthane",
        "Kartal", "Küçükçekmece", "Maltepe", "Pendik", "Sancaktepe", "Sarıyer",
        "Silivri", "Sultanbeyli", "Sultangazi", "Şile", "Şişli", "Tuzla",
        "Ümraniye", "Üsküdar", "Zeytinburnu",
    ],
    "ankara": [
        "Altındağ", "Ayaş", "Bala", "Beypazarı", "Çamlıdere", "Çankaya", "Çubuk",
        "Elmadağ", "Etimesgut", "Evren", "Gölbaşı", "Güdül", "Haymana", "Kahramankazan",
        "Kalecik", "Keçiören", "Kızılcahamam", "Mamak", "Nallıhan", "Polatlı",
        "Pursaklar", "Sincan", "Şereflikoçhisar", "Yenimahalle", "Akyurt",
    ],
    "izmir": [
        "Aliağa", "Balçova", "Bayındır", "Bayraklı", "Bergama", "Beydağ", "Bornova",
        "Buca", "Çeşme", "Çiğli", "Dikili", "Foça", "Gaziemir", "Güzelbahçe",
        "Karabağlar", "Karaburun", "Karşıyaka", "Kemalpaşa", "Kınık", "Kiraz",
        "Konak", "Menderes", "Menemen", "Narlıdere", "Ödemiş", "Seferihisar",
        "Selçuk", "Tire", "Torbalı", "Urla",
    ],
    "bursa": [
        "Osmangazi", "Yıldırım", "Nilüfer", "Gemlik", "İnegöl", "Mudanya",
        "Mustafakemalpaşa", "Gürsu", "Kestel", "Karacabey", "Orhangazi", "İznik",
    ],
    "antalya": [
        "Muratpaşa", "Kepez", "Konyaaltı", "Aksu", "Döşemealtı", "Alanya", "Manavgat",
        "Serik", "Kumluca", "Kaş", "Kemer", "Finike", "Demre", "Elmalı",
    ],
    "adana": ["Seyhan", "Yüreğir", "Çukurova", "Sarıçam", "Ceyhan", "Kozan", "İmamoğlu"],
    "konya": ["Selçuklu", "Meram", "Karatay", "Ereğli", "Akşehir", "Beyşehir", "Cihanbeyli"],
    "gaziantep": ["Şahinbey", "Şehitkamil", "Oğuzeli", "Nizip", "İslahiye", "Nurdağı"],
    "kocaeli": ["İzmit", "Gebze", "Darıca", "Körfez", "Gölcük", "Kartepe", "Derince", "Çayırova"],
    "mersin": ["Akdeniz", "Yenişehir", "Toroslar", "Mezitli", "Tarsus", "Erdemli", "Silifke"],
    "diyarbakir": ["Bağlar", "Kayapınar", "Sur", "Yenişehir", "Bismil", "Ergani"],
    "hatay": ["Antakya", "Defne", "İskenderun", "Dörtyol", "Samandağ", "Reyhanlı"],
    "manisa": ["Yunusemre", "Şehzadeler", "Akhisar", "Salihli", "Turgutlu", "Soma"],
    "kayseri": ["Melikgazi", "Kocasinan", "Talas", "Develi", "Yahyalı", "Bünyan"],
    "samsun": ["Atakum", "İlkadım", "Canik", "Tekkeköy", "Bafra", "Çarşamba"],
    "balikesir": ["Altıeylül", "Karesi", "Bandırma", "Edremit", "Gönen", "Ayvalık"],
    "kahramanmaras": ["Onikişubat", "Dulkadiroğlu", "Elbistan", "Afşin", "Türkoğlu"],
    "van": ["İpekyolu", "Tuşba", "Edremit", "Erciş", "Özalp"],
    "denizli": ["Pamukkale", "Merkezefendi", "Çivril", "Acıpayam", "Tavas"],
    "sanliurfa": ["Eyyübiye", "Haliliye", "Karaköprü", "Siverek", "Viranşehir"],
    "trabzon": ["Ortahisar", "Akçaabat", "Yomra", "Araklı", "Of"],
    "eskisehir": ["Tepebaşı", "Odunpazarı", "Sivrihisar", "Çifteler"],
    "malatya": ["Battalgazi", "Yeşilyurt", "Darende", "Akçadağ"],
    "erzurum": ["Yakutiye", "Palandöken", "Aziziye", "Horasan", "Oltu"],
    "sakarya": ["Adapazarı", "Serdivan", "Erenler", "Hendek", "Akyazı"],
    "mugla": ["Menteşe", "Bodrum", "Fethiye", "Marmaris", "Milas", "Dalaman"],
    "tekirdag": ["Süleymanpaşa", "Çorlu", "Çerkezköy", "Kapaklı", "Ergene"],
    "aydin": ["Efeler", "Nazilli", "Söke", "Kuşadası", "Didim"],
    "ordu": ["Altınordu", "Ünye", "Fatsa", "Perşembe"],
    "afyonkarahisar": ["Merkez", "Sandıklı", "Dinar", "Bolvadin"],
}

# slug, display name, plate code, license prefix, is metropolitan
PROVINCES: list[tuple[str, str, str, str, bool]] = [
    ("adana", "Adana", "01", "ADA", True),
    ("adiyaman", "Adıyaman", "02", "ADI", False),
    ("afyonkarahisar", "Afyonkarahisar", "03", "AFY", False),
    ("agri", "Ağrı", "04", "AGR", False),
    ("amasya", "Amasya", "05", "AMS", False),
    ("ankara", "Ankara", "06", "ANK", True),
    ("antalya", "Antalya", "07", "ANT", True),
    ("artvin", "Artvin", "08", "ART", False),
    ("aydin", "Aydın", "09", "AYD", False),
    ("balikesir", "Balıkesir", "10", "BAL", False),
    ("bilecik", "Bilecik", "11", "BIL", False),
    ("bingol", "Bingöl", "12", "BIN", False),
    ("bitlis", "Bitlis", "13", "BIT", False),
    ("bolu", "Bolu", "14", "BOL", False),
    ("burdur", "Burdur", "15", "BUR", False),
    ("bursa", "Bursa", "16", "BRS", True),
    ("canakkale", "Çanakkale", "17", "CKL", False),
    ("cankiri", "Çankırı", "18", "CKR", False),
    ("corum", "Çorum", "19", "COR", False),
    ("denizli", "Denizli", "20", "DEN", False),
    ("diyarbakir", "Diyarbakır", "21", "DIY", True),
    ("edirne", "Edirne", "22", "EDI", False),
    ("elazig", "Elazığ", "23", "ELA", False),
    ("erzincan", "Erzincan", "24", "ERZ", False),
    ("erzurum", "Erzurum", "25", "ERU", False),
    ("eskisehir", "Eskişehir", "26", "ESK", False),
    ("gaziantep", "Gaziantep", "27", "GAZ", True),
    ("giresun", "Giresun", "28", "GIR", False),
    ("gumushane", "Gümüşhane", "29", "GUM", False),
    ("hakkari", "Hakkari", "30", "HAK", False),
    ("hatay", "Hatay", "31", "HAT", True),
    ("isparta", "Isparta", "32", "ISP", False),
    ("mersin", "Mersin", "33", "MER", True),
    ("istanbul", "İstanbul", "34", "IST", True),
    ("izmir", "İzmir", "35", "IZM", True),
    ("kars", "Kars", "36", "KAR", False),
    ("kastamonu", "Kastamonu", "37", "KAS", False),
    ("kayseri", "Kayseri", "38", "KAY", False),
    ("kirklareli", "Kırklareli", "39", "KIR", False),
    ("kirsehir", "Kırşehir", "40", "KRH", False),
    ("kocaeli", "Kocaeli", "41", "KOC", True),
    ("konya", "Konya", "42", "KON", True),
    ("kutahya", "Kütahya", "43", "KUT", False),
    ("malatya", "Malatya", "44", "MAL", False),
    ("manisa", "Manisa", "45", "MAN", False),
    ("kahramanmaras", "Kahramanmaraş", "46", "KMR", False),
    ("mardin", "Mardin", "47", "MAR", False),
    ("mugla", "Muğla", "48", "MUG", False),
    ("mus", "Muş", "49", "MUS", False),
    ("nevsehir", "Nevşehir", "50", "NEV", False),
    ("nigde", "Niğde", "51", "NIG", False),
    ("ordu", "Ordu", "52", "ORD", False),
    ("rize", "Rize", "53", "RIZ", False),
    ("sakarya", "Sakarya", "54", "SAK", False),
    ("samsun", "Samsun", "55", "SAM", False),
    ("siirt", "Siirt", "56", "SII", False),
    ("sinop", "Sinop", "57", "SIN", False),
    ("sivas", "Sivas", "58", "SIV", False),
    ("tekirdag", "Tekirdağ", "59", "TEK", False),
    ("tokat", "Tokat", "60", "TOK", False),
    ("trabzon", "Trabzon", "61", "TRA", False),
    ("tunceli", "Tunceli", "62", "TUN", False),
    ("sanliurfa", "Şanlıurfa", "63", "URF", True),
    ("usak", "Uşak", "64", "USA", False),
    ("van", "Van", "65", "VAN", False),
    ("yozgat", "Yozgat", "66", "YOZ", False),
    ("zonguldak", "Zonguldak", "67", "ZON", False),
    ("aksaray", "Aksaray", "68", "AKS", False),
    ("bayburt", "Bayburt", "69", "BAY", False),
    ("karaman", "Karaman", "70", "KRM", False),
    ("kirikkale", "Kırıkkale", "71", "KRK", False),
    ("batman", "Batman", "72", "BAT", False),
    ("sirnak", "Şırnak", "73", "SIR", False),
    ("bartin", "Bartın", "74", "BAR", False),
    ("ardahan", "Ardahan", "75", "ARD", False),
    ("igdir", "Iğdır", "76", "IGD", False),
    ("yalova", "Yalova", "77", "YAL", False),
    ("karabuk", "Karabük", "78", "KRB", False),
    ("kilis", "Kilis", "79", "KLS", False),
    ("osmaniye", "Osmaniye", "80", "OSM", False),
    ("duzce", "Düzce", "81", "DUZ", False),
]


def _build_city(slug: str, name: str, plate: str, prefix: str, metropolitan: bool) -> dict:
    districts = METRO_DISTRICTS.get(slug, [f"{name} Center"])
    issuer_label = (
        f"{name} Metropolitan Municipality"
        if metropolitan
        else f"{name} Municipality"
    )
    seed_base = f"{slug}_municipality_license_seed"
    issuer_seed = (seed_base + "0" * 32)[:32]

    return {
        "slug": slug,
        "name": name,
        "plate_code": plate,
        "license_prefix": prefix,
        "metropolitan": metropolitan,
        "districts": districts,
        "issuer_name": issuer_label,
        "issuer_did": f"did:indy:tr:{slug}:municipality",
        "issuer_seed": issuer_seed,
        "credential_context": f"https://{slug}.bel.tr/credentials/v1",
        "pool_name": f"{slug}_pool",
        "license_id_example": f"2024-{prefix}-001",
    }


CITIES: dict[str, dict] = {
    slug: _build_city(slug, name, plate, prefix, metro)
    for slug, name, plate, prefix, metro in PROVINCES
}

DEFAULT_CITY_SLUG = "konya"


def get_city(slug: str) -> dict:
    """Return full configuration for a municipality slug."""
    key = (slug or DEFAULT_CITY_SLUG).lower().strip()
    if key not in CITIES:
        raise ValueError(f"Unknown city: {slug}. Use one of: {', '.join(sorted(CITIES))}")
    return CITIES[key].copy()


def list_city_summaries() -> list[dict]:
    """Lightweight list for API and UI selectors."""
    return [
        {
            "slug": city["slug"],
            "name": city["name"],
            "license_prefix": city["license_prefix"],
            "plate_code": city["plate_code"],
            "metropolitan": city["metropolitan"],
            "districts": city["districts"],
            "license_id_example": city["license_id_example"],
        }
        for city in sorted(CITIES.values(), key=lambda item: item["name"])
    ]


def all_issuer_dids() -> list[str]:
    return [city["issuer_did"] for city in CITIES.values()]
