# ECS geo field normalization for client/server geo attributes.
# Decomposes client_geo_name (e.g. "City, State, Country") into ECS geo subfields.

_PREFIXES = ('client_geo_', 'server_geo_', 'source_geo_', 'destination_geo_')

GEO_ISO2 = {
    'afghanistan': 'AF', 'albania': 'AL', 'algeria': 'DZ', 'andorra': 'AD',
    'angola': 'AO', 'argentina': 'AR', 'armenia': 'AM', 'australia': 'AU',
    'austria': 'AT', 'azerbaijan': 'AZ', 'bahrain': 'BH', 'bangladesh': 'BD',
    'belarus': 'BY', 'belgium': 'BE', 'belize': 'BZ', 'benin': 'BJ',
    'bhutan': 'BT', 'bolivia': 'BO', 'bosnia': 'BA', 'botswana': 'BW',
    'brazil': 'BR', 'brunei': 'BN', 'bulgaria': 'BG', 'cambodia': 'KH',
    'cameroon': 'CM', 'canada': 'CA', 'chile': 'CL', 'china': 'CN',
    'colombia': 'CO', 'congo': 'CG', 'costa rica': 'CR', 'croatia': 'HR',
    'cuba': 'CU', 'cyprus': 'CY', 'czechia': 'CZ', 'czech republic': 'CZ',
    'denmark': 'DK', 'ecuador': 'EC', 'egypt': 'EG', 'el salvador': 'SV',
    'estonia': 'EE', 'ethiopia': 'ET', 'finland': 'FI', 'france': 'FR',
    'georgia': 'GE', 'germany': 'DE', 'ghana': 'GH', 'greece': 'GR',
    'guatemala': 'GT', 'haiti': 'HT', 'honduras': 'HN', 'hungary': 'HU',
    'iceland': 'IS', 'india': 'IN', 'indonesia': 'ID', 'iran': 'IR',
    'iraq': 'IQ', 'ireland': 'IE', 'israel': 'IL', 'italy': 'IT',
    'jamaica': 'JM', 'japan': 'JP', 'jordan': 'JO', 'kazakhstan': 'KZ',
    'kenya': 'KE', 'kuwait': 'KW', 'kyrgyzstan': 'KG', 'laos': 'LA',
    'latvia': 'LV', 'lebanon': 'LB', 'libya': 'LY', 'liechtenstein': 'LI',
    'lithuania': 'LT', 'luxembourg': 'LU', 'malaysia': 'MY', 'maldives': 'MV',
    'mali': 'ML', 'malta': 'MT', 'mexico': 'MX', 'moldova': 'MD',
    'monaco': 'MC', 'mongolia': 'MN', 'montenegro': 'ME', 'morocco': 'MA',
    'mozambique': 'MZ', 'myanmar': 'MM', 'namibia': 'NA', 'nepal': 'NP',
    'netherlands': 'NL', 'new zealand': 'NZ', 'nicaragua': 'NI', 'nigeria': 'NG',
    'north korea': 'KP', 'north macedonia': 'MK', 'norway': 'NO', 'oman': 'OM',
    'pakistan': 'PK', 'panama': 'PA', 'paraguay': 'PY', 'peru': 'PE',
    'philippines': 'PH', 'poland': 'PL', 'portugal': 'PT', 'qatar': 'QA',
    'romania': 'RO', 'russia': 'RU', 'rwanda': 'RW', 'saudi arabia': 'SA',
    'senegal': 'SN', 'serbia': 'RS', 'singapore': 'SG', 'slovakia': 'SK',
    'slovenia': 'SI', 'somalia': 'SO', 'south africa': 'ZA', 'south korea': 'KR',
    'spain': 'ES', 'sri lanka': 'LK', 'sudan': 'SD', 'sweden': 'SE',
    'switzerland': 'CH', 'syria': 'SY', 'taiwan': 'TW', 'tajikistan': 'TJ',
    'tanzania': 'TZ', 'thailand': 'TH', 'tunisia': 'TN', 'turkey': 'TR',
    'turkmenistan': 'TM', 'uganda': 'UG', 'ukraine': 'UA',
    'united arab emirates': 'AE', 'uae': 'AE',
    'united kingdom': 'GB', 'uk': 'GB', 'great britain': 'GB',
    'united states': 'US', 'usa': 'US', 'united states of america': 'US',
    'uruguay': 'UY', 'uzbekistan': 'UZ', 'venezuela': 'VE', 'vietnam': 'VN',
    'yemen': 'YE', 'zambia': 'ZM', 'zimbabwe': 'ZW',
}

