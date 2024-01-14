from django.shortcuts import render

from utils.debug import log


def handler_log(request, msg: str, status: int):
    log(f"{request.build_absolute_uri()} - Got error {status} - {msg}")


def handler404(request, msg: str):
    handler_log(request=request, msg=msg, status=404)
    return render(request, 'error/404.html', context={'request': request, 'error_msg': msg})
