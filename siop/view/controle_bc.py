from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def controle_bc(request):
    return render(request, "controle_bc/controle_bc.html")
