# From DSC 101 to DataPulse

Youssef Rafik’s DSC 101 final project, *Global Data Science Salaries Analysis*, explored salary distributions, salary prediction, experience classification, and clustering with 607 global records. The PDF describes 2020–2023. The supplied CSV contains work years **2020–2022**. There are 565 distinct rows after excluding the exported row index. The script dropped that index and kept all observations. Work year is an attribute of the salary record.

The CSV contains original salary and currency, USD salary, job title, employee residence, employer location, remote ratio, employment type, experience and company size. There are 381 fully remote and 588 full-time rows. EDA included a USD histogram, salary boxplots by experience and company-size distribution. The report gives a USD salary range of approximately $2.8k–$600k.

| Historical DSC 101 result | Reported value |
| --- | --- |
| Linear regression | Test R² 0.220, RMSE $60,469, mean five-fold training CV R² 0.084 |
| 5-neighbor experience classifier | About 52% test accuracy and 56% CV accuracy. Senior classifications performed better. |
| K-Means | Three clusters of 215, 378 and 14. Means approximately $95k, $125k and $37k. Modal levels were mid, senior and entry. |
| PCA | Two visualization components accounted for 48.8% of standardized variance. |

The regression used a 70/30 random split and one-hot coded seniority, size and employment type. It excluded job titles and country variables. KNN used a stratified 70/30 split and standardization, with salary, remote ratio, year and numeric encodings of size and employment type. Its folds reused a scaler fit to all training rows, and the ordinal coding imposed distances on employment types. K-Means reused those numeric encodings and included pay in its clustering inputs. The cluster centroids therefore describe this sample, and the results do not validate market segments. Repeated rows and potential correlation between records reduce confidence in random holdouts.

DataPulse takes posting records from separately attributed sources, validates and deduplicates them, models provenance in SQL, and estimates disclosed USD midpoints using employer-disjoint splits and a median benchmark. Posting counts, skills, geographical coverage and salary disclosure are served from the same database contract across the dashboard and API. Current DataPulse results are tracked in `results/model_metrics.json`. The academic files remain part of the author’s original archive.
