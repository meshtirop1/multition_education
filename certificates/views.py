from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from .models import Certificate


@login_required
def my_certificates(request):
    """List user's certificates."""
    certificates = Certificate.objects.filter(student=request.user)
    return render(request, 'certificates/list.html', {'certificates': certificates})


@login_required
def download_certificate(request, certificate_id):
    """Download certificate PDF."""
    certificate = get_object_or_404(
        Certificate,
        certificate_id=certificate_id,
        student=request.user
    )
    if not certificate.pdf_file:
        raise Http404("Certificate PDF not found.")

    return FileResponse(
        certificate.pdf_file.open('rb'),
        as_attachment=True,
        filename=f'MultiTion_Certificate_{certificate.course.title[:30]}.pdf'
    )


def verify_certificate(request, certificate_id):
    """Public certificate verification."""
    try:
        certificate = Certificate.objects.get(certificate_id=certificate_id)
        valid = True
    except Certificate.DoesNotExist:
        certificate = None
        valid = False

    return render(request, 'certificates/verify.html', {
        'certificate': certificate,
        'valid': valid,
    })
