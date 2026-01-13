"""
Internationalization (i18n) module for MyTakaful application.
Supports Arabic, French, and English languages.
"""

import json
import os
from flask import session, request

# Define the path to the translation files
TRANSLATIONS_DIR = os.path.join(os.path.dirname(__file__))

# Supported languages
SUPPORTED_LANGUAGES = ['fr', 'en', 'ar']

# Default language
DEFAULT_LANGUAGE = 'fr'

def load_translations(lang_code):
    """
    Load translations for the specified language.
    
    Args:
        lang_code (str): Language code ('fr', 'en', 'ar')
        
    Returns:
        dict: Translations dictionary
    """
    try:
        file_path = os.path.join(TRANSLATIONS_DIR, f"{lang_code}.json")
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Fall back to default language if translation file not found
        file_path = os.path.join(TRANSLATIONS_DIR, f"{DEFAULT_LANGUAGE}.json")
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        # Return empty dict if any other error occurs
        return {}

def get_current_language():
    """
    Get the current language from session or request.
    
    Returns:
        str: Current language code
    """
    # First check session
    lang = session.get('language')
    if lang and lang in SUPPORTED_LANGUAGES:
        return lang
    
    # Then check URL parameter
    lang = request.args.get('lang')
    if lang and lang in SUPPORTED_LANGUAGES:
        session['language'] = lang
        return lang
    
    # Default to French
    return DEFAULT_LANGUAGE

def set_language(lang_code):
    """
    Set the current language in session.
    
    Args:
        lang_code (str): Language code to set
    """
    if lang_code in SUPPORTED_LANGUAGES:
        session['language'] = lang_code

def t(key, lang_code=None):
    """
    Translate a key to the current language.
    
    Args:
        key (str): Translation key (e.g., 'login.title')
        lang_code (str, optional): Specific language code
        
    Returns:
        str: Translated text or key if not found
    """
    if lang_code is None:
        lang_code = get_current_language()
    
    translations = load_translations(lang_code)
    
    # Navigate through the nested dictionary using the key
    keys = key.split('.')
    value = translations
    
    try:
        for k in keys:
            value = value[k]
        return value
    except (KeyError, TypeError):
        # Return the key itself if translation not found
        return key

def is_rtl(lang_code=None):
    """
    Check if the language is right-to-left.
    
    Args:
        lang_code (str, optional): Specific language code
        
    Returns:
        bool: True if RTL language, False otherwise
    """
    if lang_code is None:
        lang_code = get_current_language()
    return lang_code == 'ar'

def get_language_direction(lang_code=None):
    """
    Get the text direction for the language.
    
    Args:
        lang_code (str, optional): Specific language code
        
    Returns:
        str: 'rtl' for right-to-left, 'ltr' for left-to-right
    """
    return 'rtl' if is_rtl(lang_code) else 'ltr'

def get_available_languages():
    """
    Get list of available languages with their names.
    
    Returns:
        list: List of dictionaries with lang_code and language name
    """
    languages = []
    for lang_code in SUPPORTED_LANGUAGES:
        translations = load_translations(lang_code)
        languages.append({
            'lang_code': lang_code,
            'name': translations.get('language', lang_code)
        })
    return languages