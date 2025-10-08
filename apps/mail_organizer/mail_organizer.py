"""Core of the mail_organizaer application running inside render."""
try:
    import win32com.client
except ImportError:
    win32com = None

from datetime import datetime


AUTO_SUFFIX = '[AUTO]'


def log_message(message):
    """Print message with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{timestamp}] {message}')
    return f'[{timestamp}] {message}'


def is_valid_city_name(word):
    """
    Simple heuristic to check if word could be a Dutch city name.
    Rules: starts with capital letter, no digits
    """
    if not word:
        return False
    return word[0].isupper() and not any(char.isdigit() for char in word)


def extract_project_folder_name(subject):
    """
    Extract project folder name from email subject.
    Format: "projectnummer - projectnaam - onderwerp"
    Returns the projectnaam part if valid, else None

    Example: "2024EN00183 - VGE Herten Oolder Veste - shd"
    Returns: "Herten Oolder Veste"
    """
    try:
        parts = subject.split(' - ')
        if len(parts) < 3:
            return None

        project_part = parts[1].strip()
        project_part = project_part.replace('_', ' ')

        words = project_part.split()
        if len(words) == 0:
            return None

        valid_words = [word for word in words if is_valid_city_name(word)]

        if not valid_words:
            return None

        return ' '.join(valid_words)

    except Exception as e:
        log_message(f'Error extracting folder name from "{subject}": {e}')
        return None


def get_or_create_folder(inbox, folder_name):
    """
    Find or create folder in inbox with AUTO suffix
    """
    try:
        full_name = f'{folder_name} {AUTO_SUFFIX}'

        for folder in inbox.Folders:
            if folder.Name == full_name:
                log_message(f'Folder "{full_name}" already exists')
                return folder

        new_folder = inbox.Folders.Add(full_name)
        log_message(f'New folder created: "{full_name}"')
        return new_folder

    except Exception as e:
        log_message(f'Error creating folder "{folder_name}": {e}')
        return None


def is_auto_folder(folder_name):
    """Check if folder was automatically created"""
    return folder_name.endswith(AUTO_SUFFIX)


def should_exclude_mail(subject, exclusion_words):
    """
    Check if mail subject contains any exclusion words
    """
    if not exclusion_words:
        return False

    subject_lower = subject.lower()
    for word in exclusion_words:
        if word.lower() in subject_lower:
            return True
    return False


def get_inbox():
    """Connect to Outlook and return inbox"""
    outlook = win32com.client.Dispatch('Outlook.Application')
    namespace = outlook.GetNamespace('MAPI')
    inbox = namespace.GetDefaultFolder(6)
    return inbox


def get_auto_folders(inbox):
    """Get list of all automatically created folders"""
    auto_folders = []
    for folder in inbox.Folders:
        if is_auto_folder(folder.Name):
            auto_folders.append(folder)
    return auto_folders