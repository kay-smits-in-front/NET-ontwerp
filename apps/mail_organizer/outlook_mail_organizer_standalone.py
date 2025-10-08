"""
Outlook Mail Organizer - Standalone Script
Organiseert Outlook mails automatisch op basis van plaatsnamen in onderwerp

Gebruik:
    python outlook_mail_organizer.py

Vereist:
    pip install pywin32
"""

import win32com.client
from datetime import datetime
import sys


AUTO_SUFFIX = '[AUTO]'


def log_message(message):
	"""Print message with timestamp"""
	timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
	print(f'[{timestamp}] {message}')


def is_valid_city_name(word):
	"""Check if word could be a Dutch city name"""
	if not word:
		return False
	return word[0].isupper() and not any(char.isdigit() for char in word)


def extract_project_folder_name(subject):
	"""Extract folder name from email subject"""
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
	"""Find or create folder in inbox with AUTO suffix"""
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


def should_exclude_mail(subject, exclusion_words):
	"""Check if mail subject contains any exclusion words"""
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


def process_mails(max_mails, exclusion_words):
	"""Process emails based on configuration"""
	try:
		log_message('Connecting to Outlook...')
		inbox = get_inbox()
		log_message(f'Inbox found: {inbox.Name}')

		messages = inbox.Items

		# Sorteer op ontvangstdatum, nieuwste eerst
		messages.Sort('[ReceivedTime]', True)

		if messages.Count == 0:
			log_message('No emails found')
			return

		log_message(f'{messages.Count} emails found in inbox')

		processed_count = 0
		skipped_count = 0

		# Verwerk de laatste X mails
		for i in range(1, min(messages.Count, max_mails) + 1):
			try:
				mail = messages.Item(i)
				subject = mail.Subject
				was_unread = mail.UnRead  # Bewaar originele status

				log_message(f'Processing email: "{subject}"')

				if should_exclude_mail(subject, exclusion_words):
					log_message('Email excluded (contains exclusion word)')
					skipped_count += 1
					continue

				dash_count = subject.count(' - ')
				if dash_count < 2:
					log_message(
						f'Email has incorrect format (only {dash_count}x " - "), skip'
					)
					skipped_count += 1
					continue

				folder_name = extract_project_folder_name(subject)
				if not folder_name:
					log_message('Could not extract folder name, skip')
					skipped_count += 1
					continue

				log_message(f'Folder name found: "{folder_name}"')

				project_folder = get_or_create_folder(inbox, folder_name)
				if not project_folder:
					log_message(f'Could not create folder for "{folder_name}", skip')
					skipped_count += 1
					continue

				mail.Move(project_folder)

				# Herstel originele read/unread status
				moved_mail = project_folder.Items(project_folder.Items.Count)
				moved_mail.UnRead = was_unread
				moved_mail.Save()

				log_message(f'Email moved to folder "{folder_name}" (status behouden)')

				processed_count += 1

			except Exception as e:
				log_message(f'Error processing email {i}: {e}')
				continue

		log_message(f'Done! {processed_count} emails processed, {skipped_count} skipped')

	except Exception as e:
		log_message(f'General error: {e}')
		return False

	return True


def cleanup_auto_folders():
	"""Remove auto-created folders and move mails back to inbox"""
	try:
		log_message('Starting cleanup...')
		inbox = get_inbox()

		auto_folders = []
		for folder in inbox.Folders:
			if folder.Name.endswith(AUTO_SUFFIX):
				auto_folders.append(folder)

		if not auto_folders:
			log_message('No [AUTO] folders found')
			return

		moved_count = 0

		for folder in auto_folders:
			folder_name = folder.Name
			mail_count = folder.Items.Count
			log_message(f'Processing folder: {folder_name} ({mail_count} emails)')

			for i in range(mail_count, 0, -1):
				try:
					mail = folder.Items.Item(i)
					mail.Move(inbox)
					moved_count += 1
				except Exception as e:
					log_message(f'Error moving email from {folder_name}: {e}')

			try:
				folder.Delete()
				log_message(f'Folder deleted: {folder_name}')
			except Exception as e:
				log_message(f'Error deleting folder {folder_name}: {e}')

		log_message(f'Cleanup complete! {moved_count} emails moved back to inbox')

	except Exception as e:
		log_message(f'Error during cleanup: {e}')


def main():
	"""Main function with user interaction"""
	print('=' * 60)
	print('OUTLOOK MAIL ORGANIZER')
	print('=' * 60)
	print()

	while True:
		print('\nKies een optie:')
		print('1. Mails verwerken')
		print('2. Opruimen (verwijder [AUTO] mappen)')
		print('3. Afsluiten')
		print()

		choice = input('Keuze (1/2/3): ').strip()

		if choice == '1':
			print('\n--- Mails Verwerken ---')

			try:
				max_mails = int(
					input('Hoeveel mails wil je maximaal verwerken? (bijv. 50): ')
				)
			except ValueError:
				print('Ongeldige invoer, gebruik standaard 50')
				max_mails = 50

			exclusion_input = input(
				'Uitsluitingswoorden (gescheiden door komma, of Enter om over te slaan): '
			).strip()

			exclusion_words = []
			if exclusion_input:
				exclusion_words = [
					word.strip() for word in exclusion_input.split(',') if word.strip()
				]

			print('\nStart verwerking...\n')
			process_mails(max_mails, exclusion_words)

		elif choice == '2':
			print('\n--- Opruimen ---')
			confirm = input(
				'Weet je zeker dat je alle [AUTO] mappen wilt verwijderen? (ja/nee): '
			).strip().lower()

			if confirm == 'ja':
				cleanup_auto_folders()
			else:
				print('Opruimen geannuleerd')

		elif choice == '3':
			print('\nBedankt voor het gebruiken van Mail Organizer!')
			break

		else:
			print('Ongeldige keuze, probeer opnieuw')


if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print('\n\nScript gestopt door gebruiker')
	except Exception as e:
		print(f'\nOnverwachte fout: {e}')
		input('\nDruk Enter om af te sluiten...')