import uuid

from flask import redirect, render_template, request, url_for

from app import current_service
from app.main import main
from app.main.forms import PDFUploadForm
from app.utils import user_has_permissions


@main.route("/services/<service_id>/uploads")
@user_has_permissions('send_messages')
def uploads(service_id):
    return render_template('views/uploads/index.html')


@main.route("/services/<service_id>/upload-letter", methods=['GET', 'POST'])
@user_has_permissions('send_messages')
def upload_letter(service_id):
    form = PDFUploadForm()

    if form.validate_on_submit():
        upload_id = uuid.uuid4()

        return redirect(
            url_for(
                'main.uploaded_letter_preview',
                service_id=current_service.id,
                file_id=upload_id,
                original_filename=form.file.data.filename,
            )
        )

    return render_template('views/uploads/choose-file.html', form=form)


@main.route("/services/<service_id>/preview-letter/<file_id>")
@user_has_permissions('send_messages')
def uploaded_letter_preview(service_id, file_id):
    original_filename = request.args.get('original_filename')

    return render_template('views/uploads/preview.html', original_filename=original_filename)
