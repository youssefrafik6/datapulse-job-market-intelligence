# Skill and job title rules

The code in `src/datapulse/rules.py` defines a versioned dictionary and rule set. A supplier skill list is parsed as data with a size limit and without evaluating executable expressions. Each unique alias maps to one canonical skill. Unknown tags count toward a quality flag. Separate context-aware, boundary-delimited regex supports future description-bearing inputs. Go and R require language context. Spark requires Apache Spark or Spark SQL in free text. Case-sensitive patterns protect terms such as Git and Excel.

Both downloaded production sources expose supplier skill lists. They do not contain descriptions, so the pipeline does not independently verify supplier labels against the advertisements. Published coverage measures the percentage of records with at least one tracked mention. It is distinct from extraction recall.

## Evaluation

Three hand-labeled, authored test snippets produced 11 true positives, zero false positives and zero false negatives. Micro-precision and micro-recall were both 100% on this tiny control set. Cases include language aliases, tool names and ordinary uses of ambiguous words. Production precision and recall require a manually labeled sample with original description text.

## Titles and seniority

The title matcher reports multiple candidate families as **Ambiguous**. It retains original wording and identifies residual titles as **Other Technology**. A deterministic review took the first three posting IDs per predicted class in the Zalize snapshot, yielding 33 examples. A manual title-only pass agreed with 29 classifications, including two clearly dual-family software/data engineering titles. Four judgment calls were recorded as disagreements: a title headed by Analytics Engineer with a Data Science department, Business Intelligence Researcher, a SCADA/HMI Platform Engineer, and a Regulatory Analyst under Other Technology. This is a small stratified, single-reviewer audit. Its 29/33 agreement is a diagnostic and does not estimate population-level accuracy.

Explicit early-career words create a title signal. The Entry label additionally requires supported experience wording. Original posting requirements cannot be independently reconstructed from the two built-in sources, and an Unknown experience level should be expected.
