# Personal-Project

<img width="1810" height="1022" alt="image" src="https://github.com/user-attachments/assets/3c109984-9f46-4ef9-9757-a9c012b16cd4" />

# Traffy Fondue: Citizen Report Analysis

Cleaning and visualizing Traffy Fondue, a platform where Thai citizens report city problems such as flooding, broken roads and street lighting.

**Data source:** Hugging Face [`KDAI-NLP/traffy-fondue-type-only`](https://huggingface.co/datasets/KDAI-NLP/traffy-fondue-type-only)

## Summary and recommendations

I wrote a short summary with recommendations based on my findings.

<!-- Paste your summary and recommendations here, or link to them -->

## What was done

1. **Explored** the raw data (`load_data.ipynb`): columns, missing values, timestamp range, category counts and duplicates.
2. **Cleaned** the data (`clean_data.py`):
   - Converted timestamps from UTC to Bangkok time (UTC+7)
   - Standardized province, district and subdistrict names (removed prefixes like จังหวัด / เขต / แขวง, fixed typos, merged Bangkok spellings)
   - Corrected provinces using the district name, and marked invalid locations as unspecified
   - Added English names from a Thai province/district/subdistrict lookup
   - Removed duplicate reports (same ticket, or same comment in the same district on the same day)
   - Added time columns (month, hour, weekday) and category counts
3. **Visualized** the results in Power BI (`visualize.pbix`).

## Files

| File | Description |
|---|---|
| `load_data.ipynb` | Exploration and step-by-step cleaning notebook |
| `clean_data.py` | Full cleaning pipeline |
| `bangkok_subdistricts.csv` | Bangkok subdistrict lookup (Thai / English) |
| `thailand_subdistricts.csv` | All-Thailand subdistrict lookup |
| `traffy_fondue_clean.parquet` | Cleaned dataset |
| `powerbi/reports.csv` | One row per report (Power BI input) |
| `powerbi/report_categories.csv` | One row per report per category, join on `ticket_id` |
| `visualize.pbix` | Power BI dashboard |

Large files are stored with Git LFS.

## How to run

```bash
pip install pandas pyarrow datasets
python clean_data.py
```

Then open `visualize.pbix` in Power BI Desktop and refresh.
