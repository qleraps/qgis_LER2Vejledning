# -*- coding: utf-8 -*-
"""User-interface texts in English and Danish.

The language follows QGIS' own language setting (Settings > Options >
General): Danish if QGIS runs in Danish, otherwise English. QGIS only changes
language on restart, so it is decided once, the first time a text is needed.
Texts are looked up by key; a key missing in Danish falls back to English.

Note: the data model itself (object type and attribute names, definitions,
conditions, code lists) is published in Danish by valideringsportalen.dk and
is shown as received - only the plugin's own interface is translated.
"""

_language = None


def _detect_language():
    try:
        from qgis.core import QgsSettings
        from qgis.PyQt.QtCore import QLocale

        settings = QgsSettings()
        if settings.value("locale/overrideFlag", False, type=bool):
            locale = str(settings.value("locale/userLocale", "") or "")
        else:
            locale = QLocale.system().name()
    except Exception:
        locale = ""
    return "da" if locale.lower().startswith("da") else "en"


def language():
    global _language
    if _language is None:
        _language = _detect_language()
    return _language


def set_language(lang):
    global _language
    _language = lang


def tr(key, *args):
    text = STRINGS.get(language(), {}).get(key)
    if text is None:
        text = STRINGS["en"].get(key, key)
    return text % args if args else text


