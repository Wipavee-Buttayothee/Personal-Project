"""Clean the Traffy Fondue dataset (all provinces) and save the results.

Source: Hugging Face "KDAI-NLP/traffy-fondue-type-only"
Output: traffy_fondue_clean.parquet
        powerbi/reports.csv            one row per report
        powerbi/report_categories.csv  one row per report per category (join on ticket_id)

Run:  python clean_data.py
"""
import json
import os
import urllib.request

import pandas as pd
from datasets import load_dataset

# ---------------------------------------------------------------- settings
FOLDER = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(FOLDER, "traffy_fondue_clean.parquet")
POWERBI_FOLDER = os.path.join(FOLDER, "powerbi")
BKK_LOOKUP_FILE = os.path.join(FOLDER, "bangkok_subdistricts.csv")
TH_LOOKUP_FILE = os.path.join(FOLDER, "thailand_subdistricts.csv")
TH_LOOKUP_URL = ("https://raw.githubusercontent.com/kongvut/thai-province-data/master/"
                 "api/latest/sub_district_with_district_and_province.json")

BKK = "กรุงเทพมหานคร"
UNSPECIFIED = "ไม่ระบุ"

# Other spellings in the raw data that mean Bangkok
BKK_NAMES = ["กรุงเทพฯ", "กรุงเทพ", "Bangkok", "กทม", "กทม."]

# Typos in the raw district / subdistrict names
DISTRICT_FIXES = {"ป้อมปราบศัตรูพ่า": "ป้อมปราบศัตรูพ่าย"}
SUBDISTRICT_FIXES = {"จักรวรรดิ์": "จักรวรรดิ"}

# English names for the problem categories (the is_<Thai name> columns)
CATEGORY_EN = {
    "ไม่ระบุ": "Unspecified",
    "ความสะอาด": "Cleanliness",
    "สายไฟ": "Power lines",
    "สะพาน": "Bridge",
    "ถนน": "Road",
    "น้ำท่วม": "Flooding",
    "ร้องเรียน": "Complaint",
    "ท่อระบายน้ำ": "Drainage",
    "ความปลอดภัย": "Safety",
    "คลอง": "Canal",
    "แสงสว่าง": "Street lighting",
    "ทางเท้า": "Sidewalk",
    "จราจร": "Traffic",
    "กีดขวาง": "Obstruction",
    "การเดินทาง": "Transport",
    "เสียงรบกวน": "Noise",
    "ต้นไม้": "Trees",
    "สัตว์จรจัด": "Stray animals",
    "เสนอแนะ": "Suggestion",
    "คนจรจัด": "Homeless",
    "ห้องน้ำ": "Restroom",
    "ป้ายจราจร": "Traffic sign",
    "สอบถาม": "Inquiry",
    "ป้าย": "Signage",
    "PM2.5": "PM2.5",
}

# Before this month there are < 2,000 reports a month, so trends are only reliable from here on
RELIABLE_FROM = "2022-06-01"

# Informative comment = at least this many characters (shorter ones are like "ขยะ", "ไฟดับ")
MIN_COMMENT_LEN = 10


# ---------------------------------------------------------------- lookup table
def download_thai_lookup():
    """Download every Thai province / district / subdistrict and save it as a CSV."""
    print("Downloading Thai province/district/subdistrict names ...")
    response = urllib.request.urlopen(TH_LOOKUP_URL, timeout=60)
    data = json.load(response)
    response.close()

    rows = []
    for item in data:
        if item["deleted_at"] is not None:
            continue
        district = item["district"]
        province = district["province"]
        rows.append({
            "province": province["name_th"],
            "province_en": province["name_en"],
            "district": district["name_th"].replace("เขต", "", 1) if district["name_th"].startswith("เขต") else district["name_th"],
            "district_en": district["name_en"].replace("Khet ", "", 1) if district["name_en"].startswith("Khet ") else district["name_en"],
            "subdistrict": item["name_th"],
            "subdistrict_en": item["name_en"],
        })

    pd.DataFrame(rows).to_csv(TH_LOOKUP_FILE, index=False, encoding="utf-8-sig")


