## 2. VacancesAPI (TODO)

Classe pour récupérer les dates de vacances scolaires.

### Source

- **API** : [GitHub - vacances-scolaires](https://raw.githubusercontent.com/AntoineAugusti/vacances-scolaires/refs/heads/master/data.csv)
- **Données** : Vacances scolaires par zones (A, B, C)

### Utilisation envisagée

```python
from ml.utils.api import VacancesAPI

vacances = VacancesAPI()
df = vacances.fetch(year=2024)
df.to_parquet("data/processed/vacances_2024.parquet")
```

### Colonnes attendues

| Colonne | Type | Description |
|---------|------|-------------|
| `start_date` | date | Début vacances |
| `end_date` | date | Fin vacances |
| `zone` | string | Zone A, B ou C |
| `type` | string | Type (hiver, printemps, etc.) |

## 3. JoursFeriesAPI (TODO)

Classe pour récupérer les jours fériés en France.

### Source

- **API** : [calendrier.api.gouv.fr](https://calendrier.api.gouv.fr/jours-feries/metropole/)
- **Données** : Jours fériés nationaux

### Utilisation envisagée

```python
from ml.utils.api import JoursFeriesAPI

jours_feries = JoursFeriesAPI()
df = jours_feries.fetch(year=2024)
df.to_parquet("data/processed/jours_feries_2024.parquet")
```

### Exemple API

```javascript
// Exemple de réponse API
// GET https://calendrier.api.gouv.fr/jours-feries/metropole/2024.json

{
  "Jour de l'an": "2024-01-01",
  "Lundi de Pâques": "2024-04-01",
  "Fête du Travail": "2024-05-01",
  "Victoire 1945": "2024-05-08",
  "Ascension": "2024-05-09",
  "Lundi de Pentecôte": "2024-05-20",
  "Fête nationale": "2024-07-14",
  "Assomption": "2024-08-15",
  "Toussaint": "2024-11-01",
  "Armistice 1918": "2024-11-11",
  "Noël": "2024-12-25"
}
```





#Source vacances
https://www.data.gouv.fr/api/1/datasets/r/c3781037-dffb-4789-9af9-15a955336771 -> Lien vers l'url suivante
https://raw.githubusercontent.com/AntoineAugusti/vacances-scolaires/refs/heads/master/data.csv
-> Idealement faire une API pour obtenir juste les années souhaitées


#source jours fériés
async function getJoursFeriesDeuxAnnees(annee1, annee2) {
    const [r1, r2] = await Promise.all([
        fetch(`https://calendrier.api.gouv.fr/jours-feries/metropole/${annee1}.json`),
        fetch(`https://calendrier.api.gouv.fr/jours-feries/metropole/${annee2}.json`)
    ]);

    const jf1 = await r1.json();
    const jf2 = await r2.json();

    return { ...jf1, ...jf2 };
}

getJoursFeriesDeuxAnnees(2026, 2027)
    .then(console.log);