GEO_CONTINENT_BY_ISO2 = {
    'AF': 'AS', 'AL': 'EU', 'DZ': 'AF', 'AD': 'EU', 'AO': 'AF', 'AR': 'SA',
    'AM': 'AS', 'AU': 'OC', 'AT': 'EU', 'AZ': 'AS', 'BH': 'AS', 'BD': 'AS',
    'BY': 'EU', 'BE': 'EU', 'BZ': 'NA', 'BJ': 'AF', 'BT': 'AS', 'BO': 'SA',
    'BA': 'EU', 'BW': 'AF', 'BR': 'SA', 'BN': 'AS', 'BG': 'EU', 'KH': 'AS',
    'CM': 'AF', 'CA': 'NA', 'CL': 'SA', 'CN': 'AS', 'CO': 'SA', 'CG': 'AF',
    'CR': 'NA', 'HR': 'EU', 'CU': 'NA', 'CY': 'AS', 'CZ': 'EU', 'DK': 'EU',
    'EC': 'SA', 'EG': 'AF', 'SV': 'NA', 'EE': 'EU', 'ET': 'AF', 'FI': 'EU',
    'FR': 'EU', 'GE': 'AS', 'DE': 'EU', 'GH': 'AF', 'GR': 'EU', 'GT': 'NA',
    'HT': 'NA', 'HN': 'NA', 'HU': 'EU', 'IS': 'EU', 'IN': 'AS', 'ID': 'AS',
    'IR': 'AS', 'IQ': 'AS', 'IE': 'EU', 'IL': 'AS', 'IT': 'EU', 'JM': 'NA',
    'JP': 'AS', 'JO': 'AS', 'KZ': 'AS', 'KE': 'AF', 'KW': 'AS', 'KG': 'AS',
    'LA': 'AS', 'LV': 'EU', 'LB': 'AS', 'LY': 'AF', 'LI': 'EU', 'LT': 'EU',
    'LU': 'EU', 'MY': 'AS', 'MV': 'AS', 'ML': 'AF', 'MT': 'EU', 'MX': 'NA',
    'MD': 'EU', 'MC': 'EU', 'MN': 'AS', 'ME': 'EU', 'MA': 'AF', 'MZ': 'AF',
    'MM': 'AS', 'NA': 'AF', 'NP': 'AS', 'NL': 'EU', 'NZ': 'OC', 'NI': 'NA',
    'NG': 'AF', 'KP': 'AS', 'MK': 'EU', 'NO': 'EU', 'OM': 'AS', 'PK': 'AS',
    'PA': 'NA', 'PY': 'SA', 'PE': 'SA', 'PH': 'AS', 'PL': 'EU', 'PT': 'EU',
    'QA': 'AS', 'RO': 'EU', 'RU': 'EU', 'RW': 'AF', 'SA': 'AS', 'SN': 'AF',
    'RS': 'EU', 'SG': 'AS', 'SK': 'EU', 'SI': 'EU', 'SO': 'AF', 'ZA': 'AF',
    'KR': 'AS', 'ES': 'EU', 'LK': 'AS', 'SD': 'AF', 'SE': 'EU', 'CH': 'EU',
    'SY': 'AS', 'TW': 'AS', 'TJ': 'AS', 'TZ': 'AF', 'TH': 'AS', 'TN': 'AF',
    'TR': 'AS', 'TM': 'AS', 'UG': 'AF', 'UA': 'EU', 'AE': 'AS', 'GB': 'EU',
    'US': 'NA', 'UY': 'SA', 'UZ': 'AS', 'VE': 'SA', 'VN': 'AS', 'YE': 'AS',
    'ZM': 'AF', 'ZW': 'AF',
}

GEO_CONTINENT_NAMES = {
    'AF': 'Africa', 'AN': 'Antarctica', 'AS': 'Asia', 'EU': 'Europe',
    'NA': 'North America', 'OC': 'Oceania', 'SA': 'South America',
}





def _set_if_missing(fields: dict, key: str, value):
    if value and not fields.get(key):
        fields[key] = value


def _country_iso2(name: str) -> str:
    if not name:
        return ''
    name_l = name.strip().lower()
    if len(name_l) == 2:
        return name_l.upper()
    return GEO_ISO2.get(name_l, '')


def _decompose_geo_name(geo_name: str, prefix: str, fields: dict):
    parts = [p.strip() for p in geo_name.split(',') if p.strip()]
    if len(parts) == 3:
        _set_if_missing(fields, f'{prefix}city_name', parts[0])
        _set_if_missing(fields, f'{prefix}region_name', parts[1])
        _set_if_missing(fields, f'{prefix}country_name', parts[2])
    elif len(parts) == 2:
        _set_if_missing(fields, f'{prefix}city_name', parts[0])
        _set_if_missing(fields, f'{prefix}country_name', parts[1])
    elif len(parts) == 1:
        pass


def _enrich_country(prefix: str, fields: dict):
    country_name = fields.get(f'{prefix}country_name', '')
    iso2 = fields.get(f'{prefix}country_iso_code', '') or _country_iso2(country_name)
    if iso2:
        _set_if_missing(fields, f'{prefix}country_iso_code', iso2)
        continent_code = GEO_CONTINENT_BY_ISO2.get(iso2.upper(), '')
        if continent_code:
            _set_if_missing(fields, f'{prefix}continent_code', continent_code)
            _set_if_missing(fields, f'{prefix}continent_name', GEO_CONTINENT_NAMES.get(continent_code, ''))


def normalize_geo_fields(fields: dict) -> dict:
    for prefix in _PREFIXES:
        geo_name = fields.get(f'{prefix}name', '')
        if geo_name and isinstance(geo_name, str):
            _decompose_geo_name(geo_name, prefix, fields)
        _enrich_country(prefix, fields)
    return fields