def load_thai_lookup():
    """Table of every province / district / subdistrict with English names.

    Bangkok rows come from bangkok_subdistricts.csv (newer subdistrict boundaries).
    """
    if not os.path.exists(TH_LOOKUP_FILE):
        download_thai_lookup()

    th = pd.read_csv(TH_LOOKUP_FILE, encoding="utf-8-sig")
    bkk = pd.read_csv(BKK_LOOKUP_FILE, encoding="utf-8-sig")
    bkk["province"] = BKK
    bkk["province_en"] = "Bangkok"
    bkk = bkk[th.columns]

    # Put the Bangkok file first so it wins when we drop duplicates.
    # Old Bangkok subdistricts from the big file are kept too (older reports may use them).
    th_bkk = th[th["province"] == BKK]
    th_other = th[th["province"] != BKK]
    lookup = pd.concat([bkk, th_bkk, th_other])
    lookup = lookup.drop_duplicates(subset=["province", "district", "subdistrict"])
    return lookup


# ---------------------------------------------------------------- cleaning steps
def clean_province(df, lookup):
    """Remove 'จังหวัด' / 'จ.' prefixes, unify Bangkok, and set junk to ไม่ระบุ."""
    df["province"] = df["province"].str.replace("จังหวัด", "", regex=False)
    df["province"] = df["province"].str.replace("จ.", "", regex=False)
    df["province"] = df["province"].str.strip()

    df.loc[df["province"].isin(BKK_NAMES), "province"] = BKK

    # Anything that isn't a real Thai province (e.g. "Lac", "Borno") -> unspecified
    real_provinces = lookup["province"].unique()
    df.loc[~df["province"].isin(real_provinces), "province"] = UNSPECIFIED
    return df


def fix_province_from_district(df, lookup):
    """Some reports say Bangkok but the district is e.g. บางกรวย (Nonthaburi).
    If the district doesn't exist in the given province but belongs to only
    one province, use that province instead."""
    pairs = lookup[["province", "district"]].drop_duplicates()

    # Districts whose name appears in only one province
    district_counts = pairs["district"].value_counts()
    unique_districts = district_counts[district_counts == 1].index
    unique_pairs = pairs[pairs["district"].isin(unique_districts)]
    district_to_province = dict(zip(unique_pairs["district"], unique_pairs["province"]))

    # Is the (province, district) combination real?
    valid_keys = pairs["province"] + "|" + pairs["district"]
    df_keys = df["province"] + "|" + df["district"]
    wrong_province = ~df_keys.isin(valid_keys)

    fixable = wrong_province & df["district"].isin(unique_districts)
    df.loc[fixable, "province"] = df.loc[fixable, "district"].map(district_to_province)
    print(f"  province corrected from district: {fixable.sum():,} rows")
    return df


def add_english_names(df, lookup):
    """Add province_en, district_en and subdistrict_en by merging with the lookup table."""
    province_names = lookup[["province", "province_en"]].drop_duplicates(subset=["province"])
    district_names = lookup[["province", "district", "district_en"]].drop_duplicates(subset=["province", "district"])
    subdistrict_names = lookup[["province", "district", "subdistrict", "subdistrict_en"]]

    df = df.merge(province_names, on="province", how="left")
    df = df.merge(district_names, on=["province", "district"], how="left")
    df = df.merge(subdistrict_names, on=["province", "district", "subdistrict"], how="left")

    for th_col in ["province", "district", "subdistrict"]:
        en_col = th_col + "_en"
        df.loc[df[th_col] == UNSPECIFIED, en_col] = "Unspecified"

        # Not found in the lookup -> keep the Thai name
        missing = df[en_col].isna()
        print(f"  {en_col}: {missing.sum():,} rows not in lookup (kept Thai name)")
        df.loc[missing, en_col] = df.loc[missing, th_col]
    return df


def remove_duplicates(df):
    """Same comment at the same place on the same day = the same report sent again."""
    # Timestamps are UTC, add 7 hours to get the Bangkok day
    df["day"] = (df["timestamp"] + pd.Timedelta(hours=7)).dt.date
    before = len(df)
    df = df.drop_duplicates(subset=["comment", "province", "district", "subdistrict", "day"])
    df = df.drop(columns=["day"])
    df = df.reset_index(drop=True)
    print(f"  dropped {before - len(df):,} duplicates")
    return df


