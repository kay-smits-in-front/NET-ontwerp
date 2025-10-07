from flask import Blueprint, render_template, request, flash, redirect, url_for
from .mail_processor import (
    extract_project_folder_name,
    get_or_create_folder,
    should_exclude_mail,
    get_inbox,
    get_auto_folders,
    log_message,
)

bp = Blueprint('mail_organizer', __name__, url_prefix='/mail_organizer')


@bp.route('/')
def main():
    return render_template(
        'mail_organizer/mail_organizer.html',
        title='Mail Organizer',
        data={'message': 'Welkom bij Mail Organizer!'},
    )


@bp.route('/process', methods=['GET', 'POST'])
def process():
    if request.method == 'POST':
        return handle_process_mails()

    return render_template('mail_organizer/process.html')


@bp.route('/cleanup', methods=['GET', 'POST'])
def cleanup():
    if request.method == 'POST':
        return handle_cleanup()

    return render_template('mail_organizer/cleanup.html')


def handle_process_mails():
    """Process emails based on user input"""
    try:
        max_mails = request.form.get('max_mails', type=int)
        exclusion_text = request.form.get('exclusion_words', '')
        exclusion_words = [
            word.strip() for word in exclusion_text.split(',') if word.strip()
        ]

        if not max_mails or max_mails < 1:
            flash('Aantal mails moet minimaal 1 zijn', 'error')
            return redirect(url_for('mail_organizer.process'))

        inbox = get_inbox()
        messages = inbox.Items
        unread_messages = messages.Restrict('[Unread] = True')

        if unread_messages.Count == 0:
            flash('Geen ongelezen mails gevonden', 'warning')
            return redirect(url_for('mail_organizer.process'))

        processed_count = 0
        skipped_count = 0
        logs = []

        for i in range(
            min(unread_messages.Count, max_mails), 0, -1
        ):
            try:
                mail = unread_messages.Item(i)
                subject = mail.Subject

                logs.append(log_message(f'Processing mail: "{subject}"'))

                if should_exclude_mail(subject, exclusion_words):
                    logs.append(
                        log_message(f'Mail excluded (contains exclusion word)')
                    )
                    skipped_count += 1
                    continue

                dash_count = subject.count(' - ')
                if dash_count < 2:
                    logs.append(
                        log_message(
                            f'Mail has incorrect format (only {dash_count}x " - ", minimum 2 required), skip'
                        )
                    )
                    skipped_count += 1
                    continue

                folder_name = extract_project_folder_name(subject)
                if not folder_name:
                    logs.append(log_message('Could not extract folder name, skip'))
                    skipped_count += 1
                    continue

                logs.append(log_message(f'Folder name found: "{folder_name}"'))

                project_folder = get_or_create_folder(inbox, folder_name)
                if not project_folder:
                    logs.append(
                        log_message(
                            f'Could not create folder for "{folder_name}", skip'
                        )
                    )
                    skipped_count += 1
                    continue

                mail.Move(project_folder)
                logs.append(log_message(f'Mail moved to folder "{folder_name}"'))

                mail.UnRead = False

                processed_count += 1

            except Exception as e:
                logs.append(log_message(f'Error processing mail {i}: {e}'))
                continue

        result_data = {
            'processed_count': processed_count,
            'skipped_count': skipped_count,
            'total_checked': min(unread_messages.Count, max_mails),
            'logs': logs,
        }

        return render_template('mail_organizer/resultaat.html', data=result_data)

    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('mail_organizer.process'))


def handle_cleanup():
    """Remove auto-created folders and move mails back to inbox"""
    try:
        inbox = get_inbox()
        auto_folders = get_auto_folders(inbox)

        if not auto_folders:
            flash('Geen automatisch aangemaakte mappen gevonden', 'warning')
            return redirect(url_for('mail_organizer.cleanup'))

        moved_count = 0
        deleted_folders = []

        for folder in auto_folders:
            folder_name = folder.Name
            mail_count = folder.Items.Count

            for i in range(mail_count, 0, -1):
                try:
                    mail = folder.Items.Item(i)
                    mail.Move(inbox)
                    moved_count += 1
                except Exception as e:
                    log_message(f'Error moving mail from {folder_name}: {e}')

            try:
                folder.Delete()
                deleted_folders.append(folder_name)
            except Exception as e:
                log_message(f'Error deleting folder {folder_name}: {e}')

        cleanup_data = {
            'moved_count': moved_count,
            'deleted_folders': deleted_folders,
        }

        return render_template('mail_organizer/cleanup_result.html', data=cleanup_data)

    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('mail_organizer.cleanup'))