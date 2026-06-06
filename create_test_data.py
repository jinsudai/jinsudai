import sys
sys.path.insert(0, 'src')
import pandas as pd
import numpy as np
import os

# S'assurer que data/templates et data/processed existent
os.makedirs('data/templates', exist_ok=True)
os.makedirs('data/processed', exist_ok=True)

# Générer des données de test (1 mois)
dates = pd.date_range('2024-01-01 00:00', '2024-01-31 23:30', freq='30min')
np.random.seed(42)

# Raw consommation
hourly_pattern = [500, 450, 400, 380, 360, 350, 380, 400, 450, 500, 550, 600, 
                  650, 700, 720, 750, 800, 850, 900, 950, 1000, 980, 900, 800]
raw_values = []
for d in dates:
    hour = d.hour
    base_value = hourly_pattern[hour % 24]
    noise = np.random.normal(0, 50)
    raw_values.append(max(0, base_value + noise))

raw_df = pd.DataFrame({
    'Identifiant PRM': ['0'] * len(dates),
    'Date de début': ['2024-01-01 00:00'] * len(dates),
    'Date de fin': ['2024-01-31 23:30'] * len(dates),
    'Grandeur physique': ['PA'] * len(dates),
    'Grandeur métier': ['CONS'] * len(dates),
    'Etape métier': ['BRUT'] * len(dates),
    'Unité': ['W'] * len(dates),
    'Horodate': dates,
    'Valeur': raw_values,
    'Nature': ['B'] * len(dates),
    'Pas': ['PT30M'] * len(dates),
    'Indice de vraisemblance': [0] * len(dates),
    'Etat complémentaire': [0] * len(dates)
})
raw_df.to_csv('data/templates/test_raw_consumption.csv', index=False, sep=';')
print(f'Created: data/templates/test_raw_consumption.csv ({raw_df.shape})')

# Weather data
weather_df = pd.DataFrame({
    'Horodate': dates,
    'temperature_2m_mean': np.random.normal(10, 5, len(dates)),
    'relative_humidity_mean': np.random.normal(70, 10, len(dates)),
    'precipitation_sum': np.random.exponential(0.1, len(dates))
})
weather_df.to_parquet('data/processed/test_weather_full.parquet')
print(f'Created: data/processed/test_weather_full.parquet ({weather_df.shape})')

# Holidays data
holidays_df = pd.DataFrame({
    'Horodate': dates,
    'is_vacances': [1 if (d.month == 1 and d.day <= 7) else 0 for d in dates],
    'nom_vacances': ['Noël' if (d.month == 1 and d.day <= 7) else '' for d in dates],
    'jour de la semaine': [d.strftime('%A') for d in dates],
    'jour férié': [1 if d.day == 1 and d.month == 1 else 0 for d in dates]
})
holidays_df.to_parquet('data/processed/test_holidays_full.parquet')
print(f'Created: data/processed/test_holidays_full.parquet ({holidays_df.shape})')

print('\nAll test files created successfully!')