def add_time_columns(df):
    # Raw timestamps are UTC -> convert to Bangkok time (UTC+7)
    df["timestamp"] = df["timestamp"].dt.tz_localize("UTC").dt.tz_convert("Asia/Bangkok")
    df["date"] = df["timestamp"].dt.date
    df["year"] = df["timestamp"].dt.year
    df["month_of_year"] = df["timestamp"].dt.month
    df["month"] = pd.to_datetime(df["year"].astype(str) + "-" + df["month_of_year"].astype(str) + "-01")
    df["hour"] = df["timestamp"].dt.hour
    df["weekday"] = df["timestamp"].dt.day_name()
    return df


# ---------------------------------------------------------------- Power BI export
def export_powerbi(df):
    """Two CSVs for Power BI, related on ticket_id (one report -> many categories)."""
    os.makedirs(POWERBI_FOLDER, exist_ok=True)

    columns = [
        "ticket_id", "timestamp", "date", "month", "year", "month_of_year", "hour", "weekday",
        "province", "province_en", "district", "district_en", "subdistrict", "subdistrict_en",
        "is_bangkok", "type", "n_categories", "informative_text", "comment",
    ]
    reports = df[columns].copy()

    # Power BI doesn't handle time zones well -> plain Bangkok local time
    reports["timestamp"] = reports["timestamp"].dt.tz_localize(None)
    reports["weekday_num"] = df["timestamp"].dt.dayofweek + 1  # Monday = 1, for "Sort by column"
    reports["reliable_period"] = reports["month"] >= RELIABLE_FROM
    # Newlines inside comments break some CSV readers
    reports["comment"] = reports["comment"].str.replace(r"\s+", " ", regex=True)

    # One row for every (report, category) pair
    category_tables = []
    for category_th, category_en in CATEGORY_EN.items():
        has_category = df["is_" + category_th] == 1
        table = pd.DataFrame({"ticket_id": df.loc[has_category, "ticket_id"]})
        table["category_th"] = category_th
        table["category_en"] = category_en
        category_tables.append(table)
    categories = pd.concat(category_tables, ignore_index=True)

    # utf-8-sig so Power BI / Excel read the Thai text correctly
    reports.to_csv(os.path.join(POWERBI_FOLDER, "reports.csv"), index=False, encoding="utf-8-sig")
    categories.to_csv(os.path.join(POWERBI_FOLDER, "report_categories.csv"), index=False, encoding="utf-8-sig")
    print(f"Saved powerbi/reports.csv ({len(reports):,} rows)")
    print(f"Saved powerbi/report_categories.csv ({len(categories):,} rows)")


# ---------------------------------------------------------------- main
def main():
    print("Loading raw dataset ...")
    dataset = load_dataset("KDAI-NLP/traffy-fondue-type-only")
    df = dataset["train"].to_pandas()
    n_raw = len(df)
    print(f"  raw rows: {n_raw:,}")

    lookup = load_thai_lookup()

    # Text columns: remove spaces at the ends, empty text -> ไม่ระบุ
    for col in ["province", "district", "subdistrict", "type"]:
        df[col] = df[col].str.strip()
        df[col] = df[col].replace("", UNSPECIFIED)
    df["comment"] = df["comment"].str.strip()

    print("Cleaning locations ...")
    df = clean_province(df, lookup)
    df["district"] = df["district"].replace(DISTRICT_FIXES)
    df["subdistrict"] = df["subdistrict"].replace(SUBDISTRICT_FIXES)
    df = fix_province_from_district(df, lookup)
    df = add_english_names(df, lookup)
    df["is_bangkok"] = df["province"] == BKK

    print("Removing duplicate reports ...")
    df = remove_duplicates(df)

    df = add_time_columns(df)

    # Number of categories per report (not counting "ไม่ระบุ")
    category_cols = []
    for category_th in CATEGORY_EN:
        if category_th != UNSPECIFIED:
            category_cols.append("is_" + category_th)
    df["n_categories"] = df[category_cols].sum(axis=1)

    df["informative_text"] = df["comment"].str.len() >= MIN_COMMENT_LEN

    df.to_parquet(OUTPUT_FILE, index=False)

    print(f"\nSaved traffy_fondue_clean.parquet: {len(df):,} rows (from {n_raw:,})")
    print(f"  provinces: {df['province'].nunique()}")
    print(f"  Bangkok share: {df['is_bangkok'].mean():.1%}")
    print(df["province_en"].value_counts().head(10))

    export_powerbi(df)


if __name__ == "__main__":
    main()
