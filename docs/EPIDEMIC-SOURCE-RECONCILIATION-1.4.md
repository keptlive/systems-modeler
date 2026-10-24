# Epidemic source reconciliation 1.4

Reviewed 2026-10-20. This review corrects citation identity and explicitly withdraws unsupported reproduction claims. It does not certify models as trustworthy. No equations, stock initial values, IDs, flow links, time settings or positions changed.

Changed 29 model definitions; 22 had the same unrelated chondrogenesis DOI, including nine failing defaults. Other changes cover seven failing epidemiology definitions. The complete field-level before/after values, original descriptions, SHA256 manifest and evidence URLs are in operations/epidemic-source-reconciliation-v14.json.

The Keeling/Rohani book record is the Princeton University Press edition on JSTOR, copyright 2008, DOI 10.2307/j.ctvcm4gk0. It supports a conceptual book reference only. No exact book equation/parameter provenance was established. Correct bibliographic identity does not validate a generated model.

Bartlett: publisher record gives DOI 10.2307/2342553 and pages 48-60 (other references include discussion through p70). The definition is deterministic, with no extinction mechanism; its birth rate multiplies population twice. These equations were preserved and flagged.

The viral-dynamics Science DOI belongs to a protein dislocase paper; its citation was withdrawn with no speculative replacement. The peer-vaccination DOI belongs to an Umbria uptake study; source now links a related EpiModel project implementation, while explicitly identifying the library aggregate as illustrative. SIDARTHE has missing transitions; Mossong has untraced aggregate contacts; delay-SEIR lacks demonstrated history/solver equivalence. These remain unresolved.

Verification: every changed JSON parsed; the edit script asserted that only description/source/reference changed. The receipt records identical non-metadata content preservation. Simulation success cannot establish scientific fidelity and is not asserted.

## Evidence

- book: https://www.jstor.org/stable/j.ctvcm4gk0
- book: https://rohanilab.ecology.uga.edu/publications/
- wrong_book: https://ora.ox.ac.uk/objects/uuid%3A9a65a9d2-5c0c-47d5-9e34-07009a66be51
- bartlett: https://academic.oup.com/jrsssa/article/120/1/48/7101630
- hethcote: https://www.maths.usyd.edu.au/u/marym/populations/hethcote.pdf
- viral: https://parklab.mcb.berkeley.edu/papers/2020_Science_P5A-ATPase.pdf
- peer: https://iris.univpm.it/handle/11566/330960
- peer: https://github.com/EpiModel/COVID-Vax-Decisions
- age: https://journals.plos.org/plosmedicine/article?id=10.1371/journal.pmed.0050074
- delay: https://www.nature.com/articles/s41598-023-40008-9
- sidarthe: https://www.nature.com/articles/s41591-020-0883-7

## Changed models

- models/epidemiology/age-structured-epidemic-who-epi.json
- models/epidemiology/bartlett-measles-fade-out-epi.json
- models/epidemiology/cholera-sirw-model-epi.json
- models/epidemiology/covid-19-seir-model-epi.json
- models/epidemiology/covid19-sars-cov2-viral-dynamics-epi.json
- models/epidemiology/delay-differential-seir-epi.json
- models/epidemiology/dengue-vector-borne-disease-model-epi.json
- models/epidemiology/ebola-seihfr-model-epi.json
- models/epidemiology/hiv-disease-progression-epi.json
- models/epidemiology/hivaids-progression-model-epi.json
- models/epidemiology/malaria-ross-macdonald-epi.json
- models/epidemiology/malaria-vector-borne-transmission-model-epi.json
- models/epidemiology/measles-vaccination-coverage-model-epi.json
- models/epidemiology/mrna-vaccine-development-epi.json
- models/epidemiology/norovirus-outbreak-model-cruise-ship-epi.json
- models/epidemiology/peer-vaccination-network-nudge-epi.json
- models/epidemiology/pertussis-whooping-cough-waning-immunity-model-epi.json
- models/epidemiology/sd-fever-sir-model-epi.json
- models/epidemiology/seasonal-influenza-transmission-model-with-vaccination-epi.json
- models/epidemiology/si-epidemic-model-epi.json
- models/epidemiology/sidarthe-covid-italy-epi.json
- models/epidemiology/sir-treatment-dynamics-epi.json
- models/epidemiology/sirs-waning-immunity-model-epi.json
- models/epidemiology/sis-endemic-disease-model-epi.json
- models/epidemiology/tuberculosis-latent-active-epi.json
- models/epidemiology/tuberculosis-transmission-model-epi.json
- models/epidemiology/vaccination-campaign-logistics-epi.json
- models/epidemiology/vaccine-hesitancy-and-disease-dynamics-epi.json
- models/epidemiology/zika-virus-multi-route-transmission-model-epi.json
