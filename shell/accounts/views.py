from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render

from accounts.engine_client import (
    EngineAuthError,
    EngineResponseError,
    EngineUnreachable,
    ask_engine,
)
from accounts.models import AskRecord


def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


@login_required
def home(request):
    return render(request, 'accounts/home.html')


@login_required
def ask(request):
    context = {}
    if request.method == 'POST':
        question = request.POST.get('question', '').strip()
        context['question'] = question
        if question:
            record = AskRecord(user=request.user, question=question)
            try:
                result = ask_engine(request.user, question)
            except EngineUnreachable as exc:
                context['error'] = record.error = 'unreachable'
                context['error_detail'] = record.error_detail = str(exc)
            except EngineAuthError as exc:
                context['error'] = record.error = 'auth'
                context['error_detail'] = record.error_detail = str(exc)
            except EngineResponseError as exc:
                context['error'] = record.error = 'response'
                context['error_detail'] = record.error_detail = str(exc)
            else:
                context['result'] = result
                context['refused'] = result['refused']
                record.answer = result['answer']
                record.refused = result['refused']
                record.latency_s = result.get('latency_s')
                record.sources = result.get('sources') or []
                record.tool_calls = result.get('tool_calls') or []
            record.save()
    return render(request, 'accounts/ask.html', context)
