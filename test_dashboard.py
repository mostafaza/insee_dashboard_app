import pandas as pd

import pytest

from insee_dashboard import (
    build_dashboard,
    get_chart_candidates,
    get_filter_options,
    infer_measure_columns,
    parse_insee_xml,
    prepare_export_dataframe,
)


SAMPLE_XML = '''
<DataSetPresentation>
  <identifier>DS_RP_EMPLOI_LR_PRINC</identifier>
  <title>
    <fr>Population active et chômage</fr>
    <en>Labor force and unemployment</en>
  </title>
  <observations>
    <observations>
      <dimensions>
        <GEO>2026-AAV2020-001</GEO>
        <SEX>F</SEX>
        <TIME_PERIOD>2012</TIME_PERIOD>
        <RP_MEASURE>POP</RP_MEASURE>
      </dimensions>
      <attributes>
        <OBS_STATUS>A</OBS_STATUS>
      </attributes>
      <measures>
        <OBS_VALUE_NIVEAU><value>250757.21124</value></OBS_VALUE_NIVEAU>
      </measures>
    </observations>
    <observations>
      <dimensions>
        <GEO>2026-AAV2020-001</GEO>
        <SEX>M</SEX>
        <TIME_PERIOD>2012</TIME_PERIOD>
        <RP_MEASURE>POP</RP_MEASURE>
      </dimensions>
      <attributes>
        <OBS_STATUS>A</OBS_STATUS>
      </attributes>
      <measures>
        <OBS_VALUE_NIVEAU><value>257329.30549</value></OBS_VALUE_NIVEAU>
      </measures>
    </observations>
  </observations>
</DataSetPresentation>
'''


def test_parse_insee_xml_returns_dataframe_rows():
    df = parse_insee_xml(SAMPLE_XML)
    assert list(df.columns) == [
        "GEO",
        "SEX",
        "TIME_PERIOD",
        "RP_MEASURE",
        "OBS_STATUS",
        "OBS_VALUE_NIVEAU",
    ]
    assert len(df) == 2
    assert df.iloc[0]["SEX"] == "F"
    assert float(df.iloc[0]["OBS_VALUE_NIVEAU"]) == 250757.21124


def test_infer_measure_columns_ignores_unit_columns():
    columns = [
        "UNIT_MEASURE",
        "OBS_VALUE_INDICE_DE_PRIX",
        "TIME_PERIOD",
        "GEO",
    ]
    assert infer_measure_columns(columns) == ["OBS_VALUE_INDICE_DE_PRIX"]


def test_build_dashboard_converts_measure_columns_to_numeric():
    df = pd.DataFrame(
        {
            "GEO": ["FR"],
            "TIME_PERIOD": ["2024"],
            "UNIT_MEASURE": ["%"],
            "OBS_VALUE_INDICE_DE_PRIX": ["123.45"],
        }
    )
    converted = build_dashboard(df)
    assert pd.api.types.is_numeric_dtype(converted["OBS_VALUE_INDICE_DE_PRIX"])
    assert float(converted["OBS_VALUE_INDICE_DE_PRIX"].iloc[0]) == 123.45


def test_get_chart_candidates_excludes_selected_axis_and_keeps_same_field_pool():
    df = pd.DataFrame(
        {
            "GEO": ["FR", "FR"],
            "TIME_PERIOD": ["2023", "2024"],
            "OBS_VALUE_INDICE_DE_PRIX": [10.5, 12.5],
            "OTHER_VALUE": [100, 200],
        }
    )
    x_options, y_options = get_chart_candidates(df, x_axis="TIME_PERIOD")

    assert "TIME_PERIOD" not in y_options
    assert "GEO" in x_options
    assert "GEO" in y_options
    assert all(col != "TIME_PERIOD" for col in y_options)


def test_prepare_export_dataframe_applies_selected_filters():
    df = pd.DataFrame(
        {
            "GEO": ["FR", "BE"],
            "TIME_PERIOD": ["2023", "2024"],
            "OBS_VALUE_INDICE_DE_PRIX": [10.5, 20.5],
        }
    )
    result = prepare_export_dataframe(df, {"GEO": "FR"})
    assert list(result["GEO"]) == ["FR"]
    assert len(result) == 1


def test_get_filter_options_keeps_high_cardinality_dimensions():
    df = pd.DataFrame(
        {
            "GEO": [f"GEO-{i}" for i in range(60)],
            "SEX": ["F", "M"] * 30,
            "TIME_PERIOD": [2020] * 60,
            "OBS_STATUS": ["A"] * 60,
            "OBS_VALUE_NIVEAU": list(range(60)),
        }
    )
    filters = get_filter_options(df)
    assert "GEO" in filters
    assert "SEX" in filters
    assert "TIME_PERIOD" in filters
    assert "OBS_STATUS" in filters
    assert "OBS_VALUE_NIVEAU" in filters


def test_parse_insee_xml_rejects_non_xml_content():
    html = "<html><body>not a dataset</body></html>"
    with pytest.raises(ValueError, match="XML INSEE valide"):
        parse_insee_xml(html)
