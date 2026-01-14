"""
Configuration centralisée pour l'application MyTakaful.
- Charge les clés depuis les variables d'environnement avec des valeurs par défaut
- Définit la connexion SQLAlchemy
- Active la protection CSRF (via SECRET_KEY)
"""

import os

# Chemin racine du projet
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Clé secrète pour sessions et CSRF (remplacez en production)
    SECRET_KEY = os.environ.get("MYTAKAFUL_SECRET_KEY") or os.urandom(24)

    # Base de données SQLite (locale par défaut, compatible déploiement)
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("MYTAKAFUL_DB_URI")
        or "sqlite:///" + os.path.join(BASE_DIR, "instance", "database.db")
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Intégrations paiement
    STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY")
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")

    PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID")
    PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET")

    # Commission technique appliquée aux cotisations (ex: 2%)
    COMMISSION_RATE = float(
        os.environ.get("MYTAKAFUL_COMMISSION_RATE", "0.02")
    )
