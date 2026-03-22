from django.shortcuts import render


def flora(request):
    return render(request, "controlebc/flora.html")
