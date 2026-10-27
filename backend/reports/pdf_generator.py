from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable,
)


COLOR_GREEN = colors.HexColor('#4ade80')
COLOR_DARK = colors.HexColor('#0a0f0d')
COLOR_GRAY = colors.HexColor('#5a8a68')
COLOR_LIGHT = colors.HexColor('#f0fdf4')
COLOR_RED = colors.HexColor('#f87171')
COLOR_WARN = colors.HexColor('#fbbf24')
COLOR_SURFACE = colors.HexColor('#1c2a1e')
COLOR_BORDER = colors.HexColor('#243328')


def build_styles(base):
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        'ReportTitle', parent=styles['Title'],
        fontName='Helvetica-Bold', fontSize=22, textColor=COLOR_GREEN,
        spaceAfter=4 * mm, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        'Subtitle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=10, textColor=COLOR_GRAY,
        spaceAfter=10 * mm, alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        'SectionTitle', parent=styles['Heading2'],
        fontName='Helvetica-Bold', fontSize=13, textColor=COLOR_GREEN,
        spaceBefore=8 * mm, spaceAfter=4 * mm,
    ))
    styles.add(ParagraphStyle(
        'BodySmall', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#111a15'),
        leading=12,
    ))
    styles.add(ParagraphStyle(
        'BodySmallBold', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#111a15'),
        leading=12,
    ))
    styles.add(ParagraphStyle(
        'CellCenter', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8.5, textColor=colors.HexColor('#111a15'),
        alignment=TA_CENTER, leading=11,
    ))
    styles.add(ParagraphStyle(
        'Pedagogia', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#111a15'),
        leading=13, spaceBefore=2 * mm,
    ))
    return styles


def _make_info_table(data, styles):
    rows = [[Paragraph(k, styles['BodySmallBold']), Paragraph(v, styles['BodySmall'])]
            for k, v in data]
    t = Table(rows, colWidths=[5.5 * cm, 10 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, COLOR_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6 * mm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4 * mm),
        ('TOPPADDING', (0, 0), (-1, -1), 3 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3 * mm),
        ('BACKGROUND', (0, 0), (0, -1), COLOR_SURFACE),
        ('TEXTCOLOR', (0, 0), (0, -1), COLOR_LIGHT),
    ]))
    return t


def _make_stats_table(data, styles):
    headers = ['Total', 'Promedio', 'Máximo', 'Mínimo', 'Aprobación']
    values = [
        str(data['total_attempts']),
        f"{data['avg']}%",
        f"{data['max_score']}%",
        f"{data['min_score']}%",
        f"{data['pct_aprobacion']}%",
    ]
    rows = [
        [Paragraph(h, styles['CellCenter']) for h in headers],
        [Paragraph(v, styles['CellCenter']) for v in values],
    ]
    t = Table(rows, colWidths=[3 * cm] * 5)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_DARK),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BACKGROUND', (0, 1), (-1, 1), COLOR_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, COLOR_BORDER),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3 * mm),
    ]))
    return t


def _make_students_table(students, styles):
    headers = ['#', 'Nombre', 'Documento', 'Puntaje', '%', 'Fecha']
    rows = [[Paragraph(h, styles['CellCenter']) for h in headers]]
    for i, s in enumerate(students, 1):
        fecha = s.fecha.strftime('%d/%m/%Y') if s.fecha else '-'
        rows.append([
            Paragraph(str(i), styles['CellCenter']),
            Paragraph(s.nombre_estudiante, styles['BodySmall']),
            Paragraph(s.documento_estudiante, styles['BodySmall']),
            Paragraph(f"{s.puntaje}/{s.total_preguntas}", styles['CellCenter']),
            Paragraph(f"{s.porcentaje}%", styles['CellCenter']),
            Paragraph(fecha, styles['CellCenter']),
        ])
    col_widths = [0.8 * cm, 4.5 * cm, 3 * cm, 2.2 * cm, 1.5 * cm, 2.5 * cm]
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_DARK),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, COLOR_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5 * mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 2 * mm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2 * mm),
    ]
    for i in range(1, len(rows)):
        bg = COLOR_LIGHT if i % 2 == 1 else colors.white
        style_cmds.append(('BACKGROUND', (0, i), (-1, i), bg))
    t.setStyle(TableStyle(style_cmds))
    return t


