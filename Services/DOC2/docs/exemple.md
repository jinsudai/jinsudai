# Architecture du Système

Voici un diagramme détaillé de l'architecture :

```mermaid
graph LR
    subgraph "Couche Données"
        A[Base de Données EHS] --> B[API Data]
    end
    subgraph "Couche Traitement"
        B --> C[Analyse des Risques]
        C --> D[Modèle IA]
    end
    subgraph "Couche Présentation"
        D --> E[Tableau de Bord]
        E --> F[Rapport PDF]
    end
    style A fill:#4CAF50
    style D fill:#FF9800
    style E fill:#2196F3