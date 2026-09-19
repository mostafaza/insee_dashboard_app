import os
from functools import lru_cache
from urllib import request
import xml.etree.ElementTree as ET

import pandas as pd


DEFAULT_INSEE_URL = "https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LR_PRINC"


@lru_cache(maxsize=8)
def fetch_insee_xml_cached(url, api_key=""):
    """Cached fetch of the XML payload, to avoid re-downloading on every rerun."""
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/xml, text/xml, */*",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        req = request.Request(url, headers=headers)
        with request.urlopen(req, timeout=30) as response:
            return response.read().decode("utf-8", errors="replace")
    except ValueError as exc:
        raise ValueError(f"URL Insee invalide : {url}") from exc
    except request.HTTPError as exc:
        raise RuntimeError(
            f"Erreur HTTP {exc.code} sur l'URL INSEE : {url}. Vérifie que l'URL est correcte et accessible."
        ) from exc
    except request.URLError as exc:
        raise ConnectionError(f"Impossible de joindre l'URL INSEE : {url}. Vérifie l'URL ou la connexion Internet.") from exc
    except Exception as exc:
        raise RuntimeError(f"Erreur lors du chargement des données INSEE : {exc}") from exc


def fetch_insee_xml(url=DEFAULT_INSEE_URL, api_key=None):
    """Fetch the XML payload from the Insee Melodi API."""
    return fetch_insee_xml_cached(url, api_key or "")


def get_dataset_metadata(xml_text):
    if not xml_text or not xml_text.strip():
        return {"identifier": "", "title": ""}

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError(
            "Le contenu récupéré n’est pas un XML INSEE valide. Vérifie que l’URL pointe vers un flux XML INSEE, par exemple https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LR_PRINC."
        ) from exc

    identifier = root.findtext("identifier", default="")
    title_fr = root.findtext("title/fr", default="")
    title_en = root.findtext("title/en", default="")
    title = title_fr or title_en or "Dataset"
    return {"identifier": identifier, "title": title}


@lru_cache(maxsize=8)
def parse_insee_xml_cached(xml_text):
    """Cached parsing of XML into a DataFrame, to avoid re-parsing the same payload over and over."""
    if not xml_text or not xml_text.strip():
        return pd.DataFrame()

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError(
            "Le contenu récupéré n’est pas un XML INSEE valide. Vérifie que l’URL pointe vers un flux XML INSEE, par exemple https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LR_PRINC."
        ) from exc

    rows = []

    for observation in root.findall(".//observations/observations"):
        dimensions = observation.find("dimensions")
        attributes = observation.find("attributes")
        measures = observation.find("measures")

        row = {}

        if dimensions is not None:
            for node in dimensions:
                row[node.tag] = (node.text or "").strip()

        if attributes is not None:
            for node in attributes:
                row[node.tag] = (node.text or "").strip()

        if measures is not None:
            for node in measures:
                value_text = ""
                if node is not None:
                    value_node = node.find("value")
                    if value_node is not None:
                        value_text = (value_node.text or "").strip()
                row[node.tag] = value_text

        if row:
            rows.append(row)

    if not rows:
        if root.tag.lower() in {"html", "body", "doctype"}:
            raise ValueError(
                "Le contenu récupéré n’est pas un XML INSEE valide. Vérifie que l’URL pointe vers un flux XML INSEE, par exemple https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LR_PRINC."
            )
        return pd.DataFrame()

    return pd.DataFrame(rows)


def parse_insee_xml(xml_text):
    """Parse the Insee XML payload into a tidy DataFrame."""
    return parse_insee_xml_cached(xml_text)


def build_dashboard(df):
    """Add simple computed columns and return filtered data for UI."""
    if df.empty:
        return df

    numeric_columns = infer_measure_columns(df.columns)
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    return df


def infer_measure_columns(columns):
    """Infer the actual observation value columns while keeping genuine INSEE
    measure fields such as OBS_VALUE_NIVEAU and OBS_STATUS available for
    filtering and charting.
    """
    excluded = {
        "unit_measure",
        "freq",
        "time_period",
        "date",
        "year",
        "geo",
        "region",
        "sex",
        "sexe",
        "age",
        "status",
        "decimals",
        "conf_status",
        "indicator_type",
        "ind_type",
        "idx_type",
        "base_per",
        "seasonal_adjust",
        "tsh",
        "tph",
        "product_group",
        "pcs",
        "quantile_nivvie",
    }

    candidates = []
    for col in columns:
        lower = col.lower()
        if lower in excluded:
            continue
        if "value" in lower or "niveau" in lower or "indice" in lower or lower.endswith("_prix"):
            candidates.append(col)

    if candidates:
        return candidates

    numeric_candidates = []
    for col in columns:
        lower = col.lower()
        if lower in excluded:
            continue
        if lower.startswith("obs_") or lower.endswith("_value") or lower.endswith("_niveau"):
            numeric_candidates.append(col)

    return numeric_candidates


def get_filter_options(df):
    """Return all user-relevant columns from the dataset.

    For INSEE XML payloads, the full schema is often the business content itself
    (for example OBS_STATUS or OBS_VALUE_NIVEAU). We therefore keep all columns
    that are not empty or known to be purely technical metadata.
    """
    excluded = {"STATUS", "DECIMALS", "CONF_STATUS"}
    options = []

    for col in df.columns:
        if col in excluded:
            continue
        if df[col].isna().all():
            continue
        options.append(col)

    return options


def get_chart_axis(df):
    """Choose a sensible X-axis for the chart, defaulting to TIME_PERIOD when available."""
    if "TIME_PERIOD" in df.columns:
        return "TIME_PERIOD"

    for col in df.columns:
        if col in infer_measure_columns(df.columns):
            continue
        if col.lower() == "status":
            continue
        return col

    return df.columns[0] if len(df.columns) else None


def get_chart_candidates(df, x_axis=None, y_axis=None):
    """Return valid X/Y chart options from the same dataset schema, with X and Y kept distinct."""
    if df.empty:
        return [], []

    excluded = {"STATUS", "DECIMALS", "CONF_STATUS"}

    x_candidates = [col for col in df.columns if col not in excluded and col != y_axis]
    if not x_candidates:
        x_candidates = [col for col in df.columns if col != y_axis]

    if x_axis is not None and x_axis not in x_candidates:
        x_candidates = [x_axis] + x_candidates

    y_candidates = [col for col in x_candidates if col != x_axis]
    if y_axis is not None and y_axis not in y_candidates:
        y_candidates = [y_axis] + y_candidates

    return x_candidates, y_candidates


def prepare_export_dataframe(df, selected_filters=None):
    """Apply the current filter selection to a DataFrame, or return the original table."""
    export_df = df.copy()
    if not selected_filters:
        return export_df

    for column, selected_value in selected_filters.items():
        if selected_value != "Tous":
            export_df = export_df[export_df[column].astype(str) == str(selected_value)]
    return export_df


def main():
    import streamlit as st

    st.set_page_config(layout="wide")
    st.title("Dashboard INSEE - DS_RP_EMPLOI_LR_PRINC")

    if "df" not in st.session_state:
        st.session_state["df"] = pd.DataFrame()
    if "metadata" not in st.session_state:
        st.session_state["metadata"] = {"identifier": "", "title": ""}
    if "insee_url" not in st.session_state:
        st.session_state["insee_url"] = DEFAULT_INSEE_URL
    if "last_loaded_url" not in st.session_state:
        st.session_state["last_loaded_url"] = None

    url = st.text_input("URL XML INSEE", key="insee_url")
    if not url.strip():
        url = DEFAULT_INSEE_URL
        st.session_state["insee_url"] = url
    api_key = st.text_input("Clé API Insee (optionnelle)", type="password", key="insee_api_key")

    if "localhost" in url.lower() or "127.0.0.1" in url.lower():
        st.warning("Cette URL n’est pas un flux XML INSEE. Utilise un endpoint INSEE comme https://api.insee.fr/melodi/data/DS_RP_EMPLOI_LR_PRINC.")

    if st.button("Charger les données"):
        try:
            with st.spinner("Récupération des données XML..."):
                xml_text = fetch_insee_xml(url, api_key)
                metadata = get_dataset_metadata(xml_text)
                df = parse_insee_xml(xml_text)
                df = build_dashboard(df)
        except (ValueError, ConnectionError, RuntimeError) as exc:
            st.session_state["df"] = pd.DataFrame()
            st.session_state["metadata"] = {"identifier": "", "title": ""}
            st.error(str(exc))
            return

        if df.empty:
            st.session_state["df"] = pd.DataFrame()
            st.session_state["metadata"] = {"identifier": "", "title": ""}
            st.warning("Aucune donnée extraite du fichier XML. Vérifie l’URL ou le format des données.")
            return

        st.session_state["df"] = df
        st.session_state["metadata"] = metadata
        st.session_state["last_loaded_url"] = url
        st.session_state["chart_x"] = None
        st.session_state["chart_y"] = None

    if st.session_state.get("last_loaded_url") is not None and url != st.session_state["last_loaded_url"]:
        st.session_state["chart_x"] = None
        st.session_state["chart_y"] = None
        st.session_state["last_loaded_url"] = url

    df = st.session_state.get("df", pd.DataFrame())
    metadata = st.session_state.get("metadata", {"identifier": "", "title": ""})

    if df.empty:
        return

    st.subheader(metadata["title"])
    st.caption(f"Identifiant : {metadata['identifier']}")

    measure_columns = infer_measure_columns(df.columns)
    main_measure = measure_columns[0] if measure_columns else None

    col1, col2, col3 = st.columns(3)
    col1.metric("Lignes", len(df))
    col2.metric("Périodes", df["TIME_PERIOD"].nunique() if "TIME_PERIOD" in df.columns else 0)
    col3.metric(
        "Valeur max",
        f"{df[main_measure].max():,.2f}" if main_measure and pd.api.types.is_numeric_dtype(df[main_measure]) else "N/A",
    )

    filters = st.sidebar
    filters.title("Filtres")

    filter_columns = get_filter_options(df)
    selected_filters = {}
    for column in filter_columns:
        options = ["Tous"] + sorted(df[column].dropna().astype(str).unique().tolist())
        key = f"filter_{column}"
        if key not in st.session_state:
            st.session_state[key] = "Tous"
        selected_filters[column] = filters.selectbox(
            column,
            options,
            index=options.index(st.session_state[key]) if st.session_state[key] in options else 0,
            key=key,
        )

    filtered_df = prepare_export_dataframe(df, selected_filters)

    filters.subheader("Graphique")
    st.session_state.setdefault("chart_x", None)
    st.session_state.setdefault("chart_y", None)

    x_options, y_options = get_chart_candidates(filtered_df, st.session_state.get("chart_x"), st.session_state.get("chart_y"))
    if not x_options:
        st.info("Aucune colonne disponible pour construire un graphique sur ce dataset.")
        return
    if not y_options:
        st.info("Aucune colonne numérique disponible pour l'axe Y sur ce dataset. Sélectionnez un autre URL ou un autre fichier de données.")
        return

    if st.session_state["chart_x"] not in x_options:
        st.session_state["chart_x"] = x_options[0]
    if st.session_state["chart_y"] not in y_options:
        st.session_state["chart_y"] = y_options[0] if y_options else None

    chart_x = filters.selectbox(
        "Axe X",
        x_options,
        index=x_options.index(st.session_state["chart_x"]) if st.session_state["chart_x"] in x_options else 0,
        key="chart_x",
    )
    chart_y = filters.selectbox(
        "Axe Y",
        y_options,
        index=y_options.index(st.session_state["chart_y"]) if st.session_state["chart_y"] in y_options else 0,
        key="chart_y",
    )

    if filtered_df.empty:
        st.info("Aucune donnée pour ce filtre. Essayez une autre combinaison.")
    elif chart_x == chart_y:
        st.info("Les axes X et Y doivent être différents.")
    else:
        show_chart = filters.button("Afficher le graphique", width="stretch")
        if show_chart:
            if chart_x in filtered_df.columns and chart_y in filtered_df.columns:
                if pd.api.types.is_numeric_dtype(filtered_df[chart_y]):
                    chart_df = filtered_df[[chart_x, chart_y]].copy()
                    if chart_x.lower() in {"time_period", "annee", "date", "year"}:
                        chart_df = chart_df.sort_values(chart_x)
                    st.line_chart(chart_df, x=chart_x, y=chart_y)
                else:
                    chart_df = (
                        filtered_df.groupby(chart_x, as_index=False)[chart_y]
                        .count()
                        .rename(columns={chart_y: "count"})
                        .sort_values(chart_x)
                    )
                    st.bar_chart(chart_df, x=chart_x, y="count")
            else:
                st.info("Le graphique n'est pas disponible pour ce dataset ou cette sélection.")
        else:
            st.info("Choisissez un axe X et un axe Y, puis cliquez sur 'Afficher le graphique'.")

    st.subheader("Export des données")
    export_top = st.columns([5, 1.3])
    with export_top[1]:
        st.download_button(
            label="Export Filtrées (CSV)",
            data=filtered_df.to_csv(index=False).encode("utf-8"),
            file_name=f"{metadata.get('identifier', 'insee_data')}_filtered.csv",
            mime="text/csv",
            key="export_filtered_csv",
            use_container_width=True,
        )
        st.download_button(
            label="Export Total (CSV)",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"{metadata.get('identifier', 'insee_data')}_all.csv",
            mime="text/csv",
            key="export_all_csv",
            use_container_width=True,
        )
    st.dataframe(filtered_df, width="stretch")


if __name__ == "__main__":
    main()