def _make_failed_questions_table(failed, styles):
    if not failed:
        return Paragraph('No hay datos de preguntas falladas.', styles['BodySmall'])

    headers = ['#', 'Pregunta', 'Errores', '% Error']
    rows = [[Paragraph(h, styles['CellCenter']) for h in headers]]
    for i, f in enumerate(failed, 1):
        rows.append([
            Paragraph(str(i), styles['CellCenter']),
            Paragraph(f['pregunta'][:80], styles['BodySmall']),
            Paragraph(str(f['errores']), styles['CellCenter']),
            Paragraph(f"{f['pct_error']}%", styles['CellCenter']),
        ])
    col_widths = [0.8 * cm, 9.5 * cm, 2 * cm, 2 * cm]
    t = Table(rows, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_RED),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, COLOR_BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5 * mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5 * mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 2 * mm),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2 * mm),
    ]
    for i in range(1, len(rows)):
        bg = COLOR_LIGHT if i % 2 == 1 else colors.white
        style_cmds.append(('BACKGROUND', (0, i), (-1, i), bg))
    t.setStyle(TableStyle(style_cmds))
    return t


def generate_report(report_data):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2.5 * cm, rightMargin=2.5 * cm,
    )
    styles = build_styles(None)
    elements = []

    # ── Portada / Título ──────────────────────────────────────────────
    elements.append(Spacer(1, 1.5 * cm))
    elements.append(Paragraph('BioAula', styles['ReportTitle']))
    elements.append(Paragraph('Informe de evaluación', styles['Subtitle']))
    elements.append(HRFlowable(width='100%', thickness=0.5, color=COLOR_GREEN, spaceAfter=6 * mm))
    elements.append(Paragraph(
        f"<b>{report_data['quiz'].titulo}</b>",
        ParagraphStyle('QuizTitle', parent=styles['Normal'],
                       fontName='Helvetica-Bold', fontSize=14,
                       textColor=COLOR_DARK, alignment=TA_CENTER),
    ))
    elements.append(Spacer(1, 6 * mm))

    # ── 1. Información general ────────────────────────────────────────
    elements.append(Paragraph('1. Información general', styles['SectionTitle']))
    prof_name = report_data['profesor'].nombre if report_data['profesor'] else '—'
    created = (report_data['quiz'].fecha_creacion.strftime('%d/%m/%Y %H:%M')
               if report_data['quiz'].fecha_creacion else '—')
    num_q = report_data['quiz'].num_q or len(report_data['quiz'].questions) if report_data['quiz'].questions else 0
    info_rows = [
        ('Nombre de la prueba', report_data['quiz'].titulo),
        ('Profesor', prof_name),
        ('Fecha de creación', created),
        ('Número de preguntas', str(num_q)),
        ('Estudiantes que presentaron', str(report_data['total_attempts'])),
    ]
    elements.append(_make_info_table(info_rows, styles))

    # ── 2. Estadísticas generales ─────────────────────────────────────
    if report_data['total_attempts'] > 0:
        elements.append(Paragraph('2. Estadísticas generales', styles['SectionTitle']))
        elements.append(_make_stats_table(report_data, styles))

        # ── 3. Tabla de estudiantes ───────────────────────────────────
        elements.append(Paragraph('3. Resultados por estudiante', styles['SectionTitle']))
        elements.append(_make_students_table(report_data['students'], styles))

        # ── 4. Preguntas con mayor dificultad ─────────────────────────
        if report_data['most_failed']:
            elements.append(Paragraph('4. Preguntas con mayor dificultad', styles['SectionTitle']))
            elements.append(_make_failed_questions_table(report_data['most_failed'], styles))

    # ── 5. Recomendaciones pedagógicas ────────────────────────────────
    elements.append(Paragraph('5. Recomendaciones pedagógicas', styles['SectionTitle']))
    elements.append(Paragraph(
        'No hay recomendaciones disponibles.',
        styles['Pedagogia'],
    ))

    # ── Footer ────────────────────────────────────────────────────────
    elements.append(Spacer(1, 1.5 * cm))
    elements.append(HRFlowable(width='100%', thickness=0.3, color=COLOR_GRAY, spaceAfter=3 * mm))
    today = datetime.now().strftime('%d/%m/%Y %H:%M')
    elements.append(Paragraph(
        f'Informe generado el {today} · BioAula',
        ParagraphStyle('Footer', parent=styles['Normal'],
                       fontName='Helvetica', fontSize=7,
                       textColor=COLOR_GRAY, alignment=TA_CENTER),
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer
