from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import HttpResponse, redirect

from aw.permission import authorized_to_access, authorized_to_exec, authorized_to_write


def _deny(request) -> (bool, HttpResponse):
    if request.method not in ['GET', 'POST', 'PUT']:
        return HttpResponse(status=405)


@login_required
@user_passes_test(authorized_to_access, login_url='/')
def ui(request, **kwargs):
    bad, deny = _deny(request)
    if bad:
        return deny

    if request.method == 'POST':
        return ui_write

    if request.method == 'PUT':
        return ui_write

    return HttpResponse(status=200, content=b"OK - read")


@login_required
@user_passes_test(authorized_to_write, login_url='/')
def ui_write(request, **kwargs):
    return HttpResponse(status=200, content=b"OK - write")


@login_required
@user_passes_test(authorized_to_exec, login_url='/')
def ui_exec(request, **kwargs):
    return HttpResponse(status=200, content=b"OK - exec")


def catchall(request, **kwargs):
    return redirect('/accounts/login/')
