from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import get_object_or_404, redirect, render

from accounts.engine_client import (
    EngineAuthError,
    EngineResponseError,
    EngineUnreachable,
    ask_engine,
)
from accounts.eval_artifacts import load_judged_run, summarise_for_dashboard
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


@login_required
def history(request):
    records = AskRecord.objects.filter(user=request.user)
    return render(request, 'accounts/history.html', {'records': records})


@login_required
def trust(request):
    data, artifact_error = load_judged_run()
    context = {"artifact_error": artifact_error}
    if data is not None:
        context.update(summarise_for_dashboard(data))

    context["recent_asks"] = AskRecord.objects.filter(user=request.user)[:20]
    return render(request, 'accounts/trust.html', context)


@login_required
def history_detail(request, pk):
    record = get_object_or_404(AskRecord, pk=pk, user=request.user)
    return render(
        request,
        'accounts/history_detail.html',
        {
            'record': record,
            'result': record,
            'refused': record.refused,
            'error': record.error,
            'error_detail': record.error_detail,
        },
    )
