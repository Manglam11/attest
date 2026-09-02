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

# Duplicated from engine/app/agent.py's SYSTEM_PROMPT — the two live in
# separate containers with no shared package, and the eval judge already
# carries its own copy (engine/app/eval/judge.py). A refusal is a correct
# answer, not an error, so the UI needs to recognize it by exact text.
REFUSAL_TEXT = "I cannot answer this from the provided sources."


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
            try:
                result = ask_engine(request.user, question)
            except EngineUnreachable as exc:
                context['error'] = 'unreachable'
                context['error_detail'] = str(exc)
            except EngineAuthError as exc:
                context['error'] = 'auth'
                context['error_detail'] = str(exc)
            except EngineResponseError as exc:
                context['error'] = 'response'
                context['error_detail'] = str(exc)
            else:
                context['result'] = result
                context['refused'] = result['answer'].strip() == REFUSAL_TEXT
    return render(request, 'accounts/ask.html', context)
