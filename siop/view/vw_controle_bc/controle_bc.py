from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone

from siop.models import ControleAtendimento


def _controle_bc_context():
    now = timezone.localtime()
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    atendimentos = ControleAtendimento.objects.all()

    area_local_mais_atendimento = (
        atendimentos.values("area_atendimento", "local")
        .exclude(area_atendimento__isnull=True)
        .exclude(area_atendimento__exact="")
        .exclude(local__isnull=True)
        .exclude(local__exact="")
        .annotate(total=Count("id"))
        .order_by("-total", "area_atendimento", "local")
        .first()
    )
    principal_primeiro_socorro = (
        atendimentos.values("primeiros_socorros")
        .exclude(primeiros_socorros__isnull=True)
        .exclude(primeiros_socorros__exact="")
        .annotate(total=Count("id"))
        .order_by("-total", "primeiros_socorros")
        .first()
    )

    return {
        "atendimento_total_semana": atendimentos.filter(data_atendimento__gte=week_start).count(),
        "atendimento_total_mes": atendimentos.filter(data_atendimento__gte=month_start).count(),
        "atendimento_area_local_top": (
            f"{area_local_mais_atendimento['area_atendimento']} - {area_local_mais_atendimento['local']}"
            if area_local_mais_atendimento
            else "-"
        ),
        "atendimento_area_local_top_total": (area_local_mais_atendimento or {}).get("total") or 0,
        "atendimento_primeiro_socorro_top": (principal_primeiro_socorro or {}).get("primeiros_socorros") or "-",
        "atendimento_primeiro_socorro_top_total": (principal_primeiro_socorro or {}).get("total") or 0,
    }


@login_required
def controle_bc(request):
    return render(request, "controle_bc/controle_bc.html", _controle_bc_context())
