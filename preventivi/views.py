from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def quote_list(request):
    return render(request, 'preventivi/quote_list.html')
