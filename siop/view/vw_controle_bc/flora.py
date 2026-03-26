from django.shortcuts import render


def flora(request):
    return render(request, "controle_bc/flora/flora.html")