STRINGS = {
    "en": {
        "howto": (
            "<b>How to use the guide</b><br>"
            "<b>Attributes:</b> pick an object type (selected automatically if the active layer "
            "has the same name) and see what is mandatory, conditional and optional. "
            "Search to find an attribute across all object types.<br>"
            "<b>Code lists:</b> find the allowed values for fields that use a code list, and "
            "copy them with a double-click."
        ),
        "disclaimer": (
            "The guide is advisory and is used without liability. It gives no guarantee "
            "that LER will accept the data you deliver."
        ),
        "z_note": (
            "<b>Note on z (source: LER's own error message):</b> A vertical coordinate (z) in the "
            "geometry must not have the unknown value -99 if the cable or pipe is buried or "
            "installed after the cut-off date."
        ),
        "z_note_exception": (
            "<br><b>Electricity and telecommunication lines</b> may instead state the indicative "
            "depth (<i>vejledendeDybde</i>) rather than z in the geometry."
        ),
        "z_note_unrelated": (
            "<br>Z in the geometry and <i>noejagtighedsklasseVertikal</i> are not linked to each other."
        ),
        "z_help_title": "How to check z in QGIS",
        "z_help": (
            "1. Does the layer have z at all?\n"
            "   Right-click the layer > Properties > Information. Under 'Geometry' the type must "
            "end in Z, e.g. LineStringZ. If Z is missing, the layer's points have no z value.\n"
            "\n"
            "2. See z for a single feature\n"
            "   Select the feature, switch on the Vertex Tool and right-click the feature: "
            "the Vertex Editor shows x, y and z for each point.\n"
            "\n"
            "3. Find features where z is -99 or missing\n"
            "   Open the attribute table > 'Select features using an expression' and use:\n"
            "   array_contains(array_foreach(generate_series(1, num_points($geometry)), "
            "z(point_n($geometry, @element))), -99)\n"
            "   If you only want to check the first point of each feature, you can use:\n"
            "   z(start_point($geometry)) = -99 OR z(start_point($geometry)) IS NULL\n"
            "\n"
            "4. Remember the exception\n"
            "   Electricity and telecommunication lines may state the indicative depth "
            "instead of z in the geometry.\n"
            "\n"
            "The expressions are suggestions - try them on a layer you know before you rely on them."
        ),
        "tab_attributes": "Attributes",
        "tab_codelists": "Code lists",
        "open_web": "Open the guide on the web",
        "object_type_label": "Object type:",
        "match_layer": "Match active layer",
        "match_layer_tip": "Select the object type that fits the active layer",
        "auto_match": "Match active layer automatically",
        "auto_match_tip": "When enabled, the object type changes by itself when you select another layer in the Layers panel.",
        "z_info_tip": "How to check z in QGIS",
        "search_attributes_placeholder": "Search attributes (across all object types)...",
        "col_object_type": "Object type",
        "col_attribute": "Attribute",
        "col_requirement": "Requirement",
        "col_layer_field": "Field in your layer",
        "col_value": "Value",
        "col_value_free": "Value (free value allowed)",
        "col_description": "Description",
        "col_code_list": "Code list",
        "copy_value": "Copy selected value",
        "copy_value_tip": "Double-clicking a row does the same",
        "code_list_label": "Code list:",
        "search_values_placeholder": "Search values...",
        "select_type": "(select object type)",
        "all_lists": "(all code lists)",
        "status_cache": "Data model from local cache - checking for updates...",
        "status_fetching": "Fetching data model from valideringsportalen.dk...",
        "status_updated": "Data model updated from valideringsportalen.dk",
        "status_fetch_failed": "Could not fetch the data model: %s",
        "status_offline": "Offline - using the saved data model (%s)",
        "status_no_type_match": "The layer name matches no object type - select it manually.",
        "layer_none": "No active vector layer.",
        "layer_pick_type": "Layer: %s - select an object type to compare.",
        "layer_summary": "Layer: %s against %s - missing %d mandatory attribute(s)",
        "layer_extra": "; %d field(s) not in the model",
        "tip_missing": "Missing (mandatory): ",
        "tip_not_in_model": "Not in the model: ",
        "occ_mandatory": "Mandatory",
        "occ_conditional": "Conditional",
        "occ_optional": "Optional",
        "occ_conditional_tip": "Only required under certain conditions - see the details below",
        "compare_yes": "Yes",
        "compare_missing": "Missing",
        "compare_conditional_tip": "Conditional: only a problem if the condition is met",
        "no_results": "No results",
        "pick_or_search": "Select an object type or search",
        "detail_definition": "Definition: %s",
        "detail_object_type": "Object type: %s",
        "detail_occurrence": "Occurrence: %s",
        "detail_condition": "Condition:\n%s",
        "detail_multiplicity": "Multiplicity: %s    Voidable: %s",
        "detail_defined_on": "Defined on: %s",
        "detail_datatype": "Datatype: %s",
        "detail_code_list": "Code list: %s",
        "yes": "Yes",
        "no": "No",
        "list_note_free": "The list also allows a free value, e.g.: andet: your text",
        "list_note_closed": "Only values from the list are allowed.",
        "list_note_pick": "Select a code list, or search all code lists at once.",
        "copied": "Copied: %s",
        "err_too_large": "The response is too large",
        "err_unexpected_format": "Unexpected format",
        "err_invalid_type": "Invalid object type: %s",
        "err_invalid_list": "Invalid code list: %s",
        "err_invalid_response": "Invalid response from the server: %s",
    },
    "da": {
        "howto": (
            "<b>Sådan bruger du vejledningen</b><br>"
            "<b>Attributter:</b> vælg en objekttype (vælges automatisk, hvis det aktive lag "
            "hedder det samme) og se, hvad der er obligatorisk, betinget og frivilligt. "
            "Søg for at finde en attribut på tværs af alle objekttyper.<br>"
            "<b>Kodelister:</b> find de tilladte værdier til felter med en kodeliste, og "
            "kopiér dem med et dobbeltklik."
        ),
        "disclaimer": (
            "Vejledningen er vejledende og bruges uden ansvar. Den giver ingen garanti "
            "for, at LER accepterer de data, du afleverer."
        ),
        "z_note": (
            "<b>Note om z (kilde: LER's egen fejlmeddelelse):</b> En vertikal koordinat (z) i "
            "geometrien må ikke have ukendt-værdien -99, hvis ledningen er nedgravet eller "
            "anbragt efter skæringsdatoen."
        ),
        "z_note_exception": (
            "<br><b>El- og telekommunikationsledninger</b> må i stedet angive vejledende dybde "
            "(<i>vejledendeDybde</i>) frem for z i geometrien."
        ),
        "z_note_unrelated": (
            "<br>Z i geometrien og <i>noejagtighedsklasseVertikal</i> er ikke knyttet til hinanden."
        ),
        "z_help_title": "Sådan tjekker du z i QGIS",
        "z_help": (
            "1. Har laget z overhovedet?\n"
            "   Højreklik på laget > Egenskaber > Information. Under 'Geometri' skal typen "
            "ende på Z, fx LineStringZ. Mangler Z, har lagets punkter ingen z-værdi.\n"
            "\n"
            "2. Se z for et enkelt objekt\n"
            "   Vælg objektet, slå Vertex-værktøjet til og højreklik på objektet: "
            "Vertex-editoren viser x, y og z for hvert punkt.\n"
            "\n"
            "3. Find objekter hvor z er -99 eller mangler\n"
            "   Åbn attributtabellen > 'Vælg objekter med udtryk' og brug:\n"
            "   array_contains(array_foreach(generate_series(1, num_points($geometry)), "
            "z(point_n($geometry, @element))), -99)\n"
            "   Vil du kun se på lagets første punkt, kan du bruge:\n"
            "   z(start_point($geometry)) = -99 OR z(start_point($geometry)) IS NULL\n"
            "\n"
            "4. Husk undtagelsen\n"
            "   El- og telekommunikationsledninger må angive vejledende dybde i stedet for "
            "z i geometrien.\n"
            "\n"
            "Udtrykkene er forslag - afprøv dem på et lag, du kender, før du stoler på dem."
        ),
        "tab_attributes": "Attributter",
        "tab_codelists": "Kodelister",
        "open_web": "Åbn vejledning på web",
        "object_type_label": "Objekttype:",
        "match_layer": "Match aktivt lag",
        "match_layer_tip": "Vælg den objekttype, der passer til det aktive lag",
        "auto_match": "Match aktivt lag automatisk",
        "auto_match_tip": "Slået til: objekttypen skifter selv, når du vælger et andet lag i Lag-panelet.",
        "z_info_tip": "Sådan tjekker du z i QGIS",
        "search_attributes_placeholder": "Søg i attributter (på tværs af alle objekttyper)...",
        "col_object_type": "Objekttype",
        "col_attribute": "Attribut",
        "col_requirement": "Krav",
        "col_layer_field": "Felt i dit lag",
        "col_value": "Værdi",
        "col_value_free": "Værdi (fri værdi tilladt)",
        "col_description": "Beskrivelse",
        "col_code_list": "Kodeliste",
        "copy_value": "Kopiér valgt værdi",
        "copy_value_tip": "Dobbeltklik på en række gør det samme",
        "code_list_label": "Kodeliste:",
        "search_values_placeholder": "Søg i værdier...",
        "select_type": "(vælg objekttype)",
        "all_lists": "(alle kodelister)",
        "status_cache": "Datamodel fra lokal cache - tjekker for opdatering...",
        "status_fetching": "Henter datamodel fra valideringsportalen.dk...",
        "status_updated": "Datamodel opdateret fra valideringsportalen.dk",
        "status_fetch_failed": "Kunne ikke hente datamodellen: %s",
        "status_offline": "Offline - bruger gemt datamodel (%s)",
        "status_no_type_match": "Lagets navn matcher ingen objekttype - vælg den manuelt.",
        "layer_none": "Intet aktivt vektorlag.",
        "layer_pick_type": "Lag: %s - vælg en objekttype for at sammenligne.",
        "layer_summary": "Lag: %s mod %s - mangler %d obligatorisk(e) attribut(ter)",
        "layer_extra": "; %d felt(er) findes ikke i modellen",
        "tip_missing": "Mangler (obligatoriske): ",
        "tip_not_in_model": "Ikke i modellen: ",
        "occ_mandatory": "Obligatorisk",
        "occ_conditional": "Betinget",
        "occ_optional": "Frivillig",
        "occ_conditional_tip": "Kun påkrævet under bestemte betingelser - se detaljerne nedenfor",
        "compare_yes": "Ja",
        "compare_missing": "Mangler",
        "compare_conditional_tip": "Betinget: kun et problem, hvis betingelsen er opfyldt",
        "no_results": "Ingen resultater",
        "pick_or_search": "Vælg en objekttype eller søg",
        "detail_definition": "Definition: %s",
        "detail_object_type": "Objekttype: %s",
        "detail_occurrence": "Forekomst: %s",
        "detail_condition": "Betingelse:\n%s",
        "detail_multiplicity": "Multiplicitet: %s    Voidable: %s",
        "detail_defined_on": "Defineret på: %s",
        "detail_datatype": "Datatype: %s",
        "detail_code_list": "Kodeliste: %s",
        "yes": "Ja",
        "no": "Nej",
        "list_note_free": "Listen tillader også en fri værdi, fx: andet: din tekst",
        "list_note_closed": "Kun værdier fra listen er tilladt.",
        "list_note_pick": "Vælg en kodeliste, eller søg i alle kodelister på én gang.",
        "copied": "Kopieret: %s",
        "err_too_large": "Svaret er for stort",
        "err_unexpected_format": "Uventet format",
        "err_invalid_type": "Ugyldig objekttype: %s",
        "err_invalid_list": "Ugyldig kodeliste: %s",
        "err_invalid_response": "Ugyldigt svar fra serveren: %s",
    },
}
