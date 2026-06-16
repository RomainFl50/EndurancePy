"""Tests for the Al Kamel result-file discovery (HTML parsing)."""

from __future__ import annotations

from endurancepy.alkamel.discovery import find_files, index_page

# A synthetic portal page snippet mirroring the real Results/... link structure.
HTML = """
<a href="Results/08_2018-2019/07_SPA FRANCORCHAMPS/00_Event Info/Entry List.PDF">x</a>
<a href="Results/08_2018-2019/07_SPA FRANCORCHAMPS/267_FIA WEC/201905021200_Free Practice 1/23_Analysis_Free Practice 1.CSV">x</a>
<a href="Results/08_2018-2019/07_SPA FRANCORCHAMPS/267_FIA WEC/201905021200_Free Practice 1/03_Classification_Free Practice 1.CSV">x</a>
<a href="Results/08_2018-2019/07_SPA FRANCORCHAMPS/267_FIA WEC/201905041330_Race/Hour 6/23_Analysis_Race_Hour 6.CSV">x</a>
<a href="Results/08_2018-2019/07_SPA FRANCORCHAMPS/267_FIA WEC/201905041330_Race/Hour 6/05_Classification_Race_Hour 6.CSV">x</a>
<a href="Results/08_2018-2019/07_SPA FRANCORCHAMPS/267_FIA WEC/201905041330_Race/Hour 6/26_Weather_Race_Hour 6.CSV">x</a>
<a href="Results/08_2018-2019/08_LE MANS/276_FIA WEC/201906151500_Race/06_Hour 6/05_Classification_Race_Hour 6.CSV">x</a>
"""


def test_index_skips_non_csv_and_parses_all_csv() -> None:
    records = index_page(HTML)
    # The Entry List PDF is ignored; the 6 CSVs are parsed.
    assert len(records) == 6


def test_record_fields() -> None:
    records = index_page(HTML)
    race_class = find_files(records, kind="classification", event="SPA", session="Race")
    assert len(race_class) == 1
    rec = race_class[0]
    assert rec.season == "08_2018-2019"
    assert rec.event == "07_SPA FRANCORCHAMPS"
    assert rec.series == "267_FIA WEC"
    assert rec.hour == 6
    assert rec.filename == "05_Classification_Race_Hour 6.CSV"


def test_hour_parsed_from_numeric_folder() -> None:
    records = index_page(HTML)
    lemans = find_files(records, event="LE MANS")
    assert len(lemans) == 1
    assert lemans[0].hour == 6  # from the "06_Hour 6" folder


def test_filter_by_kind() -> None:
    records = index_page(HTML)
    assert len(find_files(records, kind="analysis")) == 2
    assert len(find_files(records, kind="weather")) == 1


def test_url_encodes_spaces() -> None:
    rec = find_files(index_page(HTML), kind="weather")[0]
    url = rec.url("fiawec.alkamelsystems.com")
    assert url == (
        "https://fiawec.alkamelsystems.com/Results/08_2018-2019/"
        "07_SPA%20FRANCORCHAMPS/267_FIA%20WEC/201905041330_Race/Hour%206/"
        "26_Weather_Race_Hour%206.CSV"
    )
