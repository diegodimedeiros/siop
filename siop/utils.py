"""Compatibility re-export layer for legacy imports.

Prefer importing shared infrastructure directly from ``core.utils`` in new
code. This module remains only to keep older domain views stable while we
finish converging imports.
"""

from core.utils.catalogos import (
    catalogo_areas_data,
    catalogo_encaminhamentos_data,
    catalogo_locais_por_area_data,
    catalogo_naturezas_data,
    catalogo_p1,
    catalogo_p1_data,
    catalogo_primeiros_socorros_data,
    catalogo_responsaveis_atendimento_data,
    catalogo_responsaveis_atendimento_display_map,
    catalogo_sexos_data,
    catalogo_tipos_ocorrencia_data,
    catalogo_tipos_pessoa_data,
    catalogo_tipos_por_natureza_data,
    catalogo_transportes_data,
    catalogo_ufs_data,
)
from core.utils.exports import (
    export_generic_csv as _export_generic_csv,
    export_generic_excel as _export_generic_excel,
    export_generic_pdf as _export_generic_pdf,
)
from core.utils.exports.pdf_export import (
    build_numbered_canvas_class,
    draw_pdf_label_value,
    draw_pdf_page_chrome,
    wrap_pdf_text_lines,
)
from core.utils.formatters import (
    as_dt_local as _as_dt_local,
    bool_ptbr as _bool_ptbr,
    fmt_dt as _fmt_dt,
    status_ptbr as _status_ptbr,
    user_display as _user_display,
)
from core.utils.helpers import (
    anexos_total as _anexos_total,
    assinatura_status as _assinatura_status,
    first_geolocalizacao_text as _first_geolocalizacao_text,
)
from core.utils.validators import validation_size

__all__ = [
    "_anexos_total",
    "_assinatura_status",
    "_as_dt_local",
    "_bool_ptbr",
    "_export_generic_csv",
    "_export_generic_excel",
    "_export_generic_pdf",
    "_first_geolocalizacao_text",
    "_fmt_dt",
    "_status_ptbr",
    "_user_display",
    "build_numbered_canvas_class",
    "catalogo_areas_data",
    "catalogo_encaminhamentos_data",
    "catalogo_locais_por_area_data",
    "catalogo_naturezas_data",
    "catalogo_p1",
    "catalogo_p1_data",
    "catalogo_primeiros_socorros_data",
    "catalogo_responsaveis_atendimento_data",
    "catalogo_responsaveis_atendimento_display_map",
    "catalogo_sexos_data",
    "catalogo_tipos_ocorrencia_data",
    "catalogo_tipos_pessoa_data",
    "catalogo_tipos_por_natureza_data",
    "catalogo_transportes_data",
    "catalogo_ufs_data",
    "draw_pdf_label_value",
    "draw_pdf_page_chrome",
    "validation_size",
    "wrap_pdf_text_lines",
]
