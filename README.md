# Traffy Fondue: Citizen Report Analysis

Cleaning and visualizing Traffy Fondue, a platform where Thai citizens report city problems such as flooding, broken roads and street lighting.

**Data source:** Hugging Face [`KDAI-NLP/traffy-fondue-type-only`](https://huggingface.co/datasets/KDAI-NLP/traffy-fondue-type-only)


### Summary

After cleaning, the dataset has **386,973 reports** from September 2021 to October 2023.

- **Almost all reports come from Bangkok (99.6%).** The platform barely reaches other provinces, so this is effectively a Bangkok dataset.
- **Usage jumped in mid-2022.** There were fewer than 2,000 reports a month before May 2022, then 56,000 in June 2022. Volume settled at around 17,000–25,000 a month through 2023. Trends are only reliable from June 2022 onward.
- **Roads are the biggest problem.** 32% of reports mention roads, followed by sidewalks (12.5%), safety (9.2%), street lighting (9.0%) and cleanliness (8.0%).
- **Flooding is seasonal.** Its share rises in the rainy season, peaking at 19% of reports in September 2022 and 10% in September 2023, and drops to 2–3% in the dry months.
- **A few districts generate the most reports.** Chatuchak leads (21,158 reports), followed by Prawet, Bang Kapi, Khlong Toei and Lat Krabang. Prawet and Lat Krabang report far more flooding than average (17% and 12%).
- **People report during the day.** Reports peak at 5–7 pm and are higher on weekdays than weekends. Street-lighting problems are the exception: 53% of them are reported between 6 pm and midnight, compared with 29% of all reports.
- **Categories are often unclear.** 18% of reports have no category and 32% have more than one, which makes it harder to route reports to the right team.

### Recommendations

1. **Put road and sidewalk repair first.** Together these are almost half of all reports, so fixing them faster would have the biggest effect.
2. **Get ready for floods before the rainy season.** Clear drains and check pumps in May and June, starting in high-flood districts such as Prawet and Lat Krabang.
3. **Give staff to districts based on report volume.** Busy districts like Chatuchak, Prawet and Bang Kapi may need more field teams or faster triage.
4. **Improve categorization at submission.** Require a category, suggest one from the comment text, or auto-tag reports with a text classifier, to reduce the 18% that are unspecified.
5. **Schedule lighting checks for the evening.** Most lighting problems are noticed after dark, so night-time inspections could find faults before residents report them.
6. **Promote the platform outside Bangkok.** Other provinces are almost absent, so promoting it there would give a nationwide picture.

*Limitation:* This dataset has no report status or resolution time, so it can't show how quickly problems are fixed. Adding that data would be the next step.

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